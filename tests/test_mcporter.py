"""Regression tests for the mcporter MCP server configuration and skill."""

import json
import pathlib
import re
import tempfile
import unittest

from chezmoi_template import execute_template

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MCPORTER = REPO_ROOT / "dot_config/mcporter/private_mcporter.json.tmpl"
SKILL = REPO_ROOT / "dot_agents/skills/mcporter/SKILL.md.tmpl"
INTERNAL_FRAGMENTS = pathlib.Path("git/dotfiles-internal/.chezmoitemplates/mcporter")
ONEPASSWORD_READ = re.compile(r'\{\{ onepasswordRead "[^"]*" \}\}')


class McporterConfigTest(unittest.TestCase):
    def test_python_servers_run_through_uvx(self) -> None:
        # uvx applies exclude-newer from uv.toml; pipx run takes the newest
        # PyPI release with no age gate.
        text = MCPORTER.read_text()
        self.assertNotIn('"pipx"', text)
        self.assertRegex(
            text,
            re.compile(
                r'"analytics-mcp": \{\s*"command": "uvx",\s*"args": \[\s*"analytics-mcp"\s*\]'
            ),
        )

    def test_editor_imports_are_disabled(self) -> None:
        # mcporter otherwise imports servers from editor configs in the working
        # directory (.cursor/mcp.json, .codex/config.toml, and others), so a
        # file written there could define a server an allowed call starts.
        self.assertRegex(MCPORTER.read_text(), re.compile(r'\A\{\s*"imports": \[\],'))


class InternalFragmentTest(unittest.TestCase):
    """The dotfiles-internal checkout extends the config and the skill."""

    def setUp(self) -> None:
        temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(temporary_directory.cleanup)
        self.home = pathlib.Path(temporary_directory.name)
        self.fragments = self.home / INTERNAL_FRAGMENTS

    def render(self, template: pathlib.Path) -> str:
        # Tests cannot reach 1Password, so secrets render as a placeholder.
        text = ONEPASSWORD_READ.sub("secret", template.read_text())
        result = execute_template(text, {"homeDir": str(self.home)})
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def write_fragments(self) -> None:
        self.fragments.mkdir(parents=True)
        (self.fragments / "servers.json").write_text(
            '{"internal-b": {"command": "b"},\n'
            ' "internal-a": {"command": "{{ .chezmoi.homeDir }}/bin/a",'
            ' "env": {"KEY": "value"}}}\n'
        )
        (self.fragments / "skill-description.txt").write_text(
            "Also use for internal systems.\n"
        )
        (self.fragments / "skill-servers.md").write_text("- `internal-a` — A\n")
        (self.fragments / "skill-tips.md").write_text("- Internal tip\n")

    def test_config_has_only_public_servers_without_the_checkout(self) -> None:
        servers = json.loads(self.render(MCPORTER))["mcpServers"]
        self.assertIn("zabbix", servers)
        self.assertFalse(any(name.startswith("internal-") for name in servers))

    def test_config_merges_internal_servers_as_valid_json(self) -> None:
        self.write_fragments()
        config = json.loads(self.render(MCPORTER))
        self.assertEqual(config["imports"], [])
        servers = config["mcpServers"]
        self.assertIn("zabbix", servers)
        self.assertEqual(servers["internal-b"], {"command": "b"})
        self.assertEqual(
            servers["internal-a"],
            {"command": f"{self.home}/bin/a", "env": {"KEY": "value"}},
        )

    def test_skill_has_only_public_text_without_the_checkout(self) -> None:
        skill = self.render(SKILL)
        self.assertRegex(
            skill, re.compile(r'^description: .*"mcporter" explicitly\.$', re.MULTILINE)
        )
        self.assertRegex(
            skill, re.compile(r"^- `zabbix` — .*\n\n## Usage", re.MULTILINE)
        )
        self.assertTrue(skill.endswith("unifi_list_clients\")'`\n"))

    def test_skill_appends_internal_text(self) -> None:
        self.write_fragments()
        skill = self.render(SKILL)
        self.assertRegex(
            skill,
            re.compile(
                r'^description: .*"mcporter" explicitly\. Also use for internal systems\.$',
                re.MULTILINE,
            ),
        )
        self.assertRegex(
            skill,
            re.compile(
                r"^- `zabbix` — .*\n- `internal-a` — A\n\n## Usage", re.MULTILINE
            ),
        )
        self.assertTrue(skill.endswith("unifi_list_clients\")'`\n- Internal tip\n"))


if __name__ == "__main__":
    unittest.main()
