#!/usr/bin/env python3
"""Kiro CLI PreToolUse hook that checks shell redirects and secret paths.

Kiro runs two checks here that its permission rules cannot make.

Redirect targets: Kiro strips redirections before matching a shell command
against its rules and never checks the target as an fs_write, so
`git log > ~/.zshrc` matches the allow for `git log`. This hook blocks (exit 2)
any `>`, `>>`, `&>`, or `>|`, or zsh's `>!` forms, whose target is outside the
paths Kiro may write without asking (the session's working directory, /tmp, ~/Desktop,
~/Downloads, and device files), which sends the model to the write tool, where
Kiro asks for approval. A target that a variable, command substitution, glob,
or process substitution builds is blocked too, since it cannot be resolved
here, and so is a relative target in a command that changes directory first.

Secret paths: the ask rule in permissions.yaml matches the command's text, so
it misses a path that only reaches a credential store once bash expands `~`,
$HOME, braces, or a glob, or follows a symlink
(`git diff --no-index ~/.a?s/c* /dev/null`). This hook expands every word of
the command, `<` sources included, resolves symlinks, and returns permissionDecision "ask" when any result matches
SECRET_PATTERNS. It asks instead of blocking because ordinary commands such as
`rg credentials src` match too, as they do under the ask rule. A blocked
redirect takes precedence over the ask.

Bash and shlex disagree on a few points, which the parsing handles:

- A here-document body is data, so it is left out before tokenizing; an
  apostrophe in prose would otherwise stop the command from tokenizing. A body
  that expands $(...) or backticks, or that never ends, is kept.
- `<<` inside $((...)) or ((...)) shifts bits and starts no here-document.
- Bash starts a comment only at a word boundary and ignores quotes inside one,
  while shlex treats `#` as always or never starting a comment. Each check runs
  in both modes (COMMENT_MODES) and combines the results.
- A command that contains `>` but does not tokenize, such as one with an
  unbalanced quote, is blocked, because bash may still run the redirect.
- shlex does not parse ANSI-C quoting ($'...'), nor the nested quotes and
  redirects of $(...), ${...}, or backticks inside double quotes, so it may
  misplace where a string ends (quoting_hazard). A $'...' command with `>` or
  `<<` is blocked, as is a `>` inside a token of a command with such a
  double-quoted expansion, and the secret path check adds rough words.
- "$(cat <<'X' ... X)" with a quoted delimiter prints its body as data, the
  usual way to pass a commit message, so the redirect checks replace it with
  "" first (without_literal_substitutions).

The model can set tool_input.cwd, so that value only resolves relative paths
and never widens the allowed paths. A payload that is not JSON of the expected
shape is blocked.
"""

# Kiro's hook environment can resolve python3 to the macOS system Python 3.9,
# which cannot evaluate `str | None` annotations at import time.
from __future__ import annotations

import fnmatch
import glob
import json
import os
import re
import shlex
import sys

