"""Regression tests for the user-level superpowers gates (Claude Code entry point)."""

import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import time
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAUDE = REPO_ROOT / "dot_agents/hooks/superpowers-gates/executable_claude"
CODEX = REPO_ROOT / "dot_agents/hooks/superpowers-gates/executable_codex"
KIRO = REPO_ROOT / "dot_agents/hooks/superpowers-gates/executable_kiro"
KIRO_TEMPLATE = REPO_ROOT / "private_dot_kiro/hooks/superpowers-gates.json.tmpl"
CODEX_TEMPLATE = REPO_ROOT / "dot_codex/modify_private_hooks.json.tmpl"
SETTINGS_TEMPLATE = REPO_ROOT / "dot_claude/modify_settings.json.tmpl"

SESSION_ID = "sess_test"
SKILLS = ("writing-plans", "brainstorming", "subagent-driven-development")
PLAN = "docs/superpowers/plans/x.md"
LEDGER = ".superpowers/sdd/p/progress.md"
GATES = "/home/u/.agents/hooks/superpowers-gates/claude"


def git_init(path: pathlib.Path) -> pathlib.Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "-q", str(path)],
        check=True,
        env={**os.environ, "GIT_CONFIG_GLOBAL": "/dev/null"},
    )
    return path


def hook_repo(path: pathlib.Path) -> pathlib.Path:
    """A repository that carries the project's own superpowers gates."""
    git_init(path)
    core = path / ".agents/hooks/superpowers-gates/core.sh"
    core.parent.mkdir(parents=True, exist_ok=True)
    core.write_text("# project hooks\n")
    return path


class GatesTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = pathlib.Path(self._tmp.name).resolve()
        self.home = tmp / "home"
        for skill in SKILLS:
            doc = self.home / ".agents/skills" / skill / "SKILL.md"
            doc.parent.mkdir(parents=True)
            doc.write_text(f"# {skill}\n")
        (self.home / ".claude/skills").mkdir(parents=True)
        (self.home / ".claude/skills/writing-plans").symlink_to(
            "../../.agents/skills/writing-plans"
        )
        self.repo = git_init(tmp / "repo")
        self.tmp = tmp
        self.path = "/usr/bin:/bin"
        self.extra_env = {}

    def run_hook(self, event, payload, cwd=None, script=None):
        env = {
            "HOME": str(self.home),
            "PATH": self.path,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            **self.extra_env,
        }
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            ["/bin/bash", str(script or CLAUDE), event],
            input=data,
            capture_output=True,
            text=True,
            env=env,
            cwd=cwd,
            check=False,
        )

    def payload(self, tool, tool_input, cwd=None):
        return {
            "session_id": SESSION_ID,
            "cwd": str(cwd or self.repo),
            "tool_name": tool,
            "tool_input": tool_input,
        }

    def write(self, relpath, repo=None, cwd=None):
        repo = repo or self.repo
        return self.run_hook(
            "pre-tool-use",
            self.payload(
                "Write", {"file_path": str(repo / relpath), "content": "x"}, cwd
            ),
        )

    def post_write(self, relpath, repo=None, cwd=None):
        repo = repo or self.repo
        return self.run_hook(
            "post-tool-use",
            self.payload(
                "Write", {"file_path": str(repo / relpath), "content": "x"}, cwd
            ),
        )

    def edit(self, relpath, old, new):
        return self.run_hook(
            "pre-tool-use",
            self.payload(
                "Edit",
                {
                    "file_path": str(self.repo / relpath),
                    "old_string": old,
                    "new_string": new,
                },
            ),
        )

    def read(self, path, cwd=None):
        return self.run_hook(
            "post-tool-use", self.payload("Read", {"file_path": str(path)}, cwd)
        )

    def read_skill(self, skill="writing-plans"):
        return self.read(self.home / ".agents/skills" / skill / "SKILL.md")

    def state_dir(self):
        return self.home / ".local/state/superpowers-gates/claude" / SESSION_ID

    def make_unfinished_ledger(self):
        plan = self.repo / "docs/superpowers/plans/p.md"
        plan.parent.mkdir(parents=True, exist_ok=True)
        plan.write_text("# Plan\n\n### Task 1: a\n\n### Task 2: b\n")
        ledger = self.repo / LEDGER
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(
            "# SDD ledger plan: docs/superpowers/plans/p.md\n\nTask 1: complete\n"
        )


