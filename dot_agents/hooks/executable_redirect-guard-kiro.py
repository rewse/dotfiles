#!/usr/bin/env python3
"""Kiro CLI PreToolUse hook that blocks shell redirects outside allowed paths.

Kiro strips redirections before matching a shell command against its
permission rules and never checks the redirect target as an fs_write, so
`echo x > ~/.zshrc` runs without a prompt under an `echo *` allow. This hook
blocks (exit 2) any redirect whose target is outside the paths that
permissions.yaml lets Kiro write without asking, which sends the model to the
write tool, where Kiro asks for approval.

Targets it cannot resolve statically (variables, command substitution, globs,
process substitution) are blocked too, and so is a command that contains `>`
but does not tokenize, such as one with an unbalanced quote: bash may still
run it, because a quote inside a comment (`> ~/.zshrc #'`) does not start a
string. An untokenizable command without `>`, such as a heredoc whose body has
an apostrophe, cannot redirect output and passes.

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

import json
import os
import re
import shlex
import sys

DEVICES = {"/dev/null", "/dev/stderr", "/dev/stdin", "/dev/stdout"}
UNRESOLVABLE = set("$`*?[(")
# shlex's default punctuation_chars; it fuses adjacent ones into one token.
PUNCTUATION = set("();<>|&")


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
    """Returns (may_link, changes_directory) for the command.

    may_link is whether another part of the command could create a symlink
    before a redirect opens its target: the command is compound and some word
    in it names one of LINK_COMMANDS, or it runs text this hook cannot read
    (backticks, or a here-document body that expands commands or never ends).
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
    if not certain or "`" in text:
        return True, bool(DIRECTORY_CHANGES & set(tokens))
    compound = any(
        set(t) <= PUNCTUATION | {"\n"} and not REDIRECT_ONLY.fullmatch(t)
        for t in tokens
    )
    may_link = compound and any(
        LINK_COMMANDS.fullmatch(os.path.basename(t)) for t in tokens
    )
    return may_link, bool(DIRECTORY_CHANGES & set(tokens))


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
    may_link, changes_directory = command_shape(command)
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
            or (may_link and missing_below_root(path, root_cwd))
        ):
            blocked.append(target)
    return blocked


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""
    root_cwd = data.get("cwd") or os.getcwd()
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
