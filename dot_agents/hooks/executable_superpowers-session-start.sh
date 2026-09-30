#!/bin/bash
# superpowers-session-start: Inject the using-superpowers skill at session
# start, as obra/superpowers' own SessionStart hook does for its plugin.
# Used as a SessionStart hook for Claude Code and Kiro CLI. Codex gets no hook:
# upstream dropped its Codex bootstrap because Codex triggers the skill from
# its native skill discovery and the injection made the UX worse.
#
# Usage: superpowers-session-start.sh <claude|kiro>
#
# The skill comes from the skills CLI install in ~/.agents/skills rather than
# a plugin root. Claude Code reads hookSpecificOutput.additionalContext; Kiro
# injects the raw stdout of a SessionStart hook that exits 0.

set -euo pipefail

skill_dir="$HOME/.agents/skills/using-superpowers"
[[ -r "$skill_dir/SKILL.md" ]] || exit 0

case "${1:-}" in
  claude) loader="use the 'Skill' tool" ;;
  kiro) loader="load them through your harness's native skill support" ;;
  *)
    echo "usage: $0 <claude|kiro>" >&2
    exit 1
    ;;
esac

# Injected text loses the skill's location, so name it for references/ paths.
context="<EXTREMELY_IMPORTANT>
You have superpowers.

**Below is the full content of your 'superpowers:using-superpowers' skill - your introduction to using skills. Its relative paths resolve against ${skill_dir}. For all other skills, ${loader}:**

$(cat "$skill_dir/SKILL.md")
</EXTREMELY_IMPORTANT>"

if [[ "$1" == kiro ]]; then
  printf '%s\n' "$context"
else
  jq -n --arg context "$context" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $context}}'
fi
