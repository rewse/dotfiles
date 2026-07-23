#!/bin/bash
# block-compound-command: Block long compound commands that tend to hang the
# Claude Code Bash tool. A command is blocked only when it BOTH chains 2+ shell
# operators (; && || |) AND exceeds the length threshold, so single commands of
# any length and short compounds (e.g. `gh ... | cat`) still pass. Only operators
# outside quotes count, so `git commit -m "a && b"` and `ssh 'a; b'` never trip it.
# Used as a preToolUse hook for both Kiro CLI and Claude Code.

set -euo pipefail

MAX_LENGTH=250
MAX_OPERATORS=1  # blocked when operator count is strictly greater than this

COMMAND=$(jq -r '.tool_input.command // ""')

length=${#COMMAND}
if [[ "$length" -le "$MAX_LENGTH" ]]; then
  exit 0
fi

# Count shell operators (; && || |) that sit OUTSIDE quotes. Operators inside
# single/double quotes are literal text, not command separators, so counting
# them would wrongly flag things like `git commit -m "a && b"` or `ssh 'a; b'`.
# && and || each count as one operator.
operators=0
in_single=0
in_double=0
i=0
while [[ "$i" -lt "$length" ]]; do
  ch="${COMMAND:$i:1}"
  next="${COMMAND:$((i + 1)):1}"
  if [[ "$in_single" -eq 1 ]]; then
    [[ "$ch" == "'" ]] && in_single=0
    i=$((i + 1))
    continue
  fi
  if [[ "$in_double" -eq 1 ]]; then
    if [[ "$ch" == '\' ]]; then
      i=$((i + 2))  # skip escaped char inside double quotes
      continue
    fi
    [[ "$ch" == '"' ]] && in_double=0
    i=$((i + 1))
    continue
  fi
  case "$ch" in
    "'") in_single=1; i=$((i + 1)); continue ;;
    '"') in_double=1; i=$((i + 1)); continue ;;
    '\') i=$((i + 2)); continue ;;  # escaped char outside quotes
  esac
  if [[ "$ch" == '&' && "$next" == '&' ]] || [[ "$ch" == '|' && "$next" == '|' ]]; then
    operators=$((operators + 1))
    i=$((i + 2))
    continue
  fi
  if [[ "$ch" == ';' || "$ch" == '|' ]]; then
    operators=$((operators + 1))
  fi
  i=$((i + 1))
done

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
