#!/bin/bash
#
# Shared logic of the user-level superpowers gates (Claude Code, Codex,
# Kiro CLI). The per-CLI entry points in this directory source this file and
# translate their CLI's hook protocol to and from these functions.
#
# The gates make an agent read the superpowers skill that governs a plan, a
# spec or an SDD ledger before it writes one. A repository that carries its
# own .agents/hooks/superpowers-gates/core.sh is left to those hooks, but only
# in a session started in such a repository, because a CLI loads project hooks
# from its own project alone.
#
# Hooks run with a minimal PATH, so this file calls external programs by
# absolute path and otherwise uses bash builtins.

SG_JSON_TOOL=/usr/bin/plutil
SG_WINDOW_SECONDS=3600
SG_SMALL_EDIT_LINES=20
SG_SESSION_MAX_AGE_DAYS=30
SG_PROJECT_MARKER=.agents/hooks/superpowers-gates/core.sh

# sg_disabled: succeeds when SUPERPOWERS_GATES=off.
sg_disabled() {
    [ "${SUPERPOWERS_GATES:-}" = "off" ]
}

# sg_json_get <json> <keypath>: prints the value; fails when it is absent
# or the JSON is malformed.
sg_json_get() {
    printf '%s' "$1" | "$SG_JSON_TOOL" -extract "$2" raw -o - - 2>/dev/null
}

