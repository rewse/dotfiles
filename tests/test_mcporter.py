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


if __name__ == "__main__":
    unittest.main()
