"""Regression tests for the Kiro CLI v3 permissions template."""

import pathlib
import re
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PERMISSIONS = REPO_ROOT / "dot_kiro/settings/private_permissions.yaml.tmpl"
HOST_GATE = '{{- if eq .chezmoi.hostname "7cf34ded5d65" }}'


class KiroPermissionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = PERMISSIONS.read_text()

    def rules(self) -> dict[str, list[str]]:
        rules: dict[str, list[str]] = {}
        for block in self.text.split("  - capability: ")[1:]:
            capability = block.split("\n", 1)[0].strip()
            rules[capability] = re.findall(r'^      - "(.*)"$', block, re.MULTILINE)
        return rules

    def test_shell_patterns_are_globs(self) -> None:
        for value in self.rules()["shell"]:
            with self.subTest(value=value):
                self.assertNotRegex(value, r"[\^$|()]|\.\*|\.\+")

    def test_shell_patterns_start_with_a_command(self) -> None:
        for value in self.rules()["shell"]:
            with self.subTest(value=value):
                self.assertRegex(value, r"^[a-z][\w-]*\*?( [\w./@:*-]+)*$")

    def test_shell_patterns_are_sorted(self) -> None:
        shell = self.rules()["shell"]
        self.assertEqual(shell, sorted(shell))

    def test_legacy_commands_are_kept(self) -> None:
        shell = self.rules()["shell"]
        for pattern in (
            "defaults read *",
            "docker compose logs *",
            "git -P diff *",
            "jq *",
            "journalctl* --no-pager*",
            "mcporter *",
            "nslookup *",
            "rg *",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, shell)

    def test_read_paths_include_cwd(self) -> None:
        self.assertEqual(
            self.rules()["fs_read"],
            [
                ".",
                "./**",
                "~/Desktop/**",
                "~/Downloads/**",
                "/private/tmp/**",
                "/tmp/**",
            ],
        )

    def test_write_paths_are_limited(self) -> None:
        self.assertEqual(
            self.rules()["fs_write"],
            ["./**", "~/Desktop/**", "~/Downloads/**", "/private/tmp/**", "/tmp/**"],
        )

    def test_tool_capabilities_are_allowed(self) -> None:
        # v2 trusted these tools through allowedTools; v3 asks unless allowed.
        for capability in ("skill", "subagent", "web_fetch", "web_search"):
            with self.subTest(capability=capability):
                self.assertIn(capability, self.rules())

    def test_rules_allow_only(self) -> None:
        self.assertNotIn("effect: ask", self.text)
        self.assertNotIn("effect: deny", self.text)

    def test_builder_mcp_rule_is_host_gated(self) -> None:
        gate = self.text.index(HOST_GATE)
        end = self.text.index("{{- end }}", gate)
        self.assertIn('"builder-mcp/*"', self.text[gate:end])
        self.assertNotIn("builder-mcp", self.text[:gate] + self.text[end:])


if __name__ == "__main__":
    unittest.main()
