"""Regression tests for the Kiro CLI v3 permissions template."""

import json
import pathlib
import tempfile
import unittest
from typing import Any

from chezmoi_template import execute_template

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PERMISSIONS = (
    REPO_ROOT / "private_dot_kiro/private_settings/private_permissions.yaml.tmpl"
)
INTERNAL_RULES = """\
- capability: mcp
  effect: allow
  match:
    - "internal-mcp/Read"
"""


def render(raw: str, home: pathlib.Path) -> dict[str, Any]:
    """Renders the template for home and parses the YAML it produces."""
    result = execute_template(raw, {"homeDir": str(home)})
    assert result.returncode == 0, result.stderr
    # chezmoi parses the YAML, so the tests need no YAML library.
    parsed = execute_template(
        "{{ .chezmoi.doc | fromYaml | toJson }}", {"doc": result.stdout}
    )
    assert parsed.returncode == 0, parsed.stderr
    return json.loads(parsed.stdout)


class KiroPermissionsTest(unittest.TestCase):
    raw: str
    rendered: dict[str, Any]
    extended: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = PERMISSIONS.read_text()
        with tempfile.TemporaryDirectory() as directory:
            home = pathlib.Path(directory)
            cls.rendered = render(cls.raw, home)
            fragments = home / "git/dotfiles-internal/.chezmoitemplates/kiro"
            fragments.mkdir(parents=True)
            (fragments / "permission-rules.yaml").write_text(INTERNAL_RULES)
            cls.extended = render(cls.raw, home)

    def setUp(self) -> None:
        self.rules: list[dict[str, Any]] = self.rendered["rules"]

    def rules_for(self, capability: str) -> list[dict[str, Any]]:
        return [rule for rule in self.rules if rule["capability"] == capability]

    def matches(self, capability: str) -> list[str]:
        return [
            value
            for rule in self.rules_for(capability)
            if rule["effect"] == "allow"
            for value in rule.get("match", [])
        ]

    def test_policies_enable_approve_for_me(self) -> None:
        self.assertEqual(self.rendered["policies"], ["approve-for-me"])

    def test_shell_has_no_rule(self) -> None:
        # approve-for-me judges every shell command.
        for rendered in (self.rendered, self.extended):
            caps = {r["capability"] for r in rendered["rules"]}
            self.assertNotIn("shell", caps)

    def test_web_capabilities_have_no_rule(self) -> None:
        caps = {r["capability"] for r in self.rules}
        self.assertFalse({"web_fetch", "web_search"} & caps)

    def test_remaining_capabilities(self) -> None:
        # Rendered for a personal host.
        self.assertEqual(
            sorted((r["capability"], r["effect"]) for r in self.rules),
            [
                ("fs_read", "allow"),
                ("fs_write", "allow"),
                ("skill", "allow"),
                ("subagent", "allow"),
            ],
        )

    def test_read_paths_include_cwd(self) -> None:
        self.assertEqual(
            self.matches("fs_read"),
            [
                ".",
                "./**",
                "/private/tmp/**",
                "/tmp/**",
                "~/Desktop/**",
                "~/Downloads/**",
            ],
        )

    def test_write_paths_are_limited(self) -> None:
        self.assertEqual(
            self.matches("fs_write"),
            ["./**", "/private/tmp/**", "/tmp/**", "~/Desktop/**", "~/Downloads/**"],
        )

    def test_rules_have_no_deny(self) -> None:
        for rendered in (self.rendered, self.extended):
            for rule in rendered["rules"]:
                with self.subTest(rule=rule["capability"]):
                    self.assertNotEqual(rule["effect"], "deny")

    def test_internal_rules_follow_the_public_rules(self) -> None:
        self.assertNotIn("builder-mcp", self.raw)
        self.assertEqual(
            self.extended["rules"][-1],
            {"capability": "mcp", "effect": "allow", "match": ["internal-mcp/Read"]},
        )
        self.assertEqual(self.extended["rules"][:-1], self.rules)
        self.assertEqual(self.extended["policies"], self.rendered["policies"])


if __name__ == "__main__":
    unittest.main()
