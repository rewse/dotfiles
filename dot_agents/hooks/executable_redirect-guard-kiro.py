#!/usr/bin/env python3
"""Kiro CLI PreToolUse hook that blocks shell redirects outside allowed paths.

Kiro strips redirections before matching a shell command against its
permission rules and never checks the redirect target as an fs_write, so
`echo x > ~/.zshrc` runs without a prompt under an `echo *` allow. This hook
blocks (exit 2) any redirect whose target is outside the paths that
permissions.yaml lets Kiro write without asking, which sends the model to the
write tool, where Kiro asks for approval.

It also blocks a `<` input redirect from a location that may hold credentials
(SECRET_PATTERNS). The shell rules in permissions.yaml exclude the same
patterns from auto-approval, but cannot see a redirect once Kiro strips it. A
target matches as written, with `~` and globs expanded, and with symlinks
resolved; a target built from a variable matches only as written.

Targets it cannot resolve statically (variables, command substitution, globs,
process substitution) are blocked too, and so is a command that contains `>`
but does not tokenize, such as one with an unbalanced quote: bash may still
run it, because a quote inside a comment (`> ~/.zshrc #'`) does not start a
string. An untokenizable command without `>`, such as a heredoc whose body has
an apostrophe, cannot redirect output and passes.

A target can also resolve elsewhere once earlier parts of the command run. A
relative target is blocked when the command contains cd, pushd, or popd. In a
compound command (one with ;, &&, ||, |, &, a subshell, a command
substitution, or a second line outside a here-document body), a target that
does not exist yet, or that has a missing parent below its allowed root, is
blocked too, because an earlier part could create it as a symlink. A path that
exists but is replaced earlier in the same command, as with rm and then ln, is
out of scope: Kiro prompts for such commands, since rm and ln are not
auto-approved.

The allowed working directory is the session's cwd from the harness. The
model can set tool_input.cwd, so that value only resolves relative targets and
never widens the allowed paths.
"""

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
# `*`. Every shell rule in permissions.yaml excludes the same list.
SECRET_PATTERNS = (
    "*.aws",
    "*.aws *",
    "*.aws/*",
    "*.config/environment*",
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
    "*.op",
    "*.op *",
    "*.op/*",
    "*.ssh*",
    "*.tavily*",
    "*/environ*",
    "*/mcporter",
    "*/mcporter *",
    "*/mcporter/*",
    "*cloudfront-waf-report*",
    "*credentials*",
    "*id_ed25519*",
    "*id_rsa*",
    "*mcporter.json*",
)


def allowed_roots(cwd):
    home = os.path.expanduser("~")
    roots = [
        cwd,
        "/tmp",
        os.path.join(home, "Desktop"),
        os.path.join(home, "Downloads"),
    ]
    return [os.path.realpath(root) for root in roots]


def resolve(target, cwd):
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


def is_device(path):
    return path in DEVICES or path.startswith("/dev/fd/")


def is_allowed(path, root_cwd):
    if is_device(path):
        return True
    return any(
        path == root or path.startswith(root + os.sep)
        for root in allowed_roots(root_cwd)
    )


def is_secret(path):
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in SECRET_PATTERNS)


def input_paths(target, cwd):
    """Returns the target as written and the paths bash would read for it."""
    if "$" in target or "`" in target:
        return [target]
    path = os.path.join(cwd, os.path.expanduser(target))
    # Bash expands a glob in a redirect target when it matches one file.
    found = glob.glob(path) if set("*?[") & set(target) else [path]
    return [target, *found, *(os.path.realpath(p) for p in found)]


def secret_inputs(command, root_cwd, cwd=None):
    """Returns the `<` targets of the command that may hold credentials.

    Here-documents, here-strings, `<&` duplication, and process substitution
    read no named file; `<>` also writes, so blocked_targets checks it.
    """
    cwd = os.path.join(root_cwd, cwd) if cwd else root_cwd
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return [command] if "<" in command and is_secret(command) else []
    # Python 3.9, which Kiro may run hooks with, lacks itertools.pairwise.
    return [
        tokens[index + 1]
        for index, token in enumerate(tokens[:-1])
        if set(token) <= PUNCTUATION
        and token.lstrip(";)|&") == "<"
        and any(is_secret(path) for path in input_paths(tokens[index + 1], cwd))
    ]


