# Claude Code Bash Hangs

Rules to avoid hangs specific to Claude Code's Bash tool. These do not apply to other CLIs (Codex, Kiro, etc.), which do not inject the shell wrappers described below.

## Prefix `grep` and `rg` with `command`

Inside a Bash tool call, always run `command grep` and `command rg` instead of bare `grep` / `rg`. Claude Code injects zsh shell functions that shadow `grep` and `rg` and route them through the `claude` CLI (as `ugrep -G ...` for grep, and as native rg for rg). Those wrappers can hang for reasons unrelated to the pattern — subprocess startup, session state, or the ugrep emulation itself — and `timeout` does not help because the grandchild is reparented and keeps running.

The bounded-quantifier case is one instance of this failure mode. The wrapped `grep` (ugrep) grows memory without bound on patterns like `grep -oE '.{60}receipt.{80}' file`, producing no output until the host OOMs. See [anthropics/claude-code#74143](https://github.com/anthropics/claude-code/issues/74143).

Safe forms:

- `command grep` (bare GNU grep, no wrapper)
- `command rg` (bare ripgrep, no wrapper)
- The Grep tool

To capture surrounding context, prefer `grep -B/-A` over a bounded-quantifier wildcard.
