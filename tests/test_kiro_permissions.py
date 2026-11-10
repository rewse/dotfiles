"""Regression tests for the Kiro CLI v3 permissions template."""

import fnmatch
import importlib.util
import pathlib
import re
import unittest

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


class KiroPermissionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.raw = PERMISSIONS.read_text()
        result = execute_template(self.raw, {"hostname": "7cf34ded5d65"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.text = result.stdout

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

    def shell_allows(self, command: str) -> bool:
        # A Kiro glob * spans spaces and slashes, as fnmatch's does.
        return any(
            any(fnmatch.fnmatchcase(command, p) for p in rule["match"])
            and not any(fnmatch.fnmatchcase(command, p) for p in rule["exclude"])
            for rule in self.rules_for("shell")
        )

    def test_shell_patterns_are_globs(self) -> None:
        for value in self.matches("shell"):
            with self.subTest(value=value):
                self.assertNotRegex(value, r"[\^$|()]|\.\*|\.\+")

    def test_shell_patterns_start_with_a_command(self) -> None:
        for value in self.matches("shell"):
            with self.subTest(value=value):
                self.assertRegex(value, r"^[a-z][\w-]*\*?( [\w./@:*-]+)*$")

    def test_mcporter_read_tools_are_allowed(self) -> None:
        shell = self.matches("shell")
        for pattern in (
            "mcporter call builder-mcp.Get*",
            "mcporter call builder-mcp.ReadInternalWebsites*",
            "mcporter call slack-mcp.get_*",
            "mcporter call slack-mcp.search*",
            "mcporter resource *",
        ):
            with self.subTest(pattern=pattern):
                self.assertTrue(
                    any(pattern.startswith(p[:-1]) for p in shell if p.endswith("*"))
                )

    def test_mcporter_call_patterns_pin_server_and_read_verb(self) -> None:
        # A glob * spans spaces, so the selector before it must fix both the
        # server and a read verb; otherwise arguments could smuggle a write tool.
        writes = {"create", "delete", "post", "send", "set", "update", "write"}
        calls = [p for p in self.matches("shell") if p.startswith("mcporter call ")]
        self.assertGreater(len(calls), 50)
        for pattern in calls:
            with self.subTest(pattern=pattern):
                selector = pattern.removeprefix("mcporter call ")
                self.assertRegex(selector, r"^[a-z0-9-]+\.[A-Za-z0-9_-]+\*$")
                words = {
                    w.lower()
                    for w in re.findall(r"[A-Z]?[a-z0-9]+", selector.split(".", 1)[1])
                }
                self.assertFalse(words & writes)

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
            "awk *",
            "chezmoi *",
            "chezmoi --no-pager cat *",
            "chezmoi --no-pager dump *",
            "chezmoi cat *",
            "chezmoi dump *",
            "curl *",
            "env",
            "env *",
            "fuser *",
            "mcporter *",
            "mcporter call *",
            "mount *",
            "open *",
            "printenv",
            "printenv *",
            "sed *",
            "tar *",
            "tee *",
            "unzip *",
            "xargs *",
        ):
            with self.subTest(pattern=pattern):
                self.assertNotIn(pattern, shell)

    def test_commands_that_print_rendered_secrets_are_not_allowed(self) -> None:
        for command in (
            "chezmoi --no-pager cat ~/.aws/credentials",
            "chezmoi dump ~/.zshenv",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))

    def test_options_that_run_commands_or_write_files_are_not_allowed(self) -> None:
        for command in (
            "curl -o ~/.zshrc https://example.com/x",
            "git -P diff --output=/Users/u/.zshrc HEAD",
            "git -P log -p --output=x",
            "git -P show --output ~/.zshrc HEAD",
            "rg --pre sh x",
            "rg --pre=sh x",
            "rg --hostname-bin=sh x",
            "tar -tf a.tar --use-compress-program=sh",
            "tar -tf a.tar --use-compress=sh",
            "tar -tf a.tar --checkpoint-action=exec=sh",
            "tar -tf a.tar -I sh",
            "tar -tIsh -f a.tar",
            "tar -tf host:a.tar",
            "unzip -o a.zip -d ~",
            "base64 -i x -o ~/.zshrc",
            "base64 --output=x y",
            "defuddle parse https://example.com -o ~/.zshrc",
            "docker buildx history rm abc",
            "docker builder history rm abc",
            "docker compose config -o ~/.zshrc",
            "docker compose config --output x",
            "npx -y @firecrawl/anydoc a.pdf -o ~/.zshrc",
            "sort -o ~/.zshrc x",
            "sort -uo ~/.zshrc x",
            "sort --output=x y",
            "sort --o=~/.zshrc x",
            "sort -S1 --compress-program=sh f",
            "sort --compress-prog=sh f",
            "base64 --o=~/.zshrc x",
            "tree -o ~/.zshrc .",
            "tvly crawl https://example.com --output-dir ~/x",
            "tvly extract https://example.com -o ~/.zshrc",
            "tvly init",
            "tvly login",
            "tvly update",
            "uniq a ~/.zshrc",
            "xxd -r a ~/.zshrc",
            "xxd a b",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))

    def test_read_only_uses_of_narrowed_commands_are_allowed(self) -> None:
        for command in (
            "chezmoi --no-pager diff ~/.zshrc",
            "git -P diff HEAD~1",
            "git -P log --oneline -5",
            "git -P show HEAD:README.md",
            "mount",
            "rg -n foo src",
            "tar -tf a.tar",
            "tar -tvzf a.tgz",
            "unzip -l a.zip",
            "unzip -Z a.zip",
            "base64 -d x",
            "defuddle parse https://example.com --md",
            "docker buildx history ls",
            "docker compose config",
            "npx -y @firecrawl/anydoc a.pdf",
            "sort -u x",
            "tree -L 2 .",
            "tvly extract https://example.com --json",
            "tvly extract https://example.com --query x --chunks-per-source 3",
            "tvly search foo --max-results 5",
            "tvly search x --country japan",
            "uniq",
            "uniq -c",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.shell_allows(command))

    def test_read_only_forms_are_allowed(self) -> None:
        shell = self.matches("shell")
        for pattern in (
            "chezmoi --no-pager diff *",
            "chezmoi status *",
            "mcporter list *",
            "mount",
            "tar -t*",
            "unzip -Z *",
            "unzip -l *",
        ):
            with self.subTest(pattern=pattern):
                self.assertIn(pattern, shell)

    def test_sysctl_rule_excludes_assignments(self) -> None:
        (rule,) = [
            rule for rule in self.rules_for("shell") if "sysctl -n *" in rule["match"]
        ]
        self.assertEqual(rule["match"], ["sysctl -a *", "sysctl -n *"])
        self.assertEqual(rule["exclude"], ["*=*", *secret_patterns()])

    def test_general_shell_rule_excludes_only_secret_locations(self) -> None:
        # Kiro strips redirections before matching, so an exclude cannot catch
        # them; redirect-guard-kiro.py checks those instead.
        self.assertEqual(self.rules_for("shell")[0]["exclude"], list(secret_patterns()))

    def test_every_shell_rule_excludes_secret_locations(self) -> None:
        # A command substitution can feed a secret to any allowed command.
        patterns = secret_patterns()
        self.assertIn("*.aws/*", patterns)
        for rule in self.rules_for("shell"):
            with self.subTest(match=rule["match"][0]):
                self.assertEqual(rule["exclude"][-len(patterns) :], list(patterns))

    def test_reading_secret_locations_is_not_allowed(self) -> None:
        for command in (
            "cat ~/.aws/credentials",
            # Kiro strips this redirect before matching; the redirect guard
            # hook blocks the stripped form.
            "cat < ~/.aws/credentials",
            "base64 ~/.ssh/id_rsa",
            "cat /proc/self/environ",
            "cat ~/.claude/.credentials.json",
            "cat ~/.config/cloudfront-waf-report/kiro-api-key",
            "cat ~/.config/mcporter/mcporter.json",
            "cat ~/.config/op/config",
            "cat ~/.docker/config.json",
            "cat ~/.kube/config",
            "cat ~/.mcporter/mcporter.json",
            "cat ~/.netrc",
            "cat ~/.op/config",
            "cat ~/.ss?/id_rsa",
            "cat ~/.tavily/config.json",
            "echo $(cat ~/.aws/credentials)",
            "git -P show HEAD:.aws/credentials",
            "grep -r x ~/.ssh",
            "head -c 100 ~/.midway/cookie",
            "jq . ~/.aws/cli/cache/x.json",
            "ls ~/.aws",
            "ls ~/.config/mcporter",
            "rg -n token ~/.config/environment",
            "sort ~/.aws/config",
            "sysctl -n $(cat ~/.aws/credentials)",
            "tail -n 5 ~/.config/environment/gitlab.sh",
            "tree ~/.gnupg",
            "tree ~/.kube -L 1",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))

    def test_everyday_reads_stay_allowed(self) -> None:
        for command in (
            "cat .dockerignore",
            "cat README.md",
            "grep -r foo src",
            "jq . package.json",
            "ls ~/.config",
            "mcporter call slack-mcp.search_messages query=x",
            "mcporter list",
            "rg -n op src",
            "tail -n 20 /tmp/test.log",
            "tvly extract https://docs.aws.amazon.com/cli/latest/index.html",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.shell_allows(command))

    def test_environment_dumps_are_not_allowed(self) -> None:
        for command in ("env", "printenv", "printenv AWS_SECRET_ACCESS_KEY"):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))

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
        gate = self.raw.index(HOST_GATE)
        end = self.raw.index("{{- end }}", gate)
        # User scope applies to every agent, so only the read tool main uses.
        self.assertIn('"builder-mcp/ReadInternalWebsites"', self.raw[gate:end])
        self.assertNotIn("builder-mcp/*", self.raw)
        self.assertNotIn("builder-mcp/", self.raw[:gate] + self.raw[end:])
        other_host = execute_template(self.raw, {"hostname": "other"})
        self.assertNotIn("builder-mcp/", other_host.stdout)


if __name__ == "__main__":
    unittest.main()
