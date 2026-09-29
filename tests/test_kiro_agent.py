"""Regression tests for the Kiro CLI v3 default agent and CLI settings."""

import pathlib
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENT = REPO_ROOT / "dot_kiro/agents/main.json.tmpl"
CLI = REPO_ROOT / "dot_kiro/settings/private_cli.json.tmpl"


class KiroAgentTest(unittest.TestCase):
    def test_agent_is_not_named_default(self) -> None:
        # v3 never resolves a user agent named "default"; the built-in agent
        # of that name wins.
        self.assertIn('"name": "main"', AGENT.read_text())
        self.assertIn('"chat.defaultAgent": "main"', CLI.read_text())
        self.assertFalse((REPO_ROOT / "dot_kiro/agents/default.json.tmpl").exists())

    def test_retired_default_agent_is_removed(self) -> None:
        removed = (REPO_ROOT / ".chezmoiremove").read_text().splitlines()
        self.assertIn(".kiro/agents/default.json", removed)
        self.assertIn(".kiro/agents/default.json.bak", removed)

    def test_default_agent_has_no_v2_fields(self) -> None:
        agent = AGENT.read_text()
        for key in (
            '"allowedTools"',
            '"hooks"',
            '"toolsSettings"',
            '"useLegacyMcpJson"',
        ):
            with self.subTest(key=key):
                self.assertNotIn(key, agent)

    def test_default_agent_includes_mcp_json(self) -> None:
        self.assertIn('"includeMcpJson": true', AGENT.read_text())

    def test_default_agent_stays_v3_when_tools_inject_allowed_tools(self) -> None:
        # Kiro treats an agent with allowedTools but no permissions as a v2
        # agent and swaps in the built-in default.
        self.assertIn('"permissions": {', AGENT.read_text())

    def test_default_agent_auto_allows_read_only_shell(self) -> None:
        self.assertIn('"policies": ["read-only-shell"]', AGENT.read_text())


class KiroCliSettingsTest(unittest.TestCase):
    def test_cli_selects_v3_engine(self) -> None:
        self.assertIn('"chat.agentEngine": "v3"', CLI.read_text())

    def test_cli_keeps_auto_agent_upgrade(self) -> None:
        # Kiro adds this key on the first v3 launch; keeping it avoids drift.
        self.assertIn('"chat.enableAutoAgentUpgrade": true', CLI.read_text())

    def test_cli_drops_settings_v3_ignores(self) -> None:
        self.assertNotIn("chat.enableCheckpoint", CLI.read_text())


if __name__ == "__main__":
    unittest.main()