class PreToolUseTest(GatesTestCase):
    def test_new_plan_is_blocked_without_read(self):
        result = self.write(PLAN)
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            f"Read ~/.agents/skills/writing-plans/SKILL.md before writing {PLAN}",
            result.stderr,
        )
        self.assertNotIn(str(self.home), result.stderr)

    def test_repo_skill_copy_is_named(self):
        doc = self.repo / ".agents/skills/writing-plans/SKILL.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# writing-plans\n")
        result = self.write(PLAN)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Read .agents/skills/writing-plans/SKILL.md", result.stderr)
        self.assertNotIn("~/.agents", result.stderr)

    def test_read_unlocks_one_write(self):
        self.read_skill()
        self.assertEqual(self.write(PLAN).returncode, 0)
        self.assertEqual(self.write("docs/superpowers/plans/y.md").returncode, 2)

    def test_read_through_claude_skill_link_unlocks(self):
        self.read(self.home / ".claude/skills/writing-plans/SKILL.md")
        self.assertEqual(self.write(PLAN).returncode, 0)

    def test_read_in_another_repo_unlocks_write(self):
        other = git_init(self.tmp / "other")
        self.read(self.home / ".agents/skills/writing-plans/SKILL.md", cwd=other)
        self.assertEqual(self.write(PLAN, repo=self.repo).returncode, 0)

    def test_skill_tool_counts_as_read(self):
        self.run_hook(
            "post-tool-use",
            self.payload("Skill", {"skill": "superpowers:writing-plans"}),
        )
        self.assertEqual(self.write(PLAN).returncode, 0)

    def test_small_edit_is_allowed(self):
        result = self.edit(PLAN, "a\nb\nc", "a\nb\nc\nd")
        self.assertEqual(result.returncode, 0)

    def test_large_edit_in_window_is_allowed(self):
        self.read_skill()
        self.assertEqual(self.write(PLAN).returncode, 0)
        old = "\n".join(f"o{i}" for i in range(12))
        new = "\n".join(f"n{i}" for i in range(13))
        self.assertEqual(self.edit(PLAN, old, new).returncode, 0)
        windows = list(self.state_dir().glob("window-*"))
        self.assertEqual(len(windows), 1)
        windows[0].write_text(f"{int(time.time()) - 3601}\n")
        self.assertEqual(self.edit(PLAN, old, new).returncode, 2)

    def test_spec_subdirectory_is_gated(self):
        result = self.write("docs/superpowers/specs/a/b c.md")
        self.assertEqual(result.returncode, 2)
        self.assertIn("brainstorming/SKILL.md", result.stderr)

    def test_new_ledger_needs_sdd_read(self):
        self.assertEqual(self.write(LEDGER).returncode, 2)
        self.read_skill("subagent-driven-development")
        self.assertEqual(self.write(LEDGER).returncode, 0)
        (self.repo / LEDGER).parent.mkdir(parents=True)
        (self.repo / LEDGER).write_text("# ledger\n")
        big = "\n".join(f"l{i}" for i in range(30))
        self.assertEqual(self.edit(LEDGER, "# ledger", big).returncode, 0)


class PostToolUseTest(GatesTestCase):
    def test_reminder_after_plan_write(self):
        result = self.run_hook(
            "post-tool-use",
            self.payload("Write", {"file_path": str(self.repo / PLAN), "content": "x"}),
        )
        self.assertEqual(result.returncode, 0)
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(
            "Self-Review checklist in ~/.agents/skills/writing-plans/SKILL.md", context
        )


class SessionStartTest(GatesTestCase):
    def session_start(self, source):
        return self.run_hook(
            "session-start",
            {"session_id": SESSION_ID, "cwd": str(self.repo), "source": source},
        )

    def test_compact_names_unfinished_ledger(self):
        self.make_unfinished_ledger()
        self.post_write(LEDGER)
        result = self.session_start("compact")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn(".superpowers/sdd/p/progress.md", output["additionalContext"])
        self.assertIn(
            "If this session is executing the plan in docs/superpowers/plans/p.md, "
            "re-read ~/.agents/skills/subagent-driven-development/SKILL.md "
            "and that ledger before continuing.",
            output["additionalContext"],
        )

    def test_compact_ignores_ledger_the_session_never_touched(self):
        self.make_unfinished_ledger()
        result = self.session_start("compact")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_compact_names_ledger_in_plain_repo_from_hooked_session(self):
        hooked = hook_repo(self.tmp / "hooked")
        self.make_unfinished_ledger()
        self.post_write(LEDGER, cwd=hooked)
        result = self.run_hook(
            "session-start",
            {"session_id": SESSION_ID, "cwd": str(hooked), "source": "compact"},
        )
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn(LEDGER, context)

    def test_compact_skips_finished_ledger(self):
        self.make_unfinished_ledger()
        self.post_write(LEDGER)
        with (self.repo / LEDGER).open("a") as f:
            f.write("Task 2: complete\n")
        result = self.session_start("compact")
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_startup_prints_nothing(self):
        self.make_unfinished_ledger()
        self.post_write(LEDGER)
        result = self.session_start("startup")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


