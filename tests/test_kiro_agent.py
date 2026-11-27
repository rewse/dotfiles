"""Regression tests for the Kiro CLI v3 default agent and CLI settings."""

import json
import pathlib
import tempfile
import unittest

from chezmoi_template import execute_template

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
AGENT = REPO_ROOT / "private_dot_kiro/private_agents/private_main.json.tmpl"
CLI = REPO_ROOT / "private_dot_kiro/private_settings/private_cli.json.tmpl"


class KiroAgentTest(unittest.TestCase):
    def test_agent_is_not_named_default(self) -> None:
        # v3 never resolves a user agent named "default"; the built-in agent
        # of that name wins.
        self.assertIn('"name": "main"', AGENT.read_text())
        self.assertIn('"chat.defaultAgent": "main"', CLI.read_text())
        self.assertFalse(
            (REPO_ROOT / "private_dot_kiro/private_agents/default.json.tmpl").exists()
        )

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

    def test_default_agent_does_not_load_project_readme(self) -> None:
        # A cloned repository's README is third-party text; loading it as a
        # standing resource puts it in context without a read step.
        self.assertNotIn("file://README.md", AGENT.read_text())

    def test_default_agent_uses_read_workspace_preset(self) -> None:
        # read-workspace only adds silent workspace reads and leaves shell
        # commands to approve-for-me. read-only-shell would instead
        # auto-approve every read-only command before the classifier sees it.
        # The policies list must stay non-empty, or kiro-cli 3 fails with
        # "Mode not found".
        agent = AGENT.read_text()
        self.assertIn('"policies": ["read-workspace"]', agent)
        self.assertNotIn("read-only-shell", agent)


class KiroAgentInternalServersTest(unittest.TestCase):
    """The dotfiles-internal checkout supplies the agent's MCP servers."""

    def render(self, home: pathlib.Path) -> dict:
        result = execute_template(AGENT.read_text(), {"homeDir": str(home)})
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_agent_has_no_servers_without_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            self.assertEqual(self.render(pathlib.Path(home))["mcpServers"], {})

    def test_agent_takes_servers_from_the_checkout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            fragments = home / "git/dotfiles-internal/.chezmoitemplates/kiro"
            fragments.mkdir(parents=True)
            (fragments / "agent-mcp-servers.json").write_text(
                '{\n  "internal": {\n    "command": "{{ .chezmoi.homeDir }}/a"\n  }\n}\n'
            )
            self.assertEqual(
                self.render(home)["mcpServers"],
                {"internal": {"command": f"{home}/a"}},
            )


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
