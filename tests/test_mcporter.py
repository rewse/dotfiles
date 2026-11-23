"""Regression tests for the mcporter MCP server configuration."""

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MCPORTER = REPO_ROOT / "dot_config/mcporter/private_mcporter.json.tmpl"


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


if __name__ == "__main__":
    unittest.main()
