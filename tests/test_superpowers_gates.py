"""Regression tests for the user-level superpowers gates (Claude Code entry point)."""

import json
import os
import pathlib
import subprocess
import tempfile
import time
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAUDE = REPO_ROOT / "dot_agents/hooks/superpowers-gates/executable_claude"
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

    def run_hook(self, event, payload, cwd=None):
        env = {
            "HOME": str(self.home),
            "PATH": self.path,
            "GIT_CONFIG_GLOBAL": "/dev/null",
            **self.extra_env,
        }
        data = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            ["/bin/bash", str(CLAUDE), event],
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

    def write(self, relpath, repo=None):
        repo = repo or self.repo
        return self.run_hook(
            "pre-tool-use",
            self.payload("Write", {"file_path": str(repo / relpath), "content": "x"}),
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
        result = self.session_start("compact")
        self.assertEqual(result.returncode, 0)
        output = json.loads(result.stdout)["hookSpecificOutput"]
        self.assertEqual(output["hookEventName"], "SessionStart")
        self.assertIn(".superpowers/sdd/p/progress.md", output["additionalContext"])
        self.assertIn(
            "Re-read ~/.agents/skills/subagent-driven-development/SKILL.md",
            output["additionalContext"],
        )

    def test_startup_prints_nothing(self):
        self.make_unfinished_ledger()
        result = self.session_start("startup")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")


class SkipTest(GatesTestCase):
    def test_defers_to_project_hooks(self):
        core = self.repo / "scripts/agent-hooks/core.sh"
        core.parent.mkdir(parents=True)
        core.write_text("# project hooks\n")
        for result in (
            self.write(PLAN),
            self.run_hook(
                "post-tool-use",
                self.payload(
                    "Write", {"file_path": str(self.repo / PLAN), "content": "x"}
                ),
            ),
        ):
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertEqual(result.stderr, "")

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
        }
        for event, (matcher, command) in expected.items():
            self.assertIn(
                {
                    "matcher": matcher,
                    "hooks": [{"type": "command", "command": command}],
                },
                hooks[event],
            )

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


if __name__ == "__main__":
    unittest.main()
