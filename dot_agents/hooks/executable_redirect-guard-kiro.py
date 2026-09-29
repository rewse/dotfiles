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
"""

import json
import os
import shlex
import sys

DEVICES = {"/dev/null", "/dev/stderr", "/dev/stdin", "/dev/stdout", "/dev/tty"}
UNRESOLVABLE = set("$`*?[(")
REDIRECT_CHARS = set("<>|&")


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


def is_allowed(path, cwd):
    if path in DEVICES or path.startswith("/dev/fd/"):
        return True
    return any(
        path == root or path.startswith(root + os.sep) for root in allowed_roots(cwd)
    )


def blocked_targets(command, cwd):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        tokens = list(lexer)
    except ValueError:
        return []
    blocked = []
    for index, token in enumerate(tokens):
        if ">" not in token or not set(token) <= REDIRECT_CHARS | {"("}:
            continue
        if "(" in token:
            blocked.append(token)
            continue
        if index + 1 == len(tokens):
            continue
        target = tokens[index + 1]
        if token.endswith("&") and (target.isdigit() or target == "-"):
            continue
        path = resolve(target, cwd)
        if path is None or not is_allowed(path, cwd):
            blocked.append(target)
    return blocked


def main():
    data = json.load(sys.stdin)
    tool_input = data.get("tool_input") or {}
    command = tool_input.get("command") or ""
    cwd = tool_input.get("cwd") or data.get("cwd") or os.getcwd()
    blocked = blocked_targets(command, cwd)
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