# sg_json_escape <text>: the text in a form that fits inside a JSON string.
sg_json_escape() {
    local s=$1
    s=${s//\\/\\\\}
    s=${s//\"/\\\"}
    s=${s//$'\n'/\\n}
    s=${s//$'\r'/\\r}
    s=${s//$'\t'/\\t}
    printf '%s' "$s"
}

# sg_count_lines <text>: the number of lines; 0 for empty text.
sg_count_lines() {
    local s=$1 stripped
    [ -n "$s" ] || { printf '0'; return 0; }
    stripped=${s//$'\n'/}
    printf '%s' $((${#s} - ${#stripped} + 1))
}

# sg_repo_root <path-or-dir>: the root of the worktree that contains the
# path, found by walking up to a directory with a .git file or directory.
sg_repo_root() {
    local dir=$1
    [ -n "$dir" ] || return 1
    while [ -n "$dir" ] && [ "$dir" != "/" ]; do
        if [ -e "$dir/.git" ]; then
            printf '%s' "$dir"
            return 0
        fi
        dir=${dir%/*}
    done
    return 1
}

# sg_defers <target-root> <cwd>: succeeds when both the repository being
# written to and the repository of the session's working directory carry
# their own agent hooks; these gates then do nothing. A session started
# elsewhere does not run the target's project hooks, so it stays gated.
sg_defers() {
    local session_root
    [ -f "$1/$SG_PROJECT_MARKER" ] || return 1
    session_root=$(sg_repo_root "$2") || return 1
    [ -f "$session_root/$SG_PROJECT_MARKER" ]
}

# sg_state_dir <cli> <session-id>: creates and prints the directory that
# holds the marks of one session. It lives outside every repository so a
# skill read in one repository counts for a write in another. Session
# directories untouched for more than 30 days are removed.
sg_state_dir() {
    [ -n "${HOME:-}" ] || return 1
    local session=${2:-nosession}
    local parent="$HOME/.local/state/superpowers-gates/$1"
    session=${session//\//%}
    local dir="$parent/$session"
    /bin/mkdir -p "$dir" || return 1
    # Touch first so the current session counts as recent, and exclude it by
    # name as well so it survives even when the touch fails.
    /usr/bin/touch "$dir" 2>/dev/null
    /usr/bin/find "$parent" -mindepth 1 -maxdepth 1 -type d ! -name "$session" \
        -mtime "+$SG_SESSION_MAX_AGE_DAYS" -exec /bin/rm -rf {} + 2>/dev/null
    printf '%s' "$dir"
}

# sg_skill_doc <repo-root> <skill>: the SKILL.md to point the agent at, as a
# path relative to the repository when it carries a copy, else under ~/.
sg_skill_doc() {
    if [ -f "$1/.agents/skills/$2/SKILL.md" ]; then
        printf '.agents/skills/%s/SKILL.md' "$2"
    else
        # shellcheck disable=SC2088  # the literal ~/ is shown to the agent
        printf '~/.agents/skills/%s/SKILL.md' "$2"
    fi
}

# sg_note_skill_read <state-dir> <text>: marks each gated skill that the
# text shows being read, as a path to its SKILL.md or as its name.
sg_note_skill_read() {
    local name
    for name in writing-plans brainstorming subagent-driven-development; do
        case "$2" in
            *"$name/SKILL.md"* | "$name" | "superpowers:$name") : > "$1/read-$name" ;;
        esac
    done
    return 0
}

# sg_skill_for_path <relpath>: the skill a file must be written under.
sg_skill_for_path() {
    case "$1" in
        docs/superpowers/plans/*.md) printf 'writing-plans' ;;
        docs/superpowers/specs/*.md) printf 'brainstorming' ;;
        .superpowers/sdd/*/progress.md) printf 'subagent-driven-development' ;;
    esac
    return 0
}

# sg_window_file <state-dir> <repo-root> <relpath>
sg_window_file() {
    local key="$2/$3"
    key=${key//\//%}
    printf '%s/window-%s' "$1" "$key"
}

sg_now() {
    /bin/date +%s
}

# sg_check_write <state-dir> <repo-root> <relpath> <kind> <changed-lines>:
# kind is create, rewrite or edit. Returns 0 to allow; returns 2 with a
# message on stdout to block.
sg_check_write() {
    local state=$1 root=$2 relpath=$3 kind=$4 lines=${5:-0}
    local skill window now started
    skill=$(sg_skill_for_path "$relpath")
    [ -n "$skill" ] || return 0
    # A ledger is appended to all session long; only its creation is gated.
    if [ "$skill" = "subagent-driven-development" ] && [ "$kind" != "create" ]; then
        return 0
    fi
    window=$(sg_window_file "$state" "$root" "$relpath")
    if [ "$kind" = "edit" ]; then
        [ "$lines" -le "$SG_SMALL_EDIT_LINES" ] && return 0
        if [ -f "$window" ]; then
            read -r started < "$window" || [ -n "$started" ]
            now=$(sg_now)
            [ $((now - started)) -le "$SG_WINDOW_SECONDS" ] && return 0
        fi
    fi
    if [ -f "$state/read-$skill" ]; then
        /bin/rm -f "$state/read-$skill"
        sg_now > "$window"
        return 0
    fi
    printf 'Read %s before writing %s; this file follows that skill. Then retry.' "$(sg_skill_doc "$root" "$skill")" "$relpath"
    return 2
}

# sg_reminder <repo-root> <relpath> <kind> <changed-lines>: prints a
# reminder for a write of a size that sg_check_write gates.
sg_reminder() {
    local root=$1 relpath=$2 kind=$3 lines=${4:-0} skill
    skill=$(sg_skill_for_path "$relpath")
    [ -n "$skill" ] || return 0
    if [ "$kind" = "edit" ] && [ "$lines" -le "$SG_SMALL_EDIT_LINES" ]; then
        return 0
    fi
    case "$skill" in
        writing-plans)
            printf 'Check %s against the Self-Review checklist in %s (spec coverage, step scan, type consistency, Review Focus, proportion) and fix what it finds.' "$relpath" "$(sg_skill_doc "$root" "$skill")" ;;
        brainstorming)
            printf 'Before handing %s over, run the builder check in %s (builder-check-prompt.md).' "$relpath" "$(sg_skill_doc "$root" "$skill")" ;;
    esac
    return 0
}

# sg_note_ledger <state-dir> <repo-root> <relpath>: records the absolute path
# of an SDD ledger that this session wrote, so a compaction reminder names
# only the ledgers of this session.
sg_note_ledger() {
    local abs="$2/$3" line
    [ "$(sg_skill_for_path "$3")" = "subagent-driven-development" ] || return 0
    if [ -f "$1/ledgers" ]; then
        while IFS= read -r line || [ -n "$line" ]; do
            [ "$line" != "$abs" ] || return 0
        done < "$1/ledgers"
    fi
    printf '%s\n' "$abs" >> "$1/ledgers"
    return 0
}

# sg_ledger_plan <repo-root> <ledger>: prints the plan path from the ledger
# header and succeeds when the ledger has fewer "Task <N>: complete" lines
# than its plan has "### Task" headings. Fails for a finished or malformed
# ledger and when the plan file is missing.
sg_ledger_plan() {
    local root=$1 ledger=$2 header plan planfile line total=0 done_count=0
    [ -f "$ledger" ] || return 1
    read -r header < "$ledger" || [ -n "$header" ] || return 1
    case "$header" in "# SDD ledger "*"plan: "*) ;; *) return 1 ;; esac
    plan=${header#*plan: }
    planfile=$plan
    case "$plan" in /*) ;; *) planfile="$root/$plan" ;; esac
    [ -f "$planfile" ] || return 1
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in "### Task "[0-9]*) total=$((total + 1)) ;; esac
    done < "$planfile"
    while IFS= read -r line || [ -n "$line" ]; do
        case "$line" in *"Task "[0-9]*": complete"*) done_count=$((done_count + 1)) ;; esac
    done < "$ledger"
    [ "$done_count" -lt "$total" ] || return 1
    printf '%s' "$plan"
}

# sg_compact_context <state-dir>: a reminder per unfinished SDD ledger that
# this session wrote, pointing the agent back to the skill and the ledger;
# nothing when the session wrote none or every one is finished.
sg_compact_context() {
    local ledger root plan first=1
    [ -f "$1/ledgers" ] || return 0
    while IFS= read -r ledger || [ -n "$ledger" ]; do
        root=$(sg_repo_root "${ledger%/*}") || continue
        plan=$(sg_ledger_plan "$root" "$ledger") || continue
        [ "$first" -eq 1 ] || printf '\n'
        first=0
        printf 'An unfinished subagent-driven-development ledger exists at %s. If this session is executing the plan in %s, re-read %s and that ledger before continuing.' \
            "${ledger#"$root"/}" "$plan" "$(sg_skill_doc "$root" subagent-driven-development)"
    done < "$1/ledgers"
    return 0
}
