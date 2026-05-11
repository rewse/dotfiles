#!/bin/bash
input=$(cat)

MODEL=$(echo "$input" | jq -r '.model.display_name // "unknown"')
PCT=$(echo "$input" | jq -r '.context_window.used_percentage // 0' | awk '{printf "%.0f", $1}')
DIR=$(echo "$input" | jq -r '.workspace.current_dir // ""')

# Color coding for context percentage
if [ "$PCT" -ge 80 ]; then
    PCT_COLOR="\033[31m"  # red
elif [ "$PCT" -ge 50 ]; then
    PCT_COLOR="\033[33m"  # yellow
else
    PCT_COLOR="\033[32m"  # green
fi
RESET="\033[0m"

# Shorten home dir to ~
DIR="${DIR/#$HOME/~}"

echo -e "${MODEL} | ${PCT_COLOR}${PCT}%${RESET} | ${DIR}"
