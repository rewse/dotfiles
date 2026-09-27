#!/usr/bin/env python3
"""Kiro CLI stop hook that asks for a Japanese rewrite of an English answer.

Reuses the detection logic and message of japanese-guard.py, the Claude Code
hook installed next to this file. Kiro passes the final answer (the text after
the last tool call) as assistant_response instead of a transcript path, and
honors the same {"decision": "block", "reason": ...} output.

Kiro sends no stop_hook_active flag, so a per-session marker file limits the
rewrite request to once per turn: the stop that follows a block always passes.
"""

import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path

GUARD_PATH = Path(__file__).with_name("japanese-guard.py")
MARKER_DIR = Path(tempfile.gettempdir()) / "japanese-guard-kiro"


def load_guard():
    spec = importlib.util.spec_from_file_location("japanese_guard", GUARD_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    data = json.load(sys.stdin)
    session = data.get("session_id") or os.environ.get("KIRO_SESSION_ID")
    if not session:
        return
    marker = MARKER_DIR / re.sub(r"[^\w-]", "_", session)
    if marker.exists():
        marker.unlink()
        return
    response = (data.get("assistant_response") or "").strip()
    guard = load_guard()
    if not guard.is_english(response):
        return
    MARKER_DIR.mkdir(mode=0o700, exist_ok=True)
    marker.touch()
    quoted = "- " + response.splitlines()[0][:80]
    print(json.dumps({"decision": "block", "reason": guard.REASON.format(quoted=quoted)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