def redirect_operator(token):
    """Returns the redirect part of a punctuation token, or None if it has none.

    shlex fuses adjacent punctuation, so `;>` or `)>` arrive as one token; the
    operator is whatever follows the last command separator.
    """
    if ">" not in token or not set(token) <= PUNCTUATION:
        return None
    if "(" in token:
        return token
    operator = re.split(r"[;)]", token)[-1]
    return operator if ">" in operator else None


# A punctuation token that only redirects, as opposed to one that separates
# commands or opens a subshell.
REDIRECT_ONLY = re.compile(r"&>>?|>>?|>\||>&|<<<|<<|<>|<&|<")
# A here-document operator and its delimiter, which may be quoted.
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)\s*(['\"]?)([^\s'\"();<>|&]+)\2")
DIRECTORY_CHANGES = {"cd", "popd", "pushd"}


def split_lines(text):
    """Splits text like blocked_targets does, but keeps newlines as tokens."""
    lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    lexer.commenters = ""
    return list(lexer)


def heredoc_operators(line):
    try:
        tokens = split_lines(line)
    except ValueError:
        return None
    return [t for t in tokens if set(t) <= PUNCTUATION and t.lstrip(";)|&") == "<<"]


def without_heredoc_bodies(command):
    """Returns (text, certain): the command without here-document bodies.

    certain is False when a body expands $(...) or backticks, which run before
    the command's redirects, or when a body has no closing delimiter. A `<<`
    that the lexer does not see as an operator, such as one inside quotes,
    starts no body.
    """
    kept, pending, certain = [], [], True
    for line in command.split("\n"):
        if pending:
            strip_tabs, quoted, delimiter = pending[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                pending.pop(0)
            elif not quoted and ("$(" in line or "`" in line):
                certain = False
            continue
        kept.append(line)
        found = HEREDOC.findall(line)
        operators = heredoc_operators(line) if found else []
        if found and operators is not None and len(operators) == len(found):
            pending = [(dash == "-", bool(quote), word) for dash, quote, word in found]
    return "\n".join(kept), certain and not pending


def command_shape(command):
    """Returns (compound, changes_directory) for the command.

    Separators and words inside a here-document body are data, so they count
    for neither. A command it cannot split counts as both.
    """
    text, certain = without_heredoc_bodies(command)
    # Bash joins a line that ends with a backslash to the next one.
    text = text.replace("\\\n", "").rstrip()
    try:
        tokens = split_lines(text)
    except ValueError:
        return True, True
    compound = (
        not certain
        or "`" in text
        or any(
            set(t) <= PUNCTUATION | {"\n"} and not REDIRECT_ONLY.fullmatch(t)
            for t in tokens
        )
    )
    return compound, bool(DIRECTORY_CHANGES & set(tokens))


def missing_below_root(path, root_cwd):
    """Returns whether the path, or a parent below its allowed root, is missing."""
    roots = [r for r in allowed_roots(root_cwd) if path.startswith(r + os.sep)]
    if is_device(path) or not roots:
        return False
    root = max(roots, key=len)
    while path != root:
        if not os.path.lexists(path):
            return True
        path = os.path.dirname(path)
    return False


def blocked_targets(command, root_cwd, cwd=None):
    cwd = os.path.join(root_cwd, cwd) if cwd else root_cwd
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    # Bash starts a comment only at a word boundary, so `x#y > f` is a redirect.
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return [command] if ">" in command else []
    compound, changes_directory = command_shape(command)
    blocked = []
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
        if operator.endswith("&") and (target.isdigit() or target == "-"):
            continue
        path = resolve(target, cwd)
        if (
            path is None
            or not is_allowed(path, root_cwd)
            or (changes_directory and not os.path.isabs(os.path.expanduser(target)))
            or (compound and missing_below_root(path, root_cwd))
        ):
            blocked.append(target)
    return blocked


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""
    root_cwd = data.get("cwd") or os.getcwd()
    secrets = secret_inputs(command, root_cwd, tool_input.get("cwd"))
    if secrets:
        print(
            f"Blocked: this command reads {', '.join(secrets)} through an input"
            " redirect, a location that may hold credentials. Use the read tool"
            " for that file so Kiro can ask for approval.",
            file=sys.stderr,
        )
        return 2
    blocked = blocked_targets(command, root_cwd, tool_input.get("cwd"))
    if not blocked:
        return 0
    print(
        f"Blocked: this command redirects output to {', '.join(blocked)}, which is"
        " outside the paths Kiro may write without asking (the working"
        " directory, /tmp, ~/Desktop, ~/Downloads) or may resolve there once"
        " earlier parts of the command run. Use the write tool for that file so"
        " Kiro can ask for approval, or run the redirect as a command of its own.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