DEVICES = {"/dev/null", "/dev/stderr", "/dev/stdin", "/dev/stdout"}
UNRESOLVABLE = set("$`*?[(")
# shlex's default punctuation_chars; it fuses adjacent ones into one token.
PUNCTUATION = set("();<>|&")
# Locations that may hold credentials, as Kiro shell globs, which support only
# `*`. The shell ask rule in permissions.yaml lists the same patterns.
SECRET_PATTERNS = (
    "*.aws",
    "*.aws *",
    "*.aws/*",
    "*.claude.json*",
    "*.codex/auth.json*",
    "*.config/environment*",
    "*.config/gcloud",
    "*.config/gcloud *",
    "*.config/gcloud/*",
    "*.config/gh",
    "*.config/gh *",
    "*.config/gh/*",
    "*.config/op",
    "*.config/op *",
    "*.config/op/*",
    "*.docker",
    "*.docker *",
    "*.docker/*",
    "*.gnupg*",
    "*.kube",
    "*.kube *",
    "*.kube/*",
    "*.mcporter*",
    "*.midway*",
    "*.netrc*",
    "*.npmrc*",
    "*.op",
    "*.op *",
    "*.op/*",
    "*.pypirc*",
    "*.ssh*",
    "*.tavily*",
    "*.zsh_history*",
    "*/environ*",
    "*/mcporter",
    "*/mcporter *",
    "*/mcporter/*",
    "*credentials*",
    "*id_ed25519*",
    "*id_rsa*",
    "*mcporter.json*",
    "*zsh/history*",
)
# shlex comment characters for each tokenizing pass. Without comments, an
# apostrophe in each of two comments joins the lines between them into one
# string; with them, `x#y` loses the rest of its line.
COMMENT_MODES = ("", "#")
DIRECTORY_CHANGES = {"cd", "popd", "pushd"}
# A here-document operator and its delimiter, which may be quoted.
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([^\s'\"();<>|&]+)\2")
# Words of a command that does not tokenize.
ROUGH_WORD = re.compile(r"[^\s;&|()<>'\"]+")
# shlex does not parse bash's ANSI-C quoting: inside $'...' bash reads \' as an
# escaped quote, while shlex ends the string there.
ANSI_C_QUOTE = "$'"
# Expansions that bash parses as nested code with quotes of their own, even
# inside double quotes; shlex reads them as plain characters of the string.
NESTED_EXPANSION = re.compile(r"\$[({]|`")
# The start of "$(cat <<'X'" or "$(cat <<"X"", ending its line.
LITERAL_SUBSTITUTION = re.compile(
    r"\"\$\(cat[ \t]*<<[ \t]*(['\"])([A-Za-z_][A-Za-z0-9_]*)\1[ \t]*\n"
)
# A leading $HOME or ${HOME} that ends the word or a path component.
HOME_VARIABLE = re.compile(r"\$(?:HOME|\{HOME\})(?=/|$)")
# A brace expansion group without nested braces, such as {a,b}.
BRACE_LIST = re.compile(r"\{([^{}]*,[^{}]*)\}")
# More brace expansion words than this make the secret path check ask.
MAX_BRACE_WORDS = 256
# zsh reads `!` right after a redirect operator (`>!`, `>>!`, `&>!`, `>&!`)
# as part of the operator, which overrides noclobber; shlex splits it off.
CLOBBER = "!"


def allowed_roots(cwd: str) -> list[str]:
    home = os.path.expanduser("~")
    roots = [
        cwd,
        "/tmp",
        os.path.join(home, "Desktop"),
        os.path.join(home, "Downloads"),
    ]
    return [os.path.realpath(root) for root in roots]


def resolve(target: str, cwd: str) -> str | None:
    if UNRESOLVABLE & set(target):
        return None
    # ~user expands to another account's home, which this hook does not look up.
    if target.startswith("~") and target != "~" and not target.startswith("~/"):
        return None
    path = os.path.join(cwd, os.path.expanduser(target))
    # Linux links /dev/stdout and /dev/fd/N into /proc, so match devices
    # before following symlinks.
    if is_device(os.path.normpath(path)):
        return os.path.normpath(path)
    return os.path.realpath(path)


def is_device(path: str) -> bool:
    return path in DEVICES or path.startswith("/dev/fd/")


def is_allowed(path: str, root_cwd: str) -> bool:
    if is_device(path):
        return True
    return any(
        path == root or path.startswith(root + os.sep)
        for root in allowed_roots(root_cwd)
    )


def is_secret(path: str) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in SECRET_PATTERNS)


def below(path: str, root: str) -> str:
    """Returns the part of path below root, or path itself when it is outside."""
    if path == root:
        return ""
    if path.startswith(root + os.sep):
        return path[len(root) + 1 :]
    return path


def brace_alternatives(word: str) -> list[str] | None:
    """Returns the words that brace expansion makes of word, word first.

    Each {a,b,...} group without nested braces expands into its alternatives,
    and the groups multiply. Returns None when they would make more than
    MAX_BRACE_WORDS words.
    """
    words, count = [word], 1
    for match in BRACE_LIST.finditer(word):
        count *= match.group(1).count(",") + 1
    if count > MAX_BRACE_WORDS:
        return None
    pending = [word]
    while pending:
        current = pending.pop()
        match = BRACE_LIST.search(current)
        if match is None:
            words.append(current)
            if len(words) > MAX_BRACE_WORDS:
                return None
            continue
        head, tail = current[: match.start()], current[match.end() :]
        pending += [head + part + tail for part in match.group(1).split(",")]
    return list(dict.fromkeys(words))


def input_paths(word: str, cwd: str) -> list[str]:
    """Returns the word as written and the paths bash would read for it.

    A leading $HOME or ${HOME} expands like `~`; a word with any other `$` or
    a backtick counts only as written. A relative word counts only with the
    part of each path below cwd, so that a cwd inside a secret location does
    not make every word match. A path that leaves cwd, through `..` or a
    symlink, counts in full.
    """
    home_variable = HOME_VARIABLE.match(word)
    if home_variable:
        word = os.path.expanduser("~") + word[home_variable.end() :]
    if "$" in word or "`" in word:
        return [word]
    expanded = os.path.expanduser(word)
    path = os.path.join(cwd, expanded)
    found = glob.glob(path) if set("*?[") & set(word) else [path]
    if os.path.isabs(expanded):
        return [word, *found, *(os.path.realpath(p) for p in found)]
    root, real_root = os.path.normpath(cwd), os.path.realpath(cwd)
    return [
        word,
        *(below(os.path.normpath(p), root) for p in found),
        *(below(os.path.realpath(p), real_root) for p in found),
    ]


def tokenize(command: str, commenters: str) -> list[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = commenters
    return list(lexer)


def tokenizes(text: str, commenters: str) -> bool:
    try:
        tokenize(text, commenters)
    except ValueError:
        return False
    return True


def is_punctuation(token: str) -> bool:
    return set(token) <= PUNCTUATION


def heredoc_operators(line: str, commenters: str) -> list[str] | None:
    try:
        tokens = tokenize(line, commenters)
    except ValueError:
        return None
    return [t for t in tokens if is_punctuation(t) and t.lstrip(";)|&") == "<<"]


def without_arithmetic(line: str, depth: int) -> tuple[str, int]:
    """Returns (text, depth): the line without $((...)) and ((...)) contents.

    `<<` inside arithmetic shifts bits and starts no here-document. depth is
    the parenthesis depth of arithmetic still open at the start of the line.
    """
    kept, index = [], 0
    while index < len(line):
        if not depth and line.startswith("((", index):
            depth, index = 2, index + 2
            continue
        if depth:
            depth += {"(": 1, ")": -1}.get(line[index], 0)
        else:
            kept.append(line[index])
        index += 1
    return "".join(kept), depth


def may_misplace_quotes(text: str) -> bool:
    """Returns whether shlex may end a string where bash does not.

    A double-quoted string that contains $(...), ${...}, or backticks may hold
    quotes that bash reads as nested and shlex as the end of the string.
    """
    return ANSI_C_QUOTE in text or (
        '"' in text and NESTED_EXPANSION.search(text) is not None
    )


def without_literal_substitutions(command: str) -> str:
    """Returns the command with each "$(cat <<'X' ... X)" replaced by "".

    With a quoted delimiter, bash reads the here-document body as literal data
    and cat prints it, so a `>` or quote in the body (a commit message's `->`
    or Markdown quote) is neither a redirect nor the end of a string. The body
    ends at its first line equal to the delimiter, and only `)"` may follow.
    No earlier body line may start with the delimiter after leading
    whitespace, because bash 5 may end the body there inside $(...).
    A span is replaced only when bash and shlex agree that it starts outside
    any string or comment: the text before it tokenizes the same with and
    without comments, has no here-document of its own, and has nothing
    may_misplace_quotes flags.
    """
    while True:
        match = LITERAL_SUBSTITUTION.search(command)
        if match is None:
            return command
        prefix = command[: match.start()]
        try:
            agree = tokenize(prefix, "") == tokenize(prefix, "#")
        except ValueError:
            agree = False
        if not agree or "<<" in prefix or may_misplace_quotes(prefix):
            return command
        delimiter = match.group(2)
        lines = command[match.end() :].split("\n")
        if delimiter not in lines:
            return command
        end = lines.index(delimiter)
        # Inside $(...), bash 5 also ends the body at a line that starts with
        # the delimiter followed by `)` and runs the rest of that line as code.
        # A body line that starts with the delimiter, such as "EOF)", "EOF ",
        # or "\tEOF", leaves the span to the checks on the whole command.
        if any(line.lstrip().startswith(delimiter) for line in lines[:end]):
            return command
        rest = "\n".join(lines[end + 1 :])
        if not rest.lstrip().startswith(')"'):
            return command
        command = prefix + '""' + rest.lstrip()[2:]


def without_heredoc_bodies(command: str, commenters: str) -> tuple[str, bool]:
    """Returns (text, certain): the command without here-document bodies.

    certain is False when a body expands $(...) or backticks, which run before
    the command's redirects, or when a body has no closing delimiter. A `<<`
    that the lexer does not see as an operator, such as one inside quotes or
    arithmetic, starts no body. That includes a line that begins inside a
    quote opened on an earlier line, which shows as the kept text so far not
    tokenizing, and a `<<` after text whose quotes shlex may misplace.
    """
    kept, pending, certain, depth = [], [], True, 0
    for line in command.split("\n"):
        if pending:
            strip_tabs, quoted, delimiter = pending[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                pending.pop(0)
            elif not quoted and ("$(" in line or "`" in line):
                certain = False
            continue
        match = HEREDOC.search(line)
        in_quote = match is not None and (
            not tokenizes("\n".join(kept), commenters)
            or may_misplace_quotes("\n".join([*kept, line[: match.start()]]))
        )
        kept.append(line)
        line, depth = without_arithmetic(line, depth)
        found = [] if in_quote else HEREDOC.findall(line)
        operators = heredoc_operators(line, commenters) if found else []
        if found and operators is not None and len(operators) == len(found):
            pending = [(dash == "-", bool(quote), word) for dash, quote, word in found]
    return "\n".join(kept), certain and not pending


def command_tokens(command: str, commenters: str) -> list[str]:
    """Tokenizes the command, leaving out here-document bodies that are data.

    Raises ValueError when the command does not tokenize.
    """
    text, certain = without_heredoc_bodies(command, commenters)
    return tokenize(text if certain else command, commenters)


def command_words(command: str, commenters: str) -> set[str]:
    """Returns the words of the whole command, here-document bodies included.

    A body need not tokenize, as with an apostrophe in prose, so a command that
    does not split falls back to rough words.
    """
    try:
        return set(tokenize(command, commenters))
    except ValueError:
        return set(ROUGH_WORD.findall(command))


def redirect_operator(token: str) -> str | None:
    """Returns the redirect part of a punctuation token, or None if it has none.

    shlex fuses adjacent punctuation, so `;>` or `)>` arrive as one token; the
    operator is whatever follows the last command separator.
    """
    if ">" not in token or not is_punctuation(token):
        return None
    if "(" in token:
        return token
    operator = re.split(r"[;)]", token)[-1]
    return operator if ">" in operator else None


def blocked_targets(command: str, root_cwd: str, cwd: str | None = None) -> list[str]:
    """Returns the redirect targets of the command outside the allowed paths.

    A directory change counts even inside a here-document body, so that a
    misread here-document operator cannot hide it.
    """
    cwd = os.path.join(root_cwd, cwd) if cwd else root_cwd
    changes_directory = any(
        DIRECTORY_CHANGES & command_words(command, commenters)
        for commenters in COMMENT_MODES
    )

    def is_blocked(target: str) -> bool:
        path = resolve(target, cwd)
        return (
            path is None
            or not is_allowed(path, root_cwd)
            or (changes_directory and not os.path.isabs(os.path.expanduser(target)))
        )

    blocked = []
    for commenters in COMMENT_MODES:
        try:
            tokens = command_tokens(command, commenters)
        except ValueError:
            if ">" in command:
                blocked.append(command)
            continue
        for index, token in enumerate(tokens):
            operator = redirect_operator(token)
            if operator is None:
                continue
            if "(" in operator:
                blocked.append(token)
                continue
            if index + 1 == len(tokens):
                continue
            target = tokens[index + 1]
            # Bash writes to a file named after the `!` word itself, and zsh
            # to the rest of the word or, for a bare `!`, the next word, so
            # every one of them must be allowed.
            targets = [target]
            if target == CLOBBER and index + 2 < len(tokens):
                targets.append(tokens[index + 2])
            elif target.startswith(CLOBBER) and target != CLOBBER:
                targets.append(target[len(CLOBBER) :])
            if operator.endswith("&") and (target.isdigit() or target == "-"):
                continue
            blocked += [path for path in targets if is_blocked(path)]
    return list(dict.fromkeys(blocked))


def secret_paths(command: str, root_cwd: str, cwd: str | None = None) -> list[str]:
    """Returns the words of the command that reach a location in SECRET_PATTERNS.

    Every word counts, `<` sources included, after expanding `~`, $HOME,
    braces, and globs and resolving symlinks. A command that does not tokenize falls back to rough
    words, and so, in addition to its tokens, does one whose quotes shlex may
    misplace (may_misplace_quotes), since a path bash reads as a word may sit
    inside one of shlex's strings.
    """
    cwd = os.path.join(root_cwd, cwd) if cwd else root_cwd
    found = []
    for commenters in COMMENT_MODES:
        try:
            words = command_tokens(command, commenters)
        except ValueError:
            words = ROUGH_WORD.findall(command)
        else:
            if may_misplace_quotes(command):
                words += ROUGH_WORD.findall(command)
        found += [
            word
            for word in words
            if not is_punctuation(word) and reaches_secret(word, cwd)
        ]
    return list(dict.fromkeys(found))


def reaches_secret(word: str, cwd: str) -> bool:
    """Returns whether any brace expansion of word reaches a secret location.

    A word with too many brace expansions to check counts as reaching one.
    """
    alternatives = brace_alternatives(word)
    if alternatives is None:
        return True
    return any(
        is_secret(path)
        for alternative in alternatives
        for path in input_paths(alternative, cwd)
    )


def quoting_hazard(command: str) -> str | None:
    """Returns why the command's redirects cannot be checked, or None.

    shlex does not parse bash's ANSI-C quoting, so with $'...' it may see a
    redirect or here-document boundary inside a string, or a string where bash
    sees a redirect. With $(...), ${...}, or backticks inside double quotes,
    bash parses a nested command whose redirects shlex reads as part of the
    string, so a `>` inside a token counts as a redirect.
    """
    if ANSI_C_QUOTE in command and (">" in command or "<<" in command):
        return (
            "this command combines ANSI-C quoting ($'...') with a redirect or a"
            " here-document, and bash ends $'...' strings where this hook cannot"
            " tell. Rewrite the command without $'...', for example with printf"
            " and a single-quoted format, or use the write tool for the file."
        )
    if not may_misplace_quotes(command):
        return None
    for commenters in COMMENT_MODES:
        try:
            tokens = command_tokens(command, commenters)
        except ValueError:
            continue
        if any(">" in token and not is_punctuation(token) for token in tokens):
            return (
                "this command has `>` inside a double-quoted string that also"
                " holds $(...), ${...}, or backticks, which bash parses as"
                " nested code with redirects of its own. Run the substitution"
                " or the redirect as a command of its own, or use the write"
                " tool for the file."
            )
    return None


def read_input() -> tuple[str, str, str | None]:
    """Returns (command, root_cwd, tool cwd) from the PreToolUse payload.

    Raises ValueError when stdin is not JSON and TypeError when the payload
    does not have the expected shape.
    """
    data = json.load(sys.stdin)
    if not isinstance(data, dict):
        raise TypeError("the payload is not a JSON object")
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        raise TypeError("tool_input is not an object")
    command = tool_input.get("command") or ""
    root_cwd = data.get("cwd") or os.getcwd()
    cwd = tool_input.get("cwd")
    if not isinstance(command, str):
        raise TypeError("tool_input.command is not a string")
    if not isinstance(root_cwd, str) or not isinstance(cwd, (str, type(None))):
        raise TypeError("cwd is not a string")
    return command, root_cwd, cwd


def main() -> int:
    try:
        command, root_cwd, cwd = read_input()
    except (TypeError, ValueError) as error:
        # A payload the hook cannot read may hide a redirect, so it blocks.
        print(f"Blocked: cannot read the hook input: {error}.", file=sys.stderr)
        return 2
    # Redirects are checked without literal here-document bodies; the secret
    # path check still reads them.
    code = without_literal_substitutions(command)
    hazard = quoting_hazard(code)
    if hazard:
        print(f"Blocked: {hazard}", file=sys.stderr)
        return 2
    blocked = blocked_targets(code, root_cwd, cwd)
    if blocked:
        print(
            f"Blocked: this command writes output to {', '.join(blocked)}, which is"
            " outside the paths Kiro may write without asking (the working"
            " directory, /tmp, ~/Desktop, ~/Downloads) or cannot be resolved"
            " before the command runs. Use the write tool for that file so Kiro"
            " can ask for approval, or run the redirect as a command of its own.",
            file=sys.stderr,
        )
        return 2
    secrets = secret_paths(command, root_cwd, cwd)
    if secrets:
        reason = (
            f"This command reaches {', '.join(secrets)}, a location that may hold"
            " credentials, once ~, $HOME, braces, globs, and symlinks are expanded."
        )
        print(
            json.dumps(
                {
                    "hookSpecificOutput": {
                        "permissionDecision": "ask",
                        "permissionDecisionReason": reason,
                    }
                }
            )
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
