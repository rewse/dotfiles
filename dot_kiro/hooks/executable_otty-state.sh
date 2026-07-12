#!/bin/sh
# Otty state bridge for Kiro CLI.
#
# Sets tab badges via `otty-cli tab badge --tab <ID>` so the correct tab is
# targeted even when it is not focused. The tab ID is resolved at first
# invocation (while the pane IS focused) and cached per session.
#
# Usage: ~/.kiro/hooks/otty-state.sh <state>
#
# States:
#   idle       → "finished" dot (turn complete)
#   processing → "running" spinner
#   awaiting   → "awaiting-input" hand icon

CLI="${OTTY_CLI:-/usr/local/bin/otty}"
state="$1"

# --- Tab ID cache (keyed by session to support parallel sessions) ----------
CACHE_DIR="${TMPDIR:-/tmp}/otty-kiro"
CACHE_FILE="${CACHE_DIR}/${KIRO_SESSION_ID:-unknown}.tab"

resolve_tab_id() {
    tab_id=$("$CLI" pane show --json 2>/dev/null \
        | sed -n 's/.*"tab_id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
        | head -n 1)
    [ -z "$tab_id" ] && return 1
    mkdir -p "$CACHE_DIR"
    printf '%s' "$tab_id" > "$CACHE_FILE"
    echo "$tab_id"
}

TAB_ID=$(cat "$CACHE_FILE" 2>/dev/null)
[ -z "$TAB_ID" ] && TAB_ID=$(resolve_tab_id)
[ -z "$TAB_ID" ] && exit 0

# --- Set badge -------------------------------------------------------------
case "$state" in
    processing) "$CLI" tab badge --tab "$TAB_ID" --kind running -q 2>/dev/null & ;;
    idle)       "$CLI" tab badge --tab "$TAB_ID" --kind finished -q 2>/dev/null & ;;
    awaiting)   "$CLI" tab badge --tab "$TAB_ID" --kind awaiting-input -q 2>/dev/null & ;;
    *)          "$CLI" tab badge --tab "$TAB_ID" --clear -q 2>/dev/null & ;;
esac
