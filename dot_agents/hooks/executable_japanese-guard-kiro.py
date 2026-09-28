#!/usr/bin/env python3
"""Kiro CLI stop hook that asks for a Japanese rewrite of an English answer.

Reuses the detection logic and message of japanese-guard.py, the Claude Code
hook installed next to this file, and honors the same
{"decision": "block", "reason": ...} output.

Kiro passes only the session ID to Stop hooks, so the final answer (the text
after the last tool call) is read from the session log at
~/.kiro/sessions/<cwd hash>/<session_id>/messages.jsonl, which Kiro writes
before running the hook. Kiro does not fire Stop again for the turn a block
continues, so every Stop is checked.
"""

import importlib.util
import json
import sys
from pathlib import Path

GUARD_PATH = Path(__file__).with_name("japanese-guard.py")
SESSIONS_DIR = Path.home() / ".kiro" / "sessions"
TURN_BOUNDARIES = {"tool_call", "tool_result", "user"}


def load_guard():
    spec = importlib.util.spec_from_file_location("japanese_guard", GUARD_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {GUARD_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def final_answer(session):
    logs = sorted(SESSIONS_DIR.glob(f"*/{session}/messages.jsonl"))
    if not logs:
        return ""
    parts = []
    for line in logs[0].read_text().splitlines():
        try:
            payload = json.loads(line).get("payload") or {}
        except json.JSONDecodeError:
            continue
        kind = payload.get("type")
        if kind in TURN_BOUNDARIES:
            parts = []
        elif kind == "assistant" and payload.get("operationType") == "Say":
            parts.append(payload.get("content") or "")
    return "\n".join(parts).strip()


def main():
    data = json.load(sys.stdin)
    session = data.get("session_id")
    if not session or "/" in session:
        return
    response = final_answer(session)
    guard = load_guard()
    if not guard.is_english(response):
        return
    quoted = "- " + response.splitlines()[0][:80]
    print(
        json.dumps(
            {"decision": "block", "reason": guard.REASON.format(quoted=quoted)},
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
