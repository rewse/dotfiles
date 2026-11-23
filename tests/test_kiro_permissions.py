"""Regression tests for the Kiro CLI v3 permissions template."""

import fnmatch
import importlib.util
import json
import pathlib
import unittest
from typing import Any

from chezmoi_template import execute_template

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PERMISSIONS = (
    REPO_ROOT / "private_dot_kiro/private_settings/private_permissions.yaml.tmpl"
)
REDIRECT_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_redirect-guard-kiro.py"
HOST_GATE = '{{- if eq .chezmoi.hostname "7cf34ded5d65" }}'


def secret_patterns() -> tuple[str, ...]:
    spec = importlib.util.spec_from_file_location("redirect_guard", REDIRECT_GUARD_KIRO)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(module.SECRET_PATTERNS)


def render(raw: str, hostname: str) -> dict[str, Any]:
    """Renders the template for hostname and parses the YAML it produces."""
    result = execute_template(raw, {"hostname": hostname})
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
    business: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = PERMISSIONS.read_text()
        cls.rendered = render(cls.raw, "other")
        cls.business = render(cls.raw, "7cf34ded5d65")

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

    def test_shell_has_only_the_secret_ask_rule(self) -> None:
        shell = [r for r in self.rules if r["capability"] == "shell"]
        self.assertEqual([r["effect"] for r in shell], ["ask"])
        self.assertEqual(tuple(shell[0]["match"]), secret_patterns())

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
                ("shell", "ask"),
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

    def test_secret_patterns_cover_new_credential_stores(self) -> None:
        patterns = secret_patterns()
        for pattern in (
            "*.claude.json*",
            "*.codex/auth.json*",
            "*.config/gcloud",
            "*.config/gcloud/*",
            "*.config/gh",
            "*.config/gh/*",
            "*.npmrc*",
            "*.pypirc*",
            "*.zsh_history*",
            "*zsh/history*",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, patterns)

    def test_secret_patterns_are_sorted(self) -> None:
        self.assertEqual(list(secret_patterns()), sorted(secret_patterns()))

    def test_secret_patterns_match_template_list(self) -> None:
        # The ask rule in the template must list exactly SECRET_PATTERNS so the
        # rule and the hook guard the same locations.
        for pattern in secret_patterns():
            with self.subTest(pattern=pattern):
                self.assertIn(f'      - "{pattern}"', self.raw)

    def test_rules_have_no_deny(self) -> None:
        for rendered in (self.rendered, self.business):
            for rule in rendered["rules"]:
                with self.subTest(rule=rule["capability"]):
                    self.assertNotEqual(rule["effect"], "deny")

    def test_secret_locations_have_a_standalone_ask_rule(self) -> None:
        # ask beats allow and evaluate, so a credential read prompts even when
        # a preset, the classifier, or a session "always allow" would approve.
        (ask,) = [rule for rule in self.rules_for("shell") if rule["effect"] == "ask"]
        self.assertEqual(ask["match"], list(secret_patterns()))
        self.assertNotIn("exclude", ask)
        for command in (
            "cat ~/.aws/credentials",
            "cat ~/.claude.json",
            "cat ~/.codex/auth.json",
            "cat ~/.config/gcloud/credentials.db",
            "cat ~/.config/gh/hosts.yml",
            "cat ~/.npmrc",
            "cat ~/.zsh_history",
            "tail ~/.local/state/zsh/history",
        ):
            with self.subTest(command=command):
                # A Kiro glob * spans spaces and slashes, as fnmatch's does.
                self.assertTrue(
                    any(fnmatch.fnmatchcase(command, p) for p in ask["match"])
                )

    def test_builder_mcp_rule_is_host_gated(self) -> None:
        gate = self.raw.index(HOST_GATE)
        end = self.raw.index("{{- end }}", gate)
        # User scope applies to every agent, so only the read tool main uses.
        self.assertIn('"builder-mcp/ReadInternalWebsites"', self.raw[gate:end])
        self.assertNotIn("builder-mcp/*", self.raw)
        self.assertNotIn("builder-mcp/", self.raw[:gate] + self.raw[end:])
        self.assertEqual(
            self.business["rules"][-1],
            {
                "capability": "mcp",
                "effect": "allow",
                "match": ["builder-mcp/ReadInternalWebsites"],
            },
        )
        self.assertEqual(self.business["rules"][:-1], self.rules)
        self.assertEqual(self.business["policies"], ["approve-for-me"])


if __name__ == "__main__":
    unittest.main()
