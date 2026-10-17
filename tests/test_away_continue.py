"""Tests for the away-continue Stop hook shared by Claude Code, Codex, and Kiro."""

import json
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "dot_agents/hooks/executable_away-continue.py"


def claude_tool_call() -> dict:
    return {
        "type": "assistant",
        "message": {"content": [{"type": "tool_use", "name": "Bash"}]},
    }


def codex_tool_call() -> dict:
    return {"type": "response_item", "payload": {"type": "function_call"}}


class AwayContinueTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.script = self.tmp / "away-continue.py"
        source = SCRIPT.read_text().replace(
            'Path("/tmp/away-continue")', f'Path("{self.tmp}/state")'
        )
        self.script.write_text(source)
        self.transcript = self.tmp / "transcript.jsonl"
        self.transcript.write_text("")

    def add_entries(self, *entries: dict) -> None:
        with self.transcript.open("a") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

    def run_stop(self, agent: str, active: bool = False) -> dict | None:
        payload = {
            "session_id": "sess",
            "hook_event_name": "Stop",
            "stop_hook_active": active,
            "transcript_path": str(self.transcript),
        }
        result = subprocess.run(
            ["python3", str(self.script), agent],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(result.stdout) if result.stdout else None

    def test_blocks_first_stop(self) -> None:
        for agent in ("claude", "codex", "kiro"):
            with self.subTest(agent=agent):
                out = self.run_stop(agent)
                assert out is not None
                self.assertEqual(out["decision"], "block")
                self.assertIn("離席中", out["reason"])

    def test_lets_agent_stop_after_waiting(self) -> None:
        for agent, tool_call in (
            ("claude", claude_tool_call),
            ("codex", codex_tool_call),
        ):
            with self.subTest(agent=agent):
                self.add_entries(tool_call())
                self.assertIsNotNone(self.run_stop(agent))
                self.assertIsNone(self.run_stop(agent, active=True))

    def test_blocks_again_after_continuing_work(self) -> None:
        for agent, tool_call in (
            ("claude", claude_tool_call),
            ("codex", codex_tool_call),
        ):
            with self.subTest(agent=agent):
                self.assertIsNotNone(self.run_stop(agent))
                self.add_entries(tool_call())
                self.assertIsNotNone(self.run_stop(agent, active=True))
                self.assertIsNone(self.run_stop(agent, active=True))

    def test_kiro_blocks_every_stop(self) -> None:
        self.assertIsNotNone(self.run_stop("kiro"))
        self.assertIsNotNone(self.run_stop("kiro", active=True))


if __name__ == "__main__":
    unittest.main()
