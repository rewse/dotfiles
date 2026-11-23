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
an apostrophe, cannot redirect output and passes. Bash also starts a comment
only at a word boundary, so `x#y > f` still redirects. shlex can treat `#` as
always or never starting a comment, so every check runs in both modes
(COMMENT_MODES) and combines the results.

Some auto-approved commands, such as sort, tree, and tvly, write the file named
by an output option. permissions.yaml sends those options to a prompt, but its
globs cannot tell an output option attached to other short flags (sort -uo/f,
tree -noC f) from a file name, so this hook checks that file like a redirect
target (OUTPUT_OPTIONS).

A target can also resolve elsewhere once earlier parts of the command run. A
relative target is blocked when the command contains cd, pushd, or popd. In a
compound command (one with ;, &&, ||, |, &, a subshell, a command
substitution, or a second line outside a here-document body) that also runs
a command able to create a symlink (LINK_COMMANDS), a target that does not
exist yet, or that has a missing parent below its allowed root, is blocked
too, because that part could create it as a symlink first. A path that
exists but is replaced earlier in the same command, as with rm and then ln, is
out of scope: Kiro prompts for such commands, since rm and ln are not
auto-approved.

The allowed working directory is the session's cwd from the harness. The
model can set tool_input.cwd, so that value only resolves relative targets and
never widens the allowed paths.
"""

import collections
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
    "*credentials*",
    "*id_ed25519*",
    "*id_rsa*",
    "*mcporter.json*",
)
# shlex comment characters for each tokenizing pass. Without comments, an
# apostrophe in each of two comments joins the lines between them into one
# string; with them, `x#y` loses the rest of its line.
COMMENT_MODES = ("", "#")


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


def tokenize(command, commenters):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    lexer.commenters = commenters
    return list(lexer)


def secret_inputs(command, root_cwd, cwd=None):
    """Returns the `<` targets of the command that may hold credentials.

    Here-documents, here-strings, `<&` duplication, and process substitution
    read no named file; `<>` also writes, so blocked_targets checks it.
    """
    cwd = os.path.join(root_cwd, cwd) if cwd else root_cwd
    found = []
    for commenters in COMMENT_MODES:
        try:
            tokens = tokenize(command, commenters)
        except ValueError:
            if "<" in command and is_secret(command):
                found.append(command)
            continue
        # Python 3.9, which Kiro may run hooks with, lacks itertools.pairwise.
        found += [
            tokens[index + 1]
            for index, token in enumerate(tokens[:-1])
            if set(token) <= PUNCTUATION
            and token.lstrip(";)|&") == "<"
            and any(is_secret(path) for path in input_paths(tokens[index + 1], cwd))
        ]
    return list(dict.fromkeys(found))


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


class OutputOptions(
    collections.namedtuple("OutputOptions", "with_arguments long separate")
):
    """How a command names the file it writes through -o.

    with_arguments holds its short options that take an argument, o included.
    long holds the long options that name an output file or directory. When
    separate is false (getopt, commander, pflag, click), an option takes the
    rest of its word as its argument, or the next word if nothing is left.
    When it is true (tree), every option in a cluster takes the next unused
    word, so `-Lo 1 f` writes f.
    """

    __slots__ = ()


GETOPT_OUTPUT = ("--output",)
# Auto-approved commands that write a file through -o, keyed by the words that
# start them in permissions.yaml. A short option missing from with_arguments
# only makes the hook stricter, except for tree, whose list must be complete.
OUTPUT_OPTIONS = {
    # macOS and GNU base64.
    ("base64",): OutputOptions("biow", GETOPT_OUTPUT, False),
    # Global options only; subcommand options are left out.
    ("chezmoi",): OutputOptions("DSWco", GETOPT_OUTPUT, False),
    ("defuddle",): OutputOptions("loup", GETOPT_OUTPUT, False),
    ("docker", "compose", "config"): OutputOptions("fop", GETOPT_OUTPUT, False),
    ("docker-compose", "config"): OutputOptions("fop", GETOPT_OUTPUT, False),
    ("npx", "-y", "@firecrawl/anydoc"): OutputOptions("fo", GETOPT_OUTPUT, False),
    ("npx", "@firecrawl/anydoc"): OutputOptions("fo", GETOPT_OUTPUT, False),
    # BSD and GNU sort.
    ("sort",): OutputOptions("STkot", GETOPT_OUTPUT, False),
    ("tree",): OutputOptions("HILPTo", (), True),
    ("tvly",): OutputOptions("o", ("--output", "--output-dir"), False),
}
# A word that sets a variable for the command after it.
ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=.*", re.DOTALL)
# An output option after an OUTPUT_OPTIONS command, for text that does not split.
HIDDEN_OUTPUT_OPTION = re.compile(
    r"\b(?:"
    + "|".join(sorted({re.escape(p[-1].rsplit("/", 1)[-1]) for p in OUTPUT_OPTIONS}))
    + r")\b[^\n]*\s(?:--o|-[^\s-]*o)"
)
# Commands that can create a symlink from their arguments, or run code or
# other commands that can. Kiro asks before running any command it does not
# auto-approve, so the list is defense in depth for those and matters most for
# the auto-approved ones (git, tar, unzip, docker, npx, chezmoi). A command
# missing from it, such as rg or mkdir, cannot turn a missing redirect target
# into a link before bash opens it.
LINK_COMMANDS = re.compile(
    r"(?:ln|cp|mv|install|rsync|ditto|g?tar|bsdtar|unzip|cpio|pax|git|docker"
    r"|docker-compose|chezmoi|npx|npm|pnpm|yarn|uvx?|pip[0-9.]*|python[0-9.]*"
    r"|node|deno|bun|perl|ruby|php|osascript|g?awk|find|xargs|env|exec|eval"
    r"|sudo|command|builtin|source|\.|(?:ba|z|da|fi|k)?sh|make|tvly|mcporter"
    r"|agent-browser)"
)


def split_lines(text, commenters=""):
    """Splits text like blocked_targets does, but keeps newlines as tokens."""
    if commenters:
        # shlex drops the newline that ends a comment; doubling every newline
        # keeps one as a separator.
        text = text.replace("\n", "\n\n")
    lexer = shlex.shlex(text, posix=True, punctuation_chars="();<>|&\n")
    lexer.whitespace_split = True
    lexer.whitespace = " \t\r"
    lexer.commenters = commenters
    return list(lexer)


def heredoc_operators(line, commenters):
    try:
        tokens = split_lines(line, commenters)
    except ValueError:
        return None
    return [t for t in tokens if set(t) <= PUNCTUATION and t.lstrip(";)|&") == "<<"]


def without_arithmetic(line, depth):
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


def without_heredoc_bodies(command, commenters):
    """Returns (text, certain): the command without here-document bodies.

    certain is False when a body expands $(...) or backticks, which run before
    the command's redirects, or when a body has no closing delimiter. A `<<`
    that the lexer does not see as an operator, such as one inside quotes or
    arithmetic, starts no body.
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
        kept.append(line)
        line, depth = without_arithmetic(line, depth)
        found = HEREDOC.findall(line)
        operators = heredoc_operators(line, commenters) if found else []
        if found and operators is not None and len(operators) == len(found):
            pending = [(dash == "-", bool(quote), word) for dash, quote, word in found]
    return "\n".join(kept), certain and not pending


