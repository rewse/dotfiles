"""Tests for the away-continue Stop hook shared by Claude Code, Codex, and Kiro."""

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest
from datetime import UTC
from datetime import datetime
from datetime import timedelta

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "dot_agents/hooks/executable_away-continue.py"
CWD = "/tmp/project"


def stamp(minutes_ago: float) -> str:
    when = datetime.now(UTC) - timedelta(minutes=minutes_ago)
    return when.isoformat().replace("+00:00", "Z")


def turn_start(agent: str, minutes_ago: float) -> dict:
    timestamp = stamp(minutes_ago)
    if agent == "claude":
        return {"type": "user", "timestamp": timestamp, "message": {"content": "q"}}
    if agent == "codex":
        return {
            "type": "event_msg",
            "timestamp": timestamp,
            "payload": {"type": "task_started"},
        }
    return {"timestamp": timestamp, "payload": {"type": "turn_start"}}


def tool_call(agent: str) -> dict:
    if agent == "claude":
        return {
            "type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": "Bash"}]},
        }
    return {"type": "response_item", "payload": {"type": "function_call"}}


def stop_feedback() -> dict:
    return {
        "type": "user",
        "isMeta": True,
        "timestamp": stamp(0),
        "message": {"content": "Stop hook feedback:\n..."},
    }


class AwayContinueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.script = self.tmp / "away-continue.py"
        source = SCRIPT.read_text().replace(
            'Path("/tmp/away-continue")', f'Path("{self.tmp}/state")'
        )
        self.script.write_text(source)
        self.home = self.tmp / "home"
        digest = hashlib.sha256(CWD.encode()).hexdigest()[:16]
        kiro_dir = self.home / ".kiro/sessions" / digest / "sess"
        kiro_dir.mkdir(parents=True)
        self.kiro_transcript = kiro_dir / "messages.jsonl"
        self.transcript = self.tmp / "transcript.jsonl"

    def path(self, agent: str) -> pathlib.Path:
        return self.kiro_transcript if agent == "kiro" else self.transcript

    def add_entries(self, agent: str, *entries: dict) -> None:
        with self.path(agent).open("a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def start_turn(self, agent: str, minutes_ago: float) -> None:
        self.path(agent).write_text("")
        self.add_entries(agent, turn_start(agent, minutes_ago))

    def run_stop(self, agent: str, active: bool = False) -> dict | None:
        payload = {
            "session_id": "sess",
            "hook_event_name": "Stop",
            "cwd": CWD,
            "stop_hook_active": active,
            "transcript_path": str(self.transcript),
        }
        result = subprocess.run(
            ["python3", str(self.script), agent],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=dict(os.environ, HOME=str(self.home)),
            check=True,
        )
        return json.loads(result.stdout) if result.stdout else None

    def test_passes_short_turn(self) -> None:
        for agent in ("claude", "codex", "kiro"):
            with self.subTest(agent=agent):
                self.start_turn(agent, minutes_ago=3)
                self.assertIsNone(self.run_stop(agent))

    def test_blocks_long_turn(self) -> None:
        for agent in ("claude", "codex", "kiro"):
            with self.subTest(agent=agent):
                self.start_turn(agent, minutes_ago=15)
                out = self.run_stop(agent)
                assert out is not None
                self.assertEqual(out["decision"], "block")
                self.assertIn("離席中", out["reason"])

    def test_measures_from_last_turn_start(self) -> None:
        self.start_turn("codex", minutes_ago=30)
        self.add_entries("codex", turn_start("codex", minutes_ago=2))
        self.assertIsNone(self.run_stop("codex"))

    def test_stop_feedback_does_not_restart_claude_turn(self) -> None:
        self.start_turn("claude", minutes_ago=15)
        self.assertIsNotNone(self.run_stop("claude"))
        self.add_entries("claude", stop_feedback(), tool_call("claude"))
        self.assertIsNotNone(self.run_stop("claude", active=True))

    def test_lets_agent_stop_after_waiting(self) -> None:
        for agent in ("claude", "codex"):
            with self.subTest(agent=agent):
                self.start_turn(agent, minutes_ago=15)
                self.add_entries(agent, tool_call(agent))
                self.assertIsNotNone(self.run_stop(agent))
                self.assertIsNone(self.run_stop(agent, active=True))

    def test_blocks_again_after_continuing_work(self) -> None:
        for agent in ("claude", "codex"):
            with self.subTest(agent=agent):
                self.start_turn(agent, minutes_ago=15)
                self.assertIsNotNone(self.run_stop(agent))
                self.add_entries(agent, tool_call(agent))
                self.assertIsNotNone(self.run_stop(agent, active=True))
                self.assertIsNone(self.run_stop(agent, active=True))

    def test_kiro_blocks_every_long_stop(self) -> None:
        self.start_turn("kiro", minutes_ago=15)
        self.assertIsNotNone(self.run_stop("kiro"))
        self.assertIsNotNone(self.run_stop("kiro", active=True))

    def test_missing_transcript_passes(self) -> None:
        for agent in ("claude", "codex", "kiro"):
            with self.subTest(agent=agent):
                self.path(agent).unlink(missing_ok=True)
                self.assertIsNone(self.run_stop(agent))


if __name__ == "__main__":
    unittest.main()
