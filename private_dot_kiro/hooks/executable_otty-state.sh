#!/bin/sh
# Otty state bridge for Kiro CLI.
#
# Sets the tab badge of the pane Kiro runs in. Kiro runs hooks inside the aim
# sandbox, which forbids process inspection, so `otty state:kiro agent-pid=...`
# silently matches no pane and focus-based lookups can hit another tab. The
# pane id comes from OTTY_PANE_ID, which Otty exports into every pane, and
# `otty pane show` resolves it to the tab over IPC on each call because a pane
# can move between tabs.
#
# Usage: ~/.kiro/hooks/otty-state.sh <state>
#
# States:
#   idle       → "finished" dot (turn complete)
#   processing → "running" spinner
#   awaiting   → "awaiting-input" hand icon

CLI="${OTTY_CLI:-/usr/local/bin/otty}"

[ -n "${OTTY_PANE_ID:-}" ] || exit 0

tab_id=$("$CLI" pane show "$OTTY_PANE_ID" --json 2>/dev/null \
    | sed -n 's/.*"tab_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -n 1)
[ -n "$tab_id" ] || exit 0

case "$1" in
    processing) kind=running ;;
    idle)       kind=finished ;;
    awaiting)   kind=awaiting-input ;;
    *)          kind= ;;
esac

if [ -n "$kind" ]; then
    "$CLI" tab badge --tab "$tab_id" --kind "$kind" -q >/dev/null 2>&1 &
else
    "$CLI" tab badge --tab "$tab_id" --clear -q >/dev/null 2>&1 &
fi