def command_shape(command):
    """Returns (may_link, changes_directory) for the command.

    may_link is whether another part of the command could create a symlink
    before a redirect opens its target: the command is compound and some word
    in it names one of LINK_COMMANDS, or it runs text this hook cannot read
    (backticks, or a here-document body that expands commands or never ends).
    Separators and words inside a here-document body are data, so they do not
    count for may_link. changes_directory counts every word, bodies included,
    so that a misread here-document operator cannot hide a directory change. A
    command it cannot split counts as both. Each value is true if it is true in
    either of COMMENT_MODES.
    """
    shapes = [split_shape(command, commenters) for commenters in COMMENT_MODES]
    return any(link for link, _ in shapes), any(cd for _, cd in shapes)


def split_shape(command, commenters):
    text, certain = without_heredoc_bodies(command, commenters)
    # Bash joins a line that ends with a backslash to the next one.
    text = text.replace("\\\n", "").rstrip()
    try:
        tokens = split_lines(text, commenters)
    except ValueError:
        return True, True
    changes_directory = bool(DIRECTORY_CHANGES & command_words(command, commenters))
    if not certain or "`" in text:
        return True, changes_directory
    compound = any(
        set(t) <= PUNCTUATION | {"\n"} and not REDIRECT_ONLY.fullmatch(t)
        for t in tokens
    )
    may_link = compound and any(
        LINK_COMMANDS.fullmatch(os.path.basename(t)) for t in tokens
    )
    return may_link, changes_directory


def command_words(command, commenters):
    """Returns the words of the whole command, here-document bodies included.

    A body need not tokenize, as with an apostrophe in prose, so a command that
    does not split falls back to every run of word characters.
    """
    try:
        return set(split_lines(command, commenters))
    except ValueError:
        return set(re.findall(r"[\w.-]+", command))


