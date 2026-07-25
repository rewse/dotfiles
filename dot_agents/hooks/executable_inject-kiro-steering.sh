#!/bin/bash
# inject-kiro-steering: Feed .kiro/steering/*.md into the session at startup.
# Used as a SessionStart hook for Claude Code, which has no native reader for
# that directory. Kiro CLI loads it itself and must not run this hook.

set -euo pipefail

INPUT=$(cat 2>/dev/null || true)
CWD=$(printf '%s' "$INPUT" | jq -r '.cwd // empty' 2>/dev/null || true)
[[ -n "$CWD" ]] || CWD="$PWD"

STEERING_DIR="$CWD/.kiro/steering"
[[ -d "$STEERING_DIR" ]] || exit 0

# Sort so the same project always produces the same order.
FILES=()
while IFS= read -r file; do
  FILES+=("$file")
done < <(find "$STEERING_DIR" -name '*.md' -type f | sort)

[[ ${#FILES[@]} -gt 0 ]] || exit 0

BODY=$(cat "${FILES[@]}")

# SessionStart output is capped at 10000 characters; past that Claude Code
# swaps the text for a file path, which loses the content. List the files
# instead and let the agent read the ones it needs.
if [[ ${#BODY} -gt 9000 ]]; then
  echo "This project keeps its conventions in these steering files. Read them before working on the project:"
  printf '%s\n' "${FILES[@]}"
  exit 0
fi

# Frame the text as project information. Claude Code's prompt-injection
# defenses can surface injected text to the user instead of using it when it
# reads as an out-of-band system instruction.
echo "The following is the content of this project's steering files under .kiro/steering/, which describe its conventions:"
echo
printf '%s\n' "$BODY"
