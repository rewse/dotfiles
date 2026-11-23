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
SKILLS = REPO_ROOT / "dot_agents/skills"


def operation_tools() -> set[str]:
    """Returns the MCP tools that skills call with an operation= argument."""
    return {
        tool
        for path in SKILLS.rglob("*.md*")
        for tool in re.findall(
            r"mcporter call ([a-z0-9-]+\.[A-Za-z0-9_-]+) operation=", path.read_text()
        )
    }


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
            effect = re.search(r"^    effect: (\w+)$", block, re.MULTILINE)
            rule["effect"] = [effect[1]] if effect else []
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

    def allow_rules_for(self, capability: str) -> list[dict[str, list[str]]]:
        return [
            rule for rule in self.rules_for(capability) if rule["effect"] == ["allow"]
        ]

    def matches(self, capability: str) -> list[str]:
        return [
            value
            for rule in self.allow_rules_for(capability)
            for value in rule["match"]
        ]

    def rule_matches(self, rule: dict[str, list[str]], command: str) -> bool:
        # A Kiro glob * spans spaces and slashes, as fnmatch's does.
        return any(fnmatch.fnmatchcase(command, p) for p in rule["match"]) and not any(
            fnmatch.fnmatchcase(command, p) for p in rule["exclude"]
        )

    def shell_allows(self, command: str) -> bool:
        # deny > ask > allow: a command is auto-approved only when an allow
        # rule matches it and no ask or deny shell rule does.
        shell = self.rules_for("shell")
        if any(
            self.rule_matches(rule, command)
            for rule in shell
            if rule["effect"] in (["ask"], ["deny"])
        ):
            return False
        return any(
            self.rule_matches(rule, command)
            for rule in shell
            if rule["effect"] == ["allow"]
        )

    def test_shell_patterns_are_globs(self) -> None:
        for value in self.matches("shell"):
            with self.subTest(value=value):
                self.assertNotRegex(value, r"[\^$|()]|\.\*|\.\+")

    def test_shell_patterns_start_with_a_command(self) -> None:
        for value in self.matches("shell"):
            with self.subTest(value=value):
                self.assertRegex(value, r"^[a-z][\w-]*\*?( [\w./@:=*-]+)*$")

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
        # A tool that dispatches on operation= is allowed only with a read
        # operation and no *, which would admit a second operation=.
        writes = {"create", "delete", "post", "send", "set", "update", "write"}
        reads = {"get", "list", "read", "search", "view"}
        dispatched = operation_tools()
        self.assertIn("aws-outlook-mcp.todo_lists", dispatched)
        calls = [p for p in self.matches("shell") if p.startswith("mcporter call ")]
        self.assertGreater(len(calls), 50)
        for pattern in calls:
            with self.subTest(pattern=pattern):
                selector = pattern.removeprefix("mcporter call ")
                tool, _, operation = selector.partition(" operation=")
                stem = tool.removesuffix("*")
                if operation or any(
                    d == stem or (tool != stem and d.startswith(stem))
                    for d in dispatched
                ):
                    self.assertIn(tool, dispatched)
                    self.assertIn(operation, reads)
                    continue
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
            "agent-browser *",
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
            "chezmoi --no-pager data -o ~/.zshrc",
            "chezmoi --no-pager diff -o/etc/hosts",
            "chezmoi data --output=/Users/u/.zshrc",
            "chezmoi status -o ~/.zshrc",
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
            "chezmoi --no-pager managed --include files",
            "chezmoi status ~/.zshrc",
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

    def test_anydoc_options_that_send_documents_off_the_host_are_not_allowed(
        self,
    ) -> None:
        # --ocr hosted uploads the document to Firecrawl Parse, and --api-key
        # and --api-url pick the account and endpoint it goes to.
        for command in (
            "npx -y @firecrawl/anydoc scan.pdf --ocr hosted",
            "npx -y @firecrawl/anydoc scan.pdf --ocr=hosted",
            "npx @firecrawl/anydoc --ocr hosted scan.pdf",
            "npx -y @firecrawl/anydoc scan.pdf --api-key x",
            "npx -y @firecrawl/anydoc scan.pdf --api-url=https://example.com",
            "FIRECRAWL_API_URL=https://example.com npx -y @firecrawl/anydoc a.pdf",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))
        for command in (
            "npx -y @firecrawl/anydoc - --format csv",
            "npx -y @firecrawl/anydoc a.docx -f docx",
            "npx @firecrawl/anydoc slides.pptx",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.shell_allows(command))

    def test_chezmoi_options_that_change_source_or_config_are_not_allowed(
        self,
    ) -> None:
        # diff, status, and verify render source templates, which can run
        # commands, so an option that picks another source, config, or data
        # set, or that runs a pager or rewrites the config, prompts.
        for command in (
            "chezmoi --no-pager diff --cache /tmp/c",
            "chezmoi --no-pager diff --pager 'sh -c id'",
            "chezmoi --no-pager diff --source /tmp/s",
            "chezmoi --no-pager diff -S /tmp/s",
            "chezmoi data --override-data '{}'",
            "chezmoi data --override-data-file /tmp/d.json",
            "chezmoi diff --pager=less",
            "chezmoi diff --persistent-state /tmp/p.boltdb",
            "chezmoi diff --source=/tmp/s",
            "chezmoi diff --working-tree /tmp/w",
            "chezmoi diff -S/tmp/s",
            "chezmoi diff -S=/tmp/s",
            "chezmoi diff -W /tmp/w",
            "chezmoi diff ~/.zshrc -S /tmp/s",
            "chezmoi managed --destination /tmp/d",
            "chezmoi status --config /tmp/c.yaml",
            "chezmoi status --config-format yaml",
            "chezmoi status --config=/tmp/c.yaml",
            "chezmoi status --init",
            "chezmoi status -c /tmp/c.yaml",
            "chezmoi verify --init=true",
            "chezmoi verify -D /tmp/d",
            "HOME=/tmp/h chezmoi diff",
            "XDG_CONFIG_HOME=/tmp/c chezmoi status",
            "XDG_DATA_HOME=/tmp/d chezmoi verify",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))
        for command in (
            "chezmoi --no-pager data --format yaml",
            "chezmoi --no-pager diff --reverse ~/.zshrc",
            "chezmoi --no-pager managed --path-style source-absolute",
            "chezmoi diff -r ~/Documents",
            "chezmoi doctor --no-network",
            "chezmoi help diff",
            "chezmoi ignored -t",
            "chezmoi managed --source-path ~/.local/share/chezmoi/dot_zshrc.tmpl",
            "chezmoi managed -p source-absolute",
            "chezmoi status -x scripts",
            "chezmoi status --exclude=scripts,encrypted",
            "chezmoi unmanaged -p absolute ~/.config",
            "chezmoi verify --use-builtin-diff ~/.zshrc",
            # The chezmoi excludes start with chezmoi, so the other commands in
            # the rule keep their -c and -D flags.
            "base64 -D x",
            "sort -c x",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.shell_allows(command))

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

    def test_every_allow_shell_rule_excludes_secret_locations(self) -> None:
        # A command substitution can feed a secret to any allowed command.
        patterns = secret_patterns()
        self.assertIn("*.aws/*", patterns)
        for rule in self.allow_rules_for("shell"):
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

    def test_agent_browser_navigation_and_page_reads_are_allowed(self) -> None:
        for command in (
            "agent-browser --engine lightpanda open https://example.com",
            "agent-browser back",
            "agent-browser click @e2",
            "agent-browser close",
            "agent-browser fill @e3 test@example.com",
            "agent-browser find role button click --name Submit",
            "agent-browser get text @e1",
            "agent-browser goto https://example.com",
            "agent-browser is visible @e1",
            "agent-browser open https://example.com",
            "agent-browser open https://example.com --json",
            "agent-browser scroll down 500",
            "agent-browser snapshot -i",
            "agent-browser tab list",
            "agent-browser tab new",
            "agent-browser wait --load networkidle",
            "agent-browser wait 2000",
        ):
            with self.subTest(command=command):
                self.assertTrue(self.shell_allows(command))

    def test_agent_browser_prompts_for_profiles_files_and_scripts(self) -> None:
        # Each of these reaches the owner's logged-in browser, reads or writes
        # local files, or runs code, wherever the option sits on the line.
        for command in (
            "agent-browser --auto-connect snapshot",
            "agent-browser --cdp 9222 snapshot",
            "agent-browser --cdp ws://127.0.0.1:9222/devtools/browser tab new",
            "agent-browser --config /tmp/c.json open https://example.com",
            "agent-browser --download-path ~ open https://example.com",
            "agent-browser --engine lightpanda --cdp 9222 open https://example.com",
            "agent-browser --engine lightpanda eval document.cookie",
            "agent-browser --executable-path /tmp/x open https://example.com",
            "agent-browser --init-script /tmp/x.js open https://example.com",
            "agent-browser --profile Default open https://mail.google.com",
            "agent-browser --session s eval document.cookie",
            "agent-browser --state ./auth.json open https://example.com",
            "agent-browser -p ios open https://example.com",
            "agent-browser auth login site",
            "agent-browser batch 'eval document.cookie'",
            "agent-browser chat hi",
            "agent-browser clipboard read",
            "agent-browser confirm c1",
            "agent-browser connect 9222",
            "agent-browser cookies get",
            "agent-browser download @e1 ~/x",
            "agent-browser eval document.cookie",
            "agent-browser flow run task",
            "agent-browser install",
            "agent-browser network har start ~/x.har",
            "agent-browser open https://example.com --allow-file-access",
            "agent-browser open https://example.com --args --user-data-dir=x",
            "agent-browser open https://example.com --profile ~/.p",
            "agent-browser pdf ~/x.pdf",
            "agent-browser plugin add x",
            "agent-browser record start ~/x.webm",
            "agent-browser screenshot ~/x.png",
            "agent-browser set credentials user pass",
            "agent-browser snapshot --cdp 9222",
            "agent-browser state save ./auth.json",
            "agent-browser storage local",
            "agent-browser trace stop ~/t.json",
            "agent-browser upload @e1 ~/.zshrc",
            "agent-browser wait --fn window.x",
            "agent-browser wait -f window.x",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))

    def test_mcporter_reads_that_save_to_a_path_are_not_allowed(self) -> None:
        tool = "mcporter call amazon-sharepoint-mcp.sharepoint_read_file"
        for command in (
            f"{tool} url=https://example.com/a.docx savePath=/Users/u/.zshrc",
            f"{tool} url=https://example.com/a.docx savePath:/Users/u/.zshrc",
            f'{tool} --args \'{{"url": "x", "savePath": "/Users/u/.zshrc"}}\'',
            f'mcporter call \'{tool.split()[-1]}(url: "x", savePath: "/u/.zshrc")\'',
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))
        self.assertTrue(self.shell_allows(f"{tool} url=https://example.com/a.docx"))

    def test_mcporter_options_that_run_or_redirect_servers_are_not_allowed(
        self,
    ) -> None:
        # These options start a program, load another config, call a tool the
        # selector does not name, send headers that expand environment
        # variables, or write files.
        get = "mcporter call slack-mcp.get_channel"
        for command in (
            f"{get} --config /tmp/c.json",
            f"{get} --cwd /",
            f"{get} --env A=1",
            f"{get} --root /tmp",
            f"{get} --server other",
            f"{get} --stdio 'sh -c id'",
            f"{get} --stdio-arg x",
            f"{get} --tool post_message",
            "mcporter call exa.web_search_exa query=x --save-images ~/x",
            "mcporter list --http-url https://example.com --header A=$env:B",
            "mcporter list --stdio 'touch /tmp/x'",
            "mcporter list --stdio x --persist ~/.zshrc",
            "mcporter resource docs --config /tmp/c.json",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))
        for command in (
            f"{get} channel=C1 --output json",
            "mcporter list slack-mcp --schema",
            "mcporter resource docs file:///repo/README.md",
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
        # $secretPaths in the template must stay identical to SECRET_PATTERNS so
        # the excludes and the hook guard the same locations.
        for pattern in secret_patterns():
            with self.subTest(pattern=pattern):
                self.assertIn(f'      "{pattern}"', self.raw)

    def test_rules_have_no_deny(self) -> None:
        self.assertNotIn("effect: deny", self.text)

    def test_secret_locations_have_a_standalone_ask_rule(self) -> None:
        # A standalone ask rule beats every preset and session allow, because
        # deny > ask > allow and an exclude on an allow never constrains another
        # allow. The same patterns stay as excludes on the allow rules so a
        # command that names a secret inside a command substitution also asks.
        ask = [rule for rule in self.rules_for("shell") if rule["effect"] == ["ask"]]
        self.assertEqual(len(ask), 1)
        self.assertEqual(ask[0]["match"], list(secret_patterns()))
        self.assertEqual(ask[0]["exclude"], [])
        # The first shell rule stays the general allow, so the exclude tests
        # keep inspecting it.
        self.assertEqual(self.rules_for("shell")[0]["effect"], ["allow"])
        for command in (
            "cat ~/.aws/credentials",
            "cat ~/.config/gh/hosts.yml",
            "cat ~/.codex/auth.json",
            "cat ~/.claude.json",
            "cat ~/.npmrc",
            "cat ~/.config/gcloud/credentials.db",
            "tail ~/.local/state/zsh/history",
            "cat ~/.zsh_history",
        ):
            with self.subTest(command=command):
                self.assertFalse(self.shell_allows(command))

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
