"""Regression tests for the Kiro CLI v3 hooks and the scripts they run."""

import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENFORCE_UV = REPO_ROOT / "dot_agents/hooks/executable_enforce-uv.sh"
JAPANESE_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_japanese-guard-kiro.py"
REDIRECT_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_redirect-guard-kiro.py"
HOOKS_DIR = REPO_ROOT / "dot_kiro/hooks"
CHEZMOIIGNORE = REPO_ROOT / ".chezmoiignore"

SESSION_ID = "sess_test"
GUARD_STUB = """\
REASON = "rewrite: {quoted}"


def is_english(text):
    return text.startswith("EN")
"""


def run_enforce_uv(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(ENFORCE_UV)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
    )


def claude_payload(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def kiro_payload(command: str) -> dict:
    return {
        "session_id": SESSION_ID,
        "hook_event_name": "PreToolUse",
        "cwd": "/tmp/project",
        "tool_name": "execute_bash",
        "tool_input": {"command": command, "description": "", "cwd": None},
    }


def event(payload: dict) -> str:
    return json.dumps({"payload": payload})


def say(text: str) -> str:
    return event({"type": "assistant", "operationType": "Say", "content": text})


class EnforceUvTest(unittest.TestCase):
    def test_blocks_pip_in_claude_and_kiro_payloads(self) -> None:
        for payload in (
            claude_payload("pip install foo"),
            kiro_payload("pip install foo"),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(run_enforce_uv(payload).returncode, 2)

    def test_allows_uv(self) -> None:
        self.assertEqual(run_enforce_uv(kiro_payload("uv add foo")).returncode, 0)


class JapaneseGuardKiroTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        hooks = self.tmp / "hooks"
        hooks.mkdir()
        self.script = hooks / "japanese-guard-kiro.py"
        shutil.copy(JAPANESE_GUARD_KIRO, self.script)
        (hooks / "japanese-guard.py").write_text(GUARD_STUB)
        self.session_dir = (
            self.tmp / "home/.kiro/sessions/0123456789abcdef" / SESSION_ID
        )
        self.session_dir.mkdir(parents=True)

    def write_session(self, *lines: str) -> None:
        (self.session_dir / "messages.jsonl").write_text("\n".join(lines) + "\n")

    def run_stop(self, session_id: str = SESSION_ID) -> str:
        payload = {
            "session_id": session_id,
            "hook_event_name": "Stop",
            "cwd": "/tmp/project",
        }
        env = dict(os.environ, HOME=str(self.tmp / "home"), TMPDIR=str(self.tmp))
        result = subprocess.run(
            ["python3", str(self.script)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return result.stdout

    def test_blocks_english_answer(self) -> None:
        self.write_session(event({"type": "user", "content": "q"}), say("EN answer"))
        out = json.loads(self.run_stop())
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "rewrite: - EN answer")

    def test_passes_japanese_answer(self) -> None:
        self.write_session(event({"type": "user", "content": "q"}), say("日本語の回答"))
        self.assertEqual(self.run_stop(), "")

    def test_checks_only_text_after_last_tool_call(self) -> None:
        self.write_session(
            event({"type": "user", "content": "q"}),
            say("EN before the tool"),
            event({"type": "tool_call", "toolName": "execute_bash"}),
            event({"type": "tool_result", "content": "Output"}),
            event(
                {
                    "type": "assistant",
                    "operationType": "Reasoning",
                    "content": "EN thinking",
                }
            ),
            say("日本語の回答"),
        )
        self.assertEqual(self.run_stop(), "")

    def test_every_stop_is_checked(self) -> None:
        # Kiro does not fire Stop again for the turn a block continues, so the
        # next Stop belongs to a new turn and must be checked too.
        self.write_session(event({"type": "user", "content": "q"}), say("EN answer"))
        self.assertNotEqual(self.run_stop(), "")
        self.assertNotEqual(self.run_stop(), "")

    def test_prefers_log_under_current_cwd_hash(self) -> None:
        current = hashlib.sha256(b"/tmp/project").hexdigest()[:16]
        stale = self.tmp / "home/.kiro/sessions/0000000000000000" / SESSION_ID
        stale.mkdir(parents=True)
        (stale / "messages.jsonl").write_text(say("EN stale answer") + "\n")
        self.session_dir = self.tmp / "home/.kiro/sessions" / current / SESSION_ID
        self.session_dir.mkdir(parents=True)
        self.write_session(event({"type": "user", "content": "q"}), say("日本語の回答"))
        self.assertEqual(self.run_stop(), "")

    def test_missing_session_passes(self) -> None:
        self.assertEqual(self.run_stop(session_id="sess_missing"), "")


class RedirectGuardKiroTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp()).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.workspace = self.home / "project"
        self.workspace.mkdir(parents=True)

    def run_guard(self, command: str) -> subprocess.CompletedProcess[str]:
        payload = kiro_payload(command)
        payload["cwd"] = str(self.workspace)
        return subprocess.run(
            ["python3", str(REDIRECT_GUARD_KIRO)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=dict(os.environ, HOME=str(self.home)),
            check=False,
        )

    def test_allows_writes_inside_allowed_paths(self) -> None:
        for command in (
            "echo hi > out.txt",
            "echo hi >> sub/out.txt",
            "echo hi > /tmp/out.txt",
            "echo hi > ~/Desktop/out.txt",
            "echo hi > ~/Downloads/out.txt",
            f"echo hi > {self.workspace}/out.txt",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard(command).returncode, 0)

    def test_allows_devices_fd_duplication_and_quoted_text(self) -> None:
        for command in (
            "rg x 2>/dev/null",
            "rg x > /dev/stdout 2>&1",
            "rg x >&2",
            "echo 'a>b'",
            'echo "a >> b"',
            "cat < input.txt",
            "cat <<EOF",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard(command).returncode, 0)

    def test_blocks_writes_outside_allowed_paths(self) -> None:
        for command in (
            "echo hi > ~/out.txt",
            "echo hi >> /etc/hosts",
            "echo hi &> ~/out.txt",
            "echo hi >| ~/out.txt",
            "echo hi > ../out.txt",
            "echo hi 2> ~/err.txt",
            "cat <> ~/out.txt",
            "rg x && echo hi > ~/out.txt",
            "echo $(echo hi > ~/out.txt)",
        ):
            with self.subTest(command=command):
                result = self.run_guard(command)
                self.assertEqual(result.returncode, 2)
                self.assertIn("write tool", result.stderr)

    def test_blocks_targets_it_cannot_resolve(self) -> None:
        for command in (
            "echo hi > $HOME/out.txt",
            "echo hi > `pwd`/out.txt",
            "echo hi >(cat)",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard(command).returncode, 2)

    def test_blocks_symlink_escaping_the_workspace(self) -> None:
        (self.workspace / "link").symlink_to(self.home)
        self.assertEqual(self.run_guard("echo hi > link/out.txt").returncode, 2)


def hook_file(name: str) -> dict:
    return json.loads(
        (HOOKS_DIR / name).read_text().replace("{{ .chezmoi.homeDir }}", "/home/u")
    )


def triggers(config: dict) -> list[tuple[str, str]]:
    return [(hook["trigger"], hook["action"]["command"]) for hook in config["hooks"]]


class KiroHookFilesTest(unittest.TestCase):
    def test_agent_guards(self) -> None:
        config = hook_file("agent-guards.json.tmpl")
        self.assertEqual(config["version"], "v1")
        self.assertEqual(
            triggers(config),
            [
                ("PreToolUse", "/home/u/.agents/hooks/enforce-uv.sh"),
                ("PreToolUse", "/home/u/.agents/hooks/redirect-guard-kiro.py"),
                ("Stop", "/home/u/.agents/hooks/japanese-guard-kiro.py"),
            ],
        )
        for hook in config["hooks"][:2]:
            self.assertEqual(hook["matcher"], "^execute_bash$")

    def test_otty_state(self) -> None:
        state = "/home/u/.kiro/hooks/otty-state.sh"
        self.assertEqual(
            triggers(hook_file("otty-state.json.tmpl")),
            [
                ("SessionStart", f"{state} idle"),
                ("UserPromptSubmit", f"{state} processing"),
                ("PreToolUse", f"{state} processing"),
                ("PostToolUse", f"{state} processing"),
                ("Stop", f"{state} idle"),
            ],
        )


class ChezmoiIgnoreTest(unittest.TestCase):
    def test_linux_ignores_only_otty_hooks(self) -> None:
        text = CHEZMOIIGNORE.read_text()
        start = text.index("{{- else }}\n")
        linux = text[start : text.index("{{- end }}", start)].splitlines()
        self.assertIn(".kiro/hooks/otty-state.json", linux)
        self.assertIn(".kiro/hooks/otty-state.sh", linux)
        self.assertNotIn(".kiro/hooks", linux)


if __name__ == "__main__":
    unittest.main()