class UserPromptSubmitTest(GatesTestCase):
    def prompt(self, text):
        return self.run_hook(
            "user-prompt-submit",
            {"session_id": SESSION_ID, "cwd": str(self.repo), "prompt": text},
        )

    def test_slash_command_counts_as_read(self):
        for text in (
            "/writing-plans",
            "/superpowers:writing-plans make it",
            "  /writing-plans\nmore",
        ):
            shutil.rmtree(self.home / ".local", ignore_errors=True)
            self.assertEqual(self.write(PLAN).returncode, 2)
            result = self.prompt(text)
            self.assertEqual((result.returncode, result.stdout), (0, ""))
            self.assertEqual(self.write(PLAN).returncode, 0, text)

    def test_other_slash_commands_and_prose_do_not(self):
        for text in (
            "/review",
            "/writing-plans-extra",
            "please run /writing-plans",
            "use writing-plans",
        ):
            self.prompt(text)
            self.assertEqual(self.write(PLAN).returncode, 2, text)

    def test_brainstorming_and_sdd_commands(self):
        self.prompt("/brainstorming idea")
        self.assertEqual(self.write("docs/superpowers/specs/s.md").returncode, 0)
        self.prompt("/superpowers:subagent-driven-development")
        self.assertEqual(self.write(LEDGER).returncode, 0)


class SkipTest(GatesTestCase):
    def assert_silent_allow(self, result):
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")

    def test_defers_to_project_hooks(self):
        hook_repo(self.repo)
        for result in (self.write(PLAN), self.post_write(PLAN)):
            self.assert_silent_allow(result)

    def test_old_project_marker_no_longer_defers(self):
        core = self.repo / "scripts/agent-hooks/core.sh"
        core.parent.mkdir(parents=True)
        core.write_text("# old location\n")
        self.assertEqual(self.write(PLAN).returncode, 2)

    def test_session_elsewhere_is_gated_in_hooked_repo(self):
        hook_repo(self.repo)
        elsewhere = git_init(self.tmp / "elsewhere")
        self.assertEqual(self.write(PLAN, cwd=elsewhere).returncode, 2)
        self.assertEqual(self.write(PLAN, cwd=self.tmp).returncode, 2)

    def test_hooked_session_defers_for_another_hooked_repo(self):
        hook_repo(self.repo)
        other = hook_repo(self.tmp / "other")
        self.assert_silent_allow(self.write(PLAN, repo=other, cwd=self.repo))
        self.assert_silent_allow(self.write(PLAN, repo=self.repo, cwd=other))

    def test_claude_project_dir_is_the_session_root(self):
        hooked = hook_repo(self.tmp / "hooked")
        plain = git_init(self.tmp / "plain")
        self.extra_env = {"CLAUDE_PROJECT_DIR": str(plain)}
        self.assertEqual(self.write(PLAN, repo=hooked, cwd=hooked).returncode, 2)
        self.extra_env = {"CLAUDE_PROJECT_DIR": str(hooked)}
        self.assert_silent_allow(self.write(PLAN, repo=hooked, cwd=plain))

    def test_hooked_session_is_gated_in_plain_repo(self):
        hooked = hook_repo(self.tmp / "hooked")
        self.assertEqual(self.write(PLAN, repo=self.repo, cwd=hooked).returncode, 2)

    def test_disabled_by_env(self):
        self.extra_env = {"SUPERPOWERS_GATES": "off"}
        result = self.write(PLAN)
        self.assertEqual(result.returncode, 0)
        self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_malformed_input_allows(self):
        for data in ("{", "{}"):
            result = self.run_hook("pre-tool-use", data)
            self.assertEqual(result.returncode, 0)
            self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_outside_git_repo_allows(self):
        plain = self.tmp / "plain"
        plain.mkdir()
        result = self.write(PLAN, repo=plain)
        self.assertEqual(result.returncode, 0)
        self.assertEqual((result.stdout, result.stderr), ("", ""))

    def test_empty_path(self):
        self.path = ""
        self.assertEqual(self.write(PLAN).returncode, 2)
        self.read_skill()
        self.assertEqual(self.write(PLAN).returncode, 0)

    def test_old_sessions_are_pruned(self):
        parent = self.home / ".local/state/superpowers-gates/claude"
        old = parent / "old_session"
        old.mkdir(parents=True)
        stale = time.time() - 31 * 86400
        os.utime(old, (stale, stale))
        self.write(PLAN)
        self.assertFalse(old.exists())
        self.assertTrue(self.state_dir().exists())

    def test_current_stale_session_is_kept(self):
        current = self.state_dir()
        current.mkdir(parents=True)
        stale = time.time() - 31 * 86400
        os.utime(current, (stale, stale))
        self.read_skill()
        self.assertTrue(current.is_dir())
        self.assertTrue((current / "read-writing-plans").exists())
        self.assertEqual(self.write(PLAN).returncode, 0)


