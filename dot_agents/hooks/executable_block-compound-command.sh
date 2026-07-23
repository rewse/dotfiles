#!/bin/bash
# block-compound-command: Block long compound commands that tend to hang the
# Claude Code Bash tool. A command is blocked only when it BOTH chains 2+ shell
# operators (; && || |) AND exceeds the length threshold, so single commands of
# any length and short compounds (e.g. `gh ... | cat`) still pass.
# Used as a preToolUse hook for both Kiro CLI and Claude Code.

set -euo pipefail

MAX_LENGTH=250
MAX_OPERATORS=1  # blocked when operator count is strictly greater than this

COMMAND=$(jq -r '.tool_input.command // ""')

length=${#COMMAND}
if [[ "$length" -le "$MAX_LENGTH" ]]; then
  exit 0
fi

# Count shell operators: ; && || |  (&& and || count as one operator each).
operators=$(printf '%s' "$COMMAND" | grep -oE '(\|\||&&|;|\|)' | grep -c '.' || true)
if [[ "$operators" -le "$MAX_OPERATORS" ]]; then
  exit 0
fi

cat >&2 <<EOF
Blocked: long compound command ($length chars, $operators shell operators).

Compound one-liners this long tend to hang the Claude Code Bash tool. Split it
into single commands and run them one at a time. Each command runs in the same
working directory context, so sequential separate calls behave the same.
EOF
exit 2
