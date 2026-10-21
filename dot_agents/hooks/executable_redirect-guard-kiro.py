#!/usr/bin/env python3
"""Kiro CLI PreToolUse hook that blocks shell redirects outside allowed paths.

Kiro strips redirections before matching a shell command against its
permission rules and never checks the redirect target as an fs_write, so
`echo x > ~/.zshrc` runs without a prompt under an `echo *` allow. This hook
blocks (exit 2) any redirect whose target is outside the paths that
permissions.yaml lets Kiro write without asking, which sends the model to the
write tool, where Kiro asks for approval.

Targets it cannot resolve statically (variables, command substitution, globs,
process substitution) are blocked too. A command that does not tokenize, such
as one with an unbalanced quote, passes because bash rejects it anyway.

The allowed working directory is the session's cwd from the harness. The
model can set tool_input.cwd, so that value only resolves relative targets and
never widens the allowed paths.
"""

import json
import os
import re
import shlex
import sys

DEVICES = {"/dev/null", "/dev/stderr", "/dev/stdin", "/dev/stdout", "/dev/tty"}
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
    path = os.path.expanduser(target)
    return os.path.realpath(os.path.join(cwd, path))


def is_allowed(path, root_cwd):
    if path in DEVICES or path.startswith("/dev/fd/"):
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


def blocked_targets(command, root_cwd, cwd=None):
    cwd = os.path.join(root_cwd, cwd) if cwd else root_cwd
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    # Bash starts a comment only at a word boundary, so `x#y > f` is a redirect.
    lexer.commenters = ""
    try:
        tokens = list(lexer)
    except ValueError:
        return []
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
        if path is None or not is_allowed(path, root_cwd):
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
        f"Blocked: this command redirects output to {', '.join(blocked)}, outside the"
        " paths Kiro may write without asking (the working directory, /tmp,"
        " ~/Desktop, ~/Downloads). Use the write tool for that file so Kiro can"
        " ask for approval.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
