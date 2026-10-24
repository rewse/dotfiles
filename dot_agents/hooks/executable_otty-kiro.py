#!/usr/bin/env python3
"""Kiro CLI hook that reports turns and resume commands to Otty.

Usage: otty-kiro.py session-start|stop

Kiro runs hooks without a controlling terminal, so /dev/tty cannot be opened.
The kiro-cli zsh wrapper passes the pane's tty path in KIRO_OTTY_TTY and its
own arguments, shell-quoted, in KIRO_OTTY_ARGS; without them the hook does
nothing.

session-start arms OSC 88 (Terminal Resume Protocol) with
`kiro-cli chat <launch options> --resume-id <session>`, so a restored Otty
pane reopens the same conversation. The launch question is left out so the
resume does not ask it again, and --no-interactive runs are never armed.
Kiro fires SessionStart at a session's first prompt, not at launch. The
wrapper clears the declaration when Kiro exits.

stop posts an OSC 777 notification carrying the project name and the start of
the final answer. Kiro already reports `done` through OSC 7501, and Otty
builds its banner from Kiro's record, so a second `done` with a message
cannot replace that banner; Otty's command-finish notification is turned off
and this hook posts the only one. Answers that japanese-guard sends back for
a rewrite are not announced, because Kiro does not fire Stop again for the
rewritten turn.
"""

import base64
import contextlib
import importlib.util
import json
import os
import re
import shlex
import sys
from pathlib import Path

GUARD_KIRO_PATH = Path(__file__).with_name("japanese-guard-kiro.py")
RESUME_FLAGS = {"-r", "--resume", "--resume-picker"}
# Options of `kiro-cli chat` that take a separate value word. Every other bare
# word is the positional first question, which a resume must not ask again.
VALUE_OPTIONS = {
    "--agent",
    "--agent-engine",
    "--delete-session",
    "--effort",
    "--format",
    "--mode",
    "--model",
    "--output-format",
    "--repo",
    "--session-source",
    "--trust-tools",
    "--wrap",
    "-d",
    "-f",
    "-w",
}
STOCK_BODY = "Response complete"
CONTROL = re.compile(r"[\x00-\x1f\x7f-\x9f]")
LINE_MARKER = re.compile(r"^\s*(?:#{1,6}\s+|>\s?|[-*+]\s+|\d+\.\s+)")
LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


def resume_args(raw: str, session_id: str) -> str | None:
    words = shlex.split(raw)
    if "--no-interactive" in words:
        return None
    if words and words[0] == "chat":
        words = words[1:]
    kept = ["chat"]
    i = 0
    while i < len(words):
        word = words[i]
        if word == "--resume-id":
            i += 1
        elif word in VALUE_OPTIONS:
            kept.extend(words[i : i + 2])
            i += 1
        elif (
            word.startswith("-")
            and word not in RESUME_FLAGS
            and not word.startswith("--resume-id=")
        ):
            kept.append(word)
        i += 1
    return shlex.join([*kept, "--resume-id", session_id])


def _b64(value: str) -> str:
    return base64.b64encode(value.encode()).decode()


def arm_sequence(args: str, cwd: str) -> bytes:
    fields = f"cmd={_b64('kiro-cli')};args={_b64(args)};cwd={_b64(cwd)}"
    return f"\x1b]88;arm;{fields}\x07".encode()


def _clean(text: str) -> str:
    text = CONTROL.sub("", text).replace(";", ",")
    return re.sub(r"\s+", " ", text).strip()


def notification_body(answer: str, limit: int = 100) -> str:
    lines = []
    for line in answer.splitlines():
        if line.lstrip().startswith("```"):
            continue
        while LINE_MARKER.match(line):
            line = LINE_MARKER.sub("", line, count=1)
        lines.append(line)
    text = LINK.sub(r"\1", " ".join(lines))
    text = _clean(text.replace("**", "").replace("__", "").replace("`", ""))
    if len(text) > limit:
        text = text[: limit - 1] + "…"
    return text or STOCK_BODY


def notify_sequence(title: str, body: str) -> bytes:
    return f"\x1b]777;notify;{_clean(title)};{body}\x07".encode()


def write_tty(path: str, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_NOCTTY)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)


def load_guard_kiro():
    spec = importlib.util.spec_from_file_location(
        "japanese_guard_kiro", GUARD_KIRO_PATH
    )
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {GUARD_KIRO_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv: list[str]) -> None:
    tty = os.environ.get("KIRO_OTTY_TTY")
    if not tty or len(argv) < 2:
        return
    data = json.load(sys.stdin)
    session = data.get("session_id") or ""
    cwd = data.get("cwd") or ""
    if not session or "/" in session:
        return
    if argv[1] == "session-start":
        args = resume_args(os.environ.get("KIRO_OTTY_ARGS", ""), session)
        if args is not None:
            write_tty(tty, arm_sequence(args, cwd))
    elif argv[1] == "stop":
        guard_kiro = load_guard_kiro()
        answer = guard_kiro.final_answer(session, cwd)
        if guard_kiro.load_guard().is_english(answer):
            return
        title = f"Kiro — {os.path.basename(cwd.rstrip('/')) or cwd}"
        write_tty(tty, notify_sequence(title, notification_body(answer)))


if __name__ == "__main__":
    # Reporting to Otty must never disturb Kiro, whatever goes wrong.
    with contextlib.suppress(Exception):
        main(sys.argv)