class SettingsTemplateTest(unittest.TestCase):
    def render(self, stdin: str) -> str:
        script = SETTINGS_TEMPLATE.read_text().replace(
            "{{ .chezmoi.homeDir }}", "/home/u"
        )
        return subprocess.run(
            ["bash", "-c", script],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def test_settings_template_registers_gates(self):
        hooks = json.loads(self.render("{}"))["hooks"]
        expected = {
            "PreToolUse": ("Write|Edit|MultiEdit", f"{GATES} pre-tool-use"),
            "PostToolUse": (
                "Read|Skill|Bash|Write|Edit|MultiEdit",
                f"{GATES} post-tool-use",
            ),
            "SessionStart": ("compact", f"{GATES} session-start"),
            "UserPromptSubmit": (None, f"{GATES} user-prompt-submit"),
        }
        for event, (matcher, command) in expected.items():
            entry = {"hooks": [{"type": "command", "command": command}]}
            if matcher:
                entry = {"matcher": matcher, **entry}
            self.assertIn(entry, hooks[event])

    def test_settings_template_is_idempotent(self):
        first = self.render("{}")
        self.assertEqual(self.render(first), first)
        otty = json.loads(first)
        otty["hooks"]["PreToolUse"].append(
            {"matcher": "x", "hooks": [{"type": "command", "command": "otty-hook"}]}
        )
        text = json.dumps(otty, indent=2) + "\n"
        out = self.render(text)
        self.assertEqual(out, text)
        self.assertIn("otty-hook", out)
        removed = json.loads(first)
        del removed["hooks"]["SessionStart"][-1]
        self.assertIn(GATES, self.render(json.dumps(removed)))
        removed = json.loads(first)
        del removed["hooks"]["UserPromptSubmit"]
        self.assertIn(f"{GATES} user-prompt-submit", self.render(json.dumps(removed)))


class CodexTest(GatesTestCase):
    def codex(self, event, payload):
        return self.run_hook(event, payload, script=CODEX)

    def patch_payload(self, patch, tool="apply_patch"):
        return {
            "session_id": SESSION_ID,
            "cwd": str(self.repo),
            "tool_name": tool,
            "tool_input": {"command": patch},
        }

    def pre_patch(self, patch):
        return self.codex("pre-tool-use", self.patch_payload(patch))

    def read_via_cat(self, skill="writing-plans"):
        command = f"cat ~/.agents/skills/{skill}/SKILL.md"
        return self.codex("post-tool-use", self.patch_payload(command, "Bash"))

    @staticmethod
    def envelope(*sections):
        return "*** Begin Patch\n" + "".join(sections) + "*** End Patch\n"

    @staticmethod
    def add(path, body="+x\n"):
        return f"*** Add File: {path}\n{body}"

    @staticmethod
    def update(path, body):
        return f"*** Update File: {path}\n@@\n{body}"

    @staticmethod
    def delete(path):
        return f"*** Delete File: {path}\n"

    def test_codex_add_plan_is_blocked(self):
        result = self.pre_patch(self.envelope(self.add(PLAN)))
        self.assertEqual(result.returncode, 2)
        self.assertIn(
            f"Read ~/.agents/skills/writing-plans/SKILL.md before writing {PLAN}",
            result.stderr,
        )

    def test_codex_cat_skill_counts_as_read(self):
        patch = self.envelope(self.add(PLAN))
        self.assertEqual(self.pre_patch(patch).returncode, 2)
        self.read_via_cat()
        self.assertEqual(self.pre_patch(patch).returncode, 0)

    def test_codex_small_update_is_allowed(self):
        body = "+a\n+b\n+c\n-d\n-e\n"
        patch = self.envelope(self.update(PLAN, body))
        self.assertEqual(self.pre_patch(patch).returncode, 0)

    def test_codex_dash_prefixed_lines_count(self):
        body = "----\n++x\n" * 11
        patch = self.envelope(self.update(PLAN, body))
        self.assertEqual(self.pre_patch(patch).returncode, 2)

    def test_codex_delete_does_not_hide_a_plan(self):
        patch = self.envelope(self.add(PLAN), self.delete("x"), self.add("y"))
        self.assertEqual(self.pre_patch(patch).returncode, 2)
        patch = self.envelope(
            self.update(PLAN, "+a\n" * 25),
            self.delete("x"),
            self.update("y", "+b\n"),
        )
        self.assertEqual(self.pre_patch(patch).returncode, 2)

    def test_codex_prompt_mention_counts_as_read(self):
        prompt = {
            "session_id": SESSION_ID,
            "cwd": str(self.repo),
            "prompt": "use $writing-plans",
        }
        self.assertEqual(self.codex("user-prompt-submit", prompt).returncode, 0)
        patch = self.envelope(self.add(PLAN))
        self.assertEqual(self.pre_patch(patch).returncode, 0)

    def test_codex_reminder_after_add(self):
        result = self.codex(
            "post-tool-use", self.patch_payload(self.envelope(self.add(PLAN)))
        )
        self.assertEqual(result.returncode, 0)
        context = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(context["hookEventName"], "PostToolUse")
        self.assertIn("Self-Review checklist", context["additionalContext"])

    def test_codex_post_compact_names_ledger(self):
        self.make_unfinished_ledger()
        self.codex(
            "post-tool-use",
            self.patch_payload(self.envelope(self.update(LEDGER, "+x\n"))),
        )
        result = self.codex(
            "post-compact", {"session_id": SESSION_ID, "cwd": str(self.repo)}
        )
        self.assertEqual(result.returncode, 0)
        context = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(context["hookEventName"], "PostCompact")
        self.assertIn(LEDGER, context["additionalContext"])
        self.assertIn(
            "If this session is executing the plan in", context["additionalContext"]
        )

    def test_codex_post_compact_ignores_untouched_ledger(self):
        self.make_unfinished_ledger()
        result = self.codex(
            "post-compact", {"session_id": SESSION_ID, "cwd": str(self.repo)}
        )
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def test_codex_absolute_path_into_other_repo_is_gated(self):
        hooked = hook_repo(self.tmp / "hooked")
        elsewhere = git_init(self.tmp / "elsewhere")
        patch = self.envelope(self.add(str(hooked / PLAN)))
        payload = self.patch_payload(patch)
        payload["cwd"] = str(elsewhere)
        self.assertEqual(self.codex("pre-tool-use", payload).returncode, 2)
        payload["cwd"] = str(hooked)
        result = self.codex("pre-tool-use", payload)
        self.assertEqual((result.returncode, result.stderr), (0, ""))

    def test_codex_mixed_patch_blocks_only_the_gated_repo(self):
        hooked = hook_repo(self.tmp / "hooked")
        patch = self.envelope(
            self.add(str(hooked / PLAN)),
            self.add(str(self.repo / "docs/superpowers/specs/s.md")),
        )
        payload = self.patch_payload(patch)
        payload["cwd"] = str(hooked)
        result = self.codex("pre-tool-use", payload)
        self.assertEqual(result.returncode, 2)
        self.assertIn("brainstorming/SKILL.md", result.stderr)
        self.assertNotIn("writing-plans", result.stderr)

    def test_codex_post_compact_without_ledger_prints_nothing(self):
        result = self.codex(
            "post-compact", {"session_id": SESSION_ID, "cwd": str(self.repo)}
        )
        self.assertEqual((result.returncode, result.stdout), (0, ""))

    def render_codex(self, stdin):
        script = CODEX_TEMPLATE.read_text().replace("{{ .chezmoi.homeDir }}", "/home/u")
        return subprocess.run(
            ["bash", "-c", script],
            input=stdin,
            capture_output=True,
            text=True,
            check=True,
        ).stdout

    def test_codex_template_is_idempotent(self):
        first = self.render_codex("{}")
        hooks = json.loads(first)["hooks"]
        gates = "/home/u/.agents/hooks/superpowers-gates/codex"
        for event, entry_matcher, command in (
            ("PreToolUse", "^apply_patch$", "pre-tool-use"),
            ("PostToolUse", "^(apply_patch|Bash)$", "post-tool-use"),
            ("UserPromptSubmit", None, "user-prompt-submit"),
            ("PostCompact", None, "post-compact"),
        ):
            entry = {"hooks": [{"type": "command", "command": f"{gates} {command}"}]}
            if entry_matcher:
                entry = {"matcher": entry_matcher, **entry}
            self.assertIn(entry, hooks[event])
        self.assertNotIn("session-start", first)
        self.assertEqual(self.render_codex(first), first)
        extra = json.loads(first)
        extra["hooks"]["PreToolUse"].append(
            {"matcher": "x", "hooks": [{"type": "command", "command": "otty-hook"}]}
        )
        text = json.dumps(extra, indent=2) + "\n"
        out = self.render_codex(text)
        self.assertEqual(out, text)
        self.assertIn("otty-hook", out)
        self.assertIn("enforce-uv.sh", out)
        removed = json.loads(first)
        del removed["hooks"]["PostCompact"]
        self.assertIn(f"{gates} post-compact", self.render_codex(json.dumps(removed)))


class KiroTest(GatesTestCase):
    def kiro(self, event, tool, tool_input):
        payload = self.payload(tool, tool_input)
        payload["hook_event_name"] = event
        return self.run_hook(event, payload, script=KIRO)

    def kiro_write(self, tool="fs_write", relpath=PLAN, **extra):
        tool_input = {"path": str(self.repo / relpath), "text": "x"}
        tool_input.update(extra)
        return self.kiro("pre-tool-use", tool, tool_input)

    def test_kiro_new_plan_is_blocked(self):
        result = self.kiro_write()
        self.assertEqual(result.returncode, 2)
        self.assertIn("Read ~/.agents/skills/writing-plans/SKILL.md", result.stderr)
        self.assertIn("Self-Review checklist", result.stderr)

    def test_kiro_read_file_counts(self):
        skill = self.home / ".agents/skills/writing-plans/SKILL.md"
        read = self.kiro("post-tool-use", "read_file", {"path": str(skill)})
        self.assertEqual(read.returncode, 0)
        self.assertEqual(self.kiro_write().returncode, 0)

    def test_kiro_small_replace_is_allowed(self):
        (self.repo / PLAN).parent.mkdir(parents=True)
        (self.repo / PLAN).write_text("a\nb\n")
        result = self.kiro_write(
            "str_replace", oldStr="a\nb", newStr="c\nd\ne", replace_all=False
        )
        self.assertEqual(result.returncode, 0)

    def test_kiro_append_to_missing_file_is_a_create(self):
        result = self.kiro_write("fs_append", text="a\nb\nc")
        self.assertEqual(result.returncode, 2)

    def test_kiro_hooks_file_is_valid(self):
        config = json.loads(
            KIRO_TEMPLATE.read_text().replace("{{ .chezmoi.homeDir }}", "/home/u")
        )
        self.assertEqual(config["version"], "v1")
        by_trigger = {h["trigger"]: h for h in config["hooks"]}
        self.assertEqual(
            set(by_trigger), {"PreToolUse", "PostToolUse", "UserPromptSubmit"}
        )
        for hook in config["hooks"]:
            matcher = hook.get("matcher")
            if matcher is not None:
                self.assertTrue(matcher.startswith("^") and matcher.endswith("$"))
            self.assertTrue(hook["name"].startswith("superpowers-gates-"))
            self.assertTrue(
                hook["action"]["command"].startswith(
                    "/home/u/.agents/hooks/superpowers-gates/kiro "
                )
            )
        self.assertEqual(
            by_trigger["PreToolUse"]["matcher"], "^(fs_write|fs_append|str_replace)$"
        )
        self.assertEqual(by_trigger["PostToolUse"]["matcher"], "^read_file$")


if __name__ == "__main__":
    unittest.main()
