#!/usr/bin/env python3
"""Stop hook that asks the agent whether to keep working while the user is away.

Usage: away-continue.py claude|codex|kiro

A turn shorter than MIN_SECONDS passes untouched, because the user is likely
still at the screen. The turn starts at the last prompt the user typed: the
last non-meta user entry for Claude Code (Stop hook feedback is a meta entry),
the last task_started event for Codex, and the last turn_start event in
~/.kiro/sessions/<cwd hash>/<session_id>/messages.jsonl for Kiro.

Every longer Stop is blocked once with REASON, so the agent decides from the
conversation whether the user said they are away. Claude Code and Codex fire
Stop again after a blocked turn continues. When that Stop arrives with
stop_hook_active set and no tool call has been made since the last block, the
agent chose to wait, so the hook lets it stop. If it made tool calls, it acted
on the reminder, so the hook blocks again and work can continue across steps.
Kiro does not fire Stop again for a continued turn, so every Kiro Stop is
blocked without state.

The tool call count at each block is kept in STATE_DIR per session. Losing the
state only costs one extra reminder.
"""

import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

REASON = (
    "作業を終える前に、ユーザーが離席中かどうかを会話から確認してください。\n"
    "- 離席中と伝えられている場合: 次の作業が明確で、ユーザーの指示なしで進められるなら、"
    "待たずに次の作業を実施する。些細な判断で止まっているなら、妥当な選択で進め、"
    "選んだ内容を報告に残して、ユーザーが戻った後に修正できるようにする。"
    "重要な判断や取り消しにくい操作が必要なら、ユーザーを待つ。\n"
    "- 離席中と伝えられていない場合: 待つことを一言だけ伝えて終了し、ユーザーを待つ。"
)
# Turns shorter than this many seconds are not checked
MIN_SECONDS = float(os.environ.get("AWAY_CONTINUE_MIN_SECONDS", "600"))
KIRO_SESSIONS_DIR = Path.home() / ".kiro" / "sessions"
STATE_DIR = Path("/tmp/away-continue")
CODEX_TOOL_CALLS = {
    "custom_tool_call",
    "function_call",
    "local_shell_call",
    "tool_search_call",
    "web_search_call",
}


def is_tool_call(agent, entry):
    if agent == "claude":
        if entry.get("type") != "assistant":
            return False
        content = (entry.get("message") or {}).get("content")
        return isinstance(content, list) and any(
            isinstance(item, dict) and item.get("type") == "tool_use"
            for item in content
        )
    payload = entry.get("payload") or {}
    return (
        entry.get("type") == "response_item" and payload.get("type") in CODEX_TOOL_CALLS
    )


def is_turn_start(agent, entry):
    if agent == "claude":
        if entry.get("type") != "user" or entry.get("isMeta"):
            return False
        content = (entry.get("message") or {}).get("content")
        if isinstance(content, str):
            return True
        return isinstance(content, list) and not any(
            isinstance(item, dict) and item.get("type") == "tool_result"
            for item in content
        )
    payload = entry.get("payload") or {}
    if agent == "codex":
        return (
            entry.get("type") == "event_msg" and payload.get("type") == "task_started"
        )
    return payload.get("type") == "turn_start"


def kiro_transcript(session, cwd):
    if cwd:
        digest = hashlib.sha256(cwd.encode()).hexdigest()[:16]
        log = KIRO_SESSIONS_DIR / digest / session / "messages.jsonl"
        if log.is_file():
            return log
    logs = KIRO_SESSIONS_DIR.glob(f"*/{session}/messages.jsonl")
    return max(logs, key=lambda path: path.stat().st_mtime, default=None)


def read_entries(transcript):
    try:
        lines = Path(transcript).read_text().splitlines()
    except (OSError, TypeError):
        return []
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def turn_seconds(agent, entries):
    """Return the seconds since the turn started, or 0 if it is unknown."""
    for entry in reversed(entries):
        if is_turn_start(agent, entry):
            try:
                started = datetime.fromisoformat(entry["timestamp"])
            except (AttributeError, KeyError, ValueError):
                return 0
            return time.time() - started.timestamp()
    return 0


def should_block(agent, data):
    session = data.get("session_id")
    if not session or "/" in session:
        return False
    if agent == "kiro":
        transcript = kiro_transcript(session, data.get("cwd"))
    else:
        transcript = data.get("transcript_path")
    entries = read_entries(transcript)
    if turn_seconds(agent, entries) < MIN_SECONDS:
        return False
    if agent == "kiro":
        return True
    state = STATE_DIR / f"{agent}-{session}"
    count = sum(is_tool_call(agent, entry) for entry in entries)
    if data.get("stop_hook_active"):
        try:
            if int(state.read_text()) == count:
                return False
        except (OSError, ValueError):
            pass
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    state.write_text(str(count))
    return True


def main():
    agent = sys.argv[1] if len(sys.argv) > 1 else ""
    if agent not in {"claude", "codex", "kiro"}:
        sys.exit(f"usage: {sys.argv[0]} claude|codex|kiro")
    data = json.load(sys.stdin)
    if should_block(agent, data):
        print(json.dumps({"decision": "block", "reason": REASON}, ensure_ascii=False))


if __name__ == "__main__":
    main()