def output_targets(command, commenters):
    """Returns the files that OUTPUT_OPTIONS commands write through -o.

    The option may share a word with other short flags, and these tools accept
    it after operands. GNU tools also accept any abbreviation of a long output
    option, which this treats as true for all of them. A command that does not
    split counts as writing the whole command if it looks like one.
    """
    try:
        tokens = split_lines(command, commenters)
    except ValueError:
        return [command] if HIDDEN_OUTPUT_OPTION.search(command) else []
    targets, index, at_command = [], 0, True
    while index < len(tokens):
        token = tokens[index]
        if set(token) <= PUNCTUATION | {"\n"}:
            index += 1
            if REDIRECT_ONLY.fullmatch(token):
                index += 1
            else:
                at_command = True
        elif at_command and not ASSIGNMENT.fullmatch(token):
            at_command = False
            prefix = command_prefix(tokens, index)
            if prefix is None:
                index += 1
                continue
            found, index = option_targets(
                tokens, index + len(prefix), OUTPUT_OPTIONS[prefix]
            )
            targets += found
        else:
            index += 1
    return targets


def command_prefix(tokens, index):
    """Returns the longest OUTPUT_OPTIONS key that starts tokens[index:]."""
    words = (os.path.basename(tokens[index]), *tokens[index + 1 :])
    found = [key for key in OUTPUT_OPTIONS if words[: len(key)] == key]
    return max(found, key=len) if found else None


def argument(tokens, index):
    """Returns (word, index): the next argument the command sees, and the index after it.

    Bash removes redirections before the command runs. shlex splits `2>f`
    into `2` and `>`, so a number right before a redirect operator counts as
    its file descriptor; when it is an argument instead, the guard checks a
    later word, which only makes it stricter. A missing argument is "".
    """
    while index < len(tokens):
        token = tokens[index]
        if REDIRECT_ONLY.fullmatch(token):
            index += 2
        elif (
            token.isdigit()
            and index + 1 < len(tokens)
            and REDIRECT_ONLY.fullmatch(tokens[index + 1])
        ):
            index += 3
        elif set(token) <= PUNCTUATION | {"\n"}:
            break
        else:
            return token, index + 1
    return "", index


def option_targets(tokens, index, options):
    """Returns (targets, index): the output arguments from tokens[index] on.

    options is the command's OutputOptions. index ends at the first word that
    is not an option or operand.
    """
    targets = []
    while index < len(tokens):
        token = tokens[index]
        if set(token) <= PUNCTUATION | {"\n"}:
            if not REDIRECT_ONLY.fullmatch(token):
                break
            index += 2
            continue
        index += 1
        if token == "--":
            break
        if token.startswith("--"):
            name, equals, value = token.partition("=")
            if len(name) > 2 and any(long.startswith(name) for long in options.long):
                if not equals:
                    value, index = argument(tokens, index)
                targets.append(value)
        elif token.startswith("-") and options.separate:
            flags = token[1:]
            values = []
            for _ in range(sum(flag in options.with_arguments for flag in flags)):
                value, index = argument(tokens, index)
                values.append(value)
            if "o" in flags:
                targets += values
        elif token.startswith("-"):
            for position, flag in enumerate(token[1:], start=2):
                if flag not in options.with_arguments:
                    continue
                value = token[position:]
                if not value:
                    value, index = argument(tokens, index)
                if flag == "o":
                    targets.append(value)
                    # pflag drops an = between a short option and its value.
                    if value.startswith("="):
                        targets.append(value[1:])
                break
    return targets, index


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
    may_link, changes_directory = command_shape(command)

    def is_blocked(target):
        path = resolve(target, cwd)
        return (
            path is None
            or not is_allowed(path, root_cwd)
            or (changes_directory and not os.path.isabs(os.path.expanduser(target)))
            or (may_link and missing_below_root(path, root_cwd))
        )

    blocked = []
    for commenters in COMMENT_MODES:
        outputs = output_targets(command, commenters)
        try:
            tokens = tokenize(command, commenters)
        except ValueError:
            if ">" in command or outputs:
                blocked.append(command)
            continue
        blocked += redirect_targets(tokens, is_blocked)
        blocked += [t for t in outputs if is_blocked(t)]
    return list(dict.fromkeys(blocked))


def redirect_targets(tokens, is_blocked):
    """Returns the redirect targets in the tokens that the guard blocks."""
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
        if is_blocked(target):
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
        f"Blocked: this command writes output to {', '.join(blocked)}, which is"
        " outside the paths Kiro may write without asking (the working"
        " directory, /tmp, ~/Desktop, ~/Downloads) or may resolve there once"
        " earlier parts of the command run. Use the write tool for that file so"
        " Kiro can ask for approval, or run the redirect as a command of its own.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
