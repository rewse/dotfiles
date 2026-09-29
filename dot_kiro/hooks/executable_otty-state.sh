#!/bin/sh
# Otty state bridge for Kiro CLI.
#
# Reports Kiro as an Otty custom agent through `otty state:kiro`, which drives
# the tab badge and notifications. Otty pins the event to a pane by agent-pid:
# the hook's parent is a descendant of the pane's shell, and later events with
# the same session-id reach that pane too.
#
# Usage: ~/.kiro/hooks/otty-state.sh <state>
#
# States:
#   idle       → turn finished
#   processing → turn in progress
#   awaiting   → waiting for approval or input

CLI="${OTTY_CLI:-/usr/local/bin/otty}"

"$CLI" state:kiro \
    state="$1" \
    agent-pid="$PPID" \
    session-id="${KIRO_SESSION_ID:-}" \
    label=Kiro \
    >/dev/null 2>&1 &
