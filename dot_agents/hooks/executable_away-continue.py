#!/usr/bin/env python3
"""Stop hook that asks the agent whether to keep working while the user is away.

Usage: away-continue.py claude|codex|kiro

Every Stop is blocked once with REASON, so the agent decides from the
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

import json
import sys
from pathlib import Path

REASON = (
    "作業を終える前に、ユーザーが離席中かどうかを会話から確認してください。\n"
    "- 離席中と伝えられている場合: 次の作業が明確で、ユーザーの指示なしで判断できるなら、"
    "待たずに次の作業を実施する。些細な判断で止まっているなら、妥当な選択で進め、"
    "選んだ内容を報告に残して、ユーザーが戻った後に修正できるようにする。"
    "重要な判断や取り消しにくい操作が必要なら、ユーザーを待つ。\n"
    "- 離席中と伝えられていない場合: 待つことを一言だけ伝えて終了し、ユーザーを待つ。"
)
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


def count_tool_calls(agent, transcript):
    try:
        lines = Path(transcript).read_text().splitlines()
    except (OSError, TypeError):
        return 0
    count = 0
    for line in lines:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict) and is_tool_call(agent, entry):
            count += 1
    return count


def should_block(agent, data):
    if agent == "kiro":
        return True
    session = data.get("session_id")
    if not session or "/" in session:
        return False
    state = STATE_DIR / f"{agent}-{session}"
    count = count_tool_calls(agent, data.get("transcript_path"))
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
