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

    def rules(self) -> list[dict[str, list[str]]]:
        rules = []
        for block in self.text.split("  - capability: ")[1:]:
            rule = {"capability": [block.split("\n", 1)[0].strip()]}
            for key in ("exclude", "match"):
                section = re.search(
                    rf"^    {key}:\n((?:      - .*\n)+)", block, re.MULTILINE
                )
                rule[key] = (
                    re.findall(r'^      - "(.*)"$', section[1], re.MULTILINE)
                    if section
                    else []
                )
            rules.append(rule)
        return rules

    def rules_for(self, capability: str) -> list[dict[str, list[str]]]:
        return [rule for rule in self.rules() if rule["capability"] == [capability]]

    def matches(self, capability: str) -> list[str]:
        return [value for rule in self.rules_for(capability) for value in rule["match"]]

    def test_shell_patterns_are_globs(self) -> None:
        for value in self.matches("shell"):
            with self.subTest(value=value):
                self.assertNotRegex(value, r"[\^$|()]|\.\*|\.\+")

    def test_shell_patterns_start_with_a_command(self) -> None:
        for value in self.matches("shell"):
            with self.subTest(value=value):
                self.assertRegex(value, r"^[a-z][\w-]*\*?( [\w./@:*-]+)*$")

    def test_shell_patterns_are_sorted(self) -> None:
        for rule in self.rules_for("shell"):
            self.assertEqual(rule["match"], sorted(rule["match"]))

    def test_legacy_commands_are_kept(self) -> None:
        shell = self.matches("shell")
        for pattern in (
            "defaults read *",
            "docker compose logs *",
            "git -P diff *",
            "jq *",
            "journalctl* --no-pager*",
            "mcporter list *",
            "nslookup *",
            "rg *",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, shell)

    def test_commands_that_run_or_write_arbitrary_things_are_not_allowed(self) -> None:
        shell = self.matches("shell")
        for pattern in (
            "chezmoi *",
            "env *",
            "mcporter *",
            "open *",
            "sed *",
            "tar *",
            "tee *",
            "xargs *",
        ):
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, shell)

    def test_read_only_forms_are_allowed(self) -> None:
        shell = self.matches("shell")
        for pattern in (
            "chezmoi --no-pager diff *",
            "chezmoi status *",
            "env",
            "mcporter list *",
            "tar -t*",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, shell)

    def test_sysctl_rule_excludes_assignments(self) -> None:
        (rule,) = [
            rule for rule in self.rules_for("shell") if "sysctl -n *" in rule["match"]
        ]
        self.assertEqual(rule["match"], ["sysctl -a *", "sysctl -n *"])
        self.assertEqual(rule["exclude"], ["*=*"])

    def test_general_shell_rule_has_no_exclude(self) -> None:
        # Kiro strips redirections before matching, so an exclude cannot catch them.
        self.assertEqual(self.rules_for("shell")[0]["exclude"], [])

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

    def test_tool_capabilities_are_allowed(self) -> None:
        # v2 trusted these tools through allowedTools; v3 asks unless allowed.
        for capability in ("skill", "subagent", "web_fetch", "web_search"):
            with self.subTest(capability=capability):
                self.assertTrue(self.rules_for(capability))

    def test_rules_allow_only(self) -> None:
        self.assertNotIn("effect: ask", self.text)
        self.assertNotIn("effect: deny", self.text)

    def test_builder_mcp_rule_is_host_gated(self) -> None:
        gate = self.text.index(HOST_GATE)
        end = self.text.index("{{- end }}", gate)
        # User scope applies to every agent, so only the read tool main uses.
        self.assertIn('"builder-mcp/ReadInternalWebsites"', self.text[gate:end])
        self.assertNotIn("builder-mcp/*", self.text)
        self.assertNotIn("builder-mcp", self.text[:gate] + self.text[end:])


if __name__ == "__main__":
    unittest.main()
