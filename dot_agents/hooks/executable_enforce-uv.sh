#!/bin/bash
# enforce-uv: Block pip/venv/virtualenv commands and suggest uv instead.
# Used as a preToolUse hook for both Kiro CLI and Claude Code.

set -euo pipefail

COMMAND=$(jq -r '.tool_input.command // ""')

# Split on shell operators and check each subcommand
while IFS= read -r subcmd; do
  # Trim leading whitespace
  subcmd="${subcmd#"${subcmd%%[![:space:]]*}"}"
  # Strip leading env assignments (VAR=value ...)
  while [[ "$subcmd" =~ ^[A-Za-z_][A-Za-z0-9_]*= ]]; do
    subcmd="${subcmd#* }"
  done

  if [[ "$subcmd" =~ ^(pip|pip3)(\ |$) ]] ||
     [[ "$subcmd" =~ ^(python|python3)\ +-m\ +venv(\ |$) ]] ||
     [[ "$subcmd" =~ ^virtualenv(\ |$) ]]; then
    SKILL_FILE="$HOME/.agents/skills/python-dependency/SKILL.md"
    if [[ -f "$SKILL_FILE" ]]; then
      cat "$SKILL_FILE" >&2
    else
      echo "Use uv instead of pip/venv/virtualenv. See the python-dependency skill." >&2
    fi
    exit 2
  fi
done <<< "$(echo "$COMMAND" | sed 's/[;&|]\{1,2\}/\n/g')"

exit 0
