"""Regression tests for the Kiro CLI v3 hooks and the scripts they run."""

import base64
import hashlib
import json
import os
import pathlib
import re
import shlex
import shutil
import subprocess
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENFORCE_UV = REPO_ROOT / "dot_agents/hooks/executable_enforce-uv.sh"
JAPANESE_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_japanese-guard-kiro.py"
OTTY_KIRO = REPO_ROOT / "dot_agents/hooks/executable_otty-kiro.py"
REDIRECT_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_redirect-guard-kiro.py"
HOOKS_DIR = REPO_ROOT / "private_dot_kiro/hooks"
CHEZMOIIGNORE = REPO_ROOT / ".chezmoiignore"
ZSHRC = REPO_ROOT / "dot_zshrc.tmpl"

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

    def run_guard(
        self, command: str, tool_cwd: str | None = None
    ) -> subprocess.CompletedProcess[str]:
        payload = kiro_payload(command)
        payload["cwd"] = str(self.workspace)
        payload["tool_input"]["cwd"] = tool_cwd
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

    def test_blocks_redirects_hidden_by_hash_or_fused_punctuation(self) -> None:
        # Bash starts a comment only at a word boundary, so x#y is one word.
        for command in (
            "printf x#y >> /etc/passwd",
            "echo hi;> ~/out.txt",
            "echo hi;>>~/out.txt",
            "(echo hi)>~/out.txt",
            "rg x;>(cat)",
        ):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard(command).returncode, 2)

    def test_allows_fused_punctuation_inside_allowed_paths(self) -> None:
        for command in ("echo hi;> out.txt", "(echo hi)>/tmp/out.txt", "echo a;>&2"):
            with self.subTest(command=command):
                self.assertEqual(self.run_guard(command).returncode, 0)

    def test_tool_cwd_does_not_widen_allowed_paths(self) -> None:
        for command, tool_cwd in (
            ("echo hi > /etc/hosts", "/"),
            ("echo hi > etc/hosts", "/"),
            ("echo hi > out.txt", str(self.home)),
        ):
            with self.subTest(command=command, tool_cwd=tool_cwd):
                self.assertEqual(self.run_guard(command, tool_cwd).returncode, 2)

    def test_tool_cwd_resolves_relative_targets(self) -> None:
        (self.workspace / "sub").mkdir()
        self.assertEqual(
            self.run_guard("echo hi > out.txt", str(self.workspace / "sub")).returncode,
            0,
        )
        self.assertEqual(self.run_guard("echo hi > out.txt", "sub").returncode, 0)
        self.assertEqual(self.run_guard("echo hi > ../out.txt", "sub").returncode, 0)
        self.assertEqual(self.run_guard("echo hi > ../../out.txt", "sub").returncode, 2)


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
                (
                    "SessionStart",
                    "/home/u/.agents/hooks/superpowers-session-start.sh kiro",
                ),
                ("Stop", "/home/u/.agents/hooks/japanese-guard-kiro.py"),
                ("Stop", "/home/u/.agents/hooks/away-continue.py kiro"),
            ],
        )
        for hook in config["hooks"][:2]:
            self.assertEqual(hook["matcher"], "^execute_bash$")


def osc_fields(data: bytes) -> list[str]:
    if not (data.startswith(b"\x1b]") and data.endswith(b"\x07")):
        raise AssertionError(f"not a single OSC sequence: {data!r}")
    return data[2:-1].decode().split(";")


def b64(value: str) -> str:
    return base64.b64decode(value).decode()


def arm_args(data: bytes) -> str:
    values = dict(field.split("=", 1) for field in osc_fields(data)[2:])
    return b64(values["args"])


class OttyKiroTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        hooks = self.tmp / "hooks"
        hooks.mkdir()
        self.script = hooks / "otty-kiro.py"
        shutil.copy(OTTY_KIRO, self.script)
        shutil.copy(JAPANESE_GUARD_KIRO, hooks / "japanese-guard-kiro.py")
        (hooks / "japanese-guard.py").write_text(GUARD_STUB)
        current = hashlib.sha256(b"/tmp/project").hexdigest()[:16]
        self.session_dir = self.tmp / "home/.kiro/sessions" / current / SESSION_ID
        self.session_dir.mkdir(parents=True)
        self.tty = self.tmp / "tty"
        self.tty.write_bytes(b"")

    def write_session(self, *lines: str) -> None:
        (self.session_dir / "messages.jsonl").write_text("\n".join(lines) + "\n")

    def run_process(
        self,
        event_name: str,
        *,
        tty: str | None = "",
        args: str = "chat",
        session_id: str = SESSION_ID,
    ) -> subprocess.CompletedProcess[str]:
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("KIRO_OTTY_TTY", "KIRO_OTTY_ARGS")
        }
        env["HOME"] = str(self.tmp / "home")
        env["KIRO_OTTY_ARGS"] = args
        if tty is not None:
            env["KIRO_OTTY_TTY"] = tty or str(self.tty)
        payload = {
            "session_id": session_id,
            "hook_event_name": event_name,
            "cwd": "/tmp/project",
        }
        return subprocess.run(
            ["python3", str(self.script), event_name],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )

    def run_hook(
        self, event_name: str, *, args: str = "chat", session_id: str = SESSION_ID
    ) -> bytes:
        result = self.run_process(event_name, args=args, session_id=session_id)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        return self.tty.read_bytes()

    def test_hook_file(self) -> None:
        hook = "/home/u/.agents/hooks/otty-kiro.py"
        self.assertEqual(
            triggers(hook_file("otty-kiro.json.tmpl")),
            [("SessionStart", f"{hook} session-start"), ("Stop", f"{hook} stop")],
        )

    def test_arm_resumes_the_session_with_launch_options(self) -> None:
        out = self.run_hook("session-start", args="chat --trust-all-tools --resume")
        fields = osc_fields(out)
        self.assertEqual(fields[:2], ["88", "arm"])
        values = dict(field.split("=", 1) for field in fields[2:])
        self.assertEqual(b64(values["cmd"]), "kiro-cli")
        self.assertEqual(
            b64(values["args"]), "chat --trust-all-tools --resume-id sess_test"
        )
        self.assertEqual(b64(values["cwd"]), "/tmp/project")

    def test_arm_drops_every_resume_flag(self) -> None:
        out = self.run_hook(
            "session-start",
            args="chat -r --resume-picker --resume-id old --resume-id=old2",
        )
        self.assertEqual(arm_args(out), "chat --resume-id sess_test")

    def test_arm_adds_chat_when_launched_without_arguments(self) -> None:
        out = self.run_hook("session-start", args="")
        self.assertEqual(arm_args(out), "chat --resume-id sess_test")

    def test_arm_keeps_quoted_arguments(self) -> None:
        out = self.run_hook("session-start", args="chat --agent 'my agent'")
        self.assertEqual(
            shlex.split(arm_args(out)),
            ["chat", "--agent", "my agent", "--resume-id", "sess_test"],
        )

    def test_stop_notifies_with_project_and_answer(self) -> None:
        self.write_session(
            event({"type": "user", "content": "q"}),
            say("## 結果\n\n**直した**よ。`a.py` を見てね"),
        )
        self.assertEqual(
            osc_fields(self.run_hook("stop")),
            ["777", "notify", "Kiro — project", "結果 直したよ。a.py を見てね"],
        )

    def test_stop_truncates_long_answers(self) -> None:
        self.write_session(say("あ" * 150))
        body = osc_fields(self.run_hook("stop"))[3]
        self.assertEqual(body, "あ" * 99 + "…")

    def test_stop_drops_code_fences(self) -> None:
        self.write_session(say("修正したよ\n```python\nprint(1)\n```"))
        self.assertEqual(osc_fields(self.run_hook("stop"))[3], "修正したよ print(1)")

    def test_stop_skips_english_answer(self) -> None:
        self.write_session(say("EN answer"))
        self.assertEqual(self.run_hook("stop"), b"")

    def test_stop_uses_stock_body_for_empty_answer(self) -> None:
        self.write_session(event({"type": "user", "content": "q"}))
        self.assertEqual(osc_fields(self.run_hook("stop"))[3], "Response complete")

    def test_notification_strips_separators_and_controls(self) -> None:
        self.write_session(say("a;b\x1b[31m赤\x07c"))
        fields = osc_fields(self.run_hook("stop"))
        self.assertEqual(len(fields), 4)
        self.assertNotRegex(fields[3], r"[\x00-\x1f\x7f]")

    def test_does_nothing_without_tty(self) -> None:
        self.write_session(say("日本語の回答"))
        result = self.run_process("stop", tty=None)
        self.assertEqual((result.returncode, result.stdout), (0, ""))
        self.assertEqual(self.tty.read_bytes(), b"")

    def test_unwritable_tty_is_ignored(self) -> None:
        self.write_session(say("日本語の回答"))
        result = self.run_process("stop", tty=str(self.tmp / "missing/tty"))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

    def test_rejects_bad_session_id(self) -> None:
        for session_id in ("", "../x"):
            with self.subTest(session_id=session_id):
                self.assertEqual(
                    self.run_hook("session-start", session_id=session_id), b""
                )


FAKE_KIRO_CLI = """\
#!/bin/sh
[ -n "${KIRO_OTTY_TTY+x}" ] && echo "KIRO_OTTY_TTY=$KIRO_OTTY_TTY"
[ -n "${KIRO_OTTY_ARGS+x}" ] && echo "KIRO_OTTY_ARGS=$KIRO_OTTY_ARGS"
exit "${FAKE_STATUS:-0}"
"""


class KiroWrapperTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = pathlib.Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        fake = bin_dir / "kiro-cli"
        fake.write_text(FAKE_KIRO_CLI)
        fake.chmod(0o755)
        self.path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"
        match = re.search(
            r"^kiro-cli\(\) \{\n.*?^\}\n", ZSHRC.read_text(), re.MULTILINE | re.DOTALL
        )
        if match is None:
            self.fail("kiro-cli function not found in dot_zshrc.tmpl")
        self.function = match.group()

    def run_wrapper(self, *args: str, fake_status: int = 0) -> bytes:
        # script(1) gives zsh a real tty, so $TTY is set as in an Otty pane.
        code = self.function + 'kiro-cli "$@"; echo "status=$?"\n'
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("KIRO_OTTY_TTY", "KIRO_OTTY_ARGS")
        }
        env.update(PATH=self.path, FAKE_STATUS=str(fake_status))
        result = subprocess.run(
            ["script", "-q", "/dev/null", "zsh", "-fc", code, "zsh", *args],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=env,
            check=True,
        )
        return result.stdout.replace(b"\r", b"")

    def test_wrapper_passes_tty_and_quoted_arguments(self) -> None:
        out = self.run_wrapper("chat", "--agent", "my agent")
        self.assertRegex(out, rb"KIRO_OTTY_TTY=/dev/ttys\d+\n")
        self.assertIn(b"KIRO_OTTY_ARGS=chat --agent 'my agent'\n", out)

    def test_wrapper_clears_and_keeps_exit_status(self) -> None:
        out = self.run_wrapper("chat", fake_status=3)
        self.assertIn(b"\x1b]88;clear\x07", out)
        self.assertIn(b"status=3\n", out)

    def test_wrapper_treats_no_arguments_as_chat(self) -> None:
        out = self.run_wrapper()
        self.assertRegex(out, rb"KIRO_OTTY_TTY=/dev/ttys\d+\n")
        self.assertIn(b"KIRO_OTTY_ARGS=\n", out)

    def test_wrapper_passes_other_subcommands_through(self) -> None:
        out = self.run_wrapper("settings", "list", fake_status=2)
        self.assertNotIn(b"KIRO_OTTY_TTY=", out)
        self.assertNotIn(b"\x1b]88;clear", out)
        self.assertIn(b"status=2\n", out)


class ChezmoiIgnoreTest(unittest.TestCase):
    def test_linux_ignores_only_otty_hooks(self) -> None:
        text = CHEZMOIIGNORE.read_text()
        start = text.index("{{- else }}\n")
        linux = text[start : text.index("{{- end }}", start)].splitlines()
        self.assertIn(".agents/hooks/otty-kiro.py", linux)
        self.assertIn(".kiro/hooks/otty-kiro.json", linux)
        self.assertNotIn(".kiro/hooks/otty-state.json", linux)
        self.assertNotIn(".kiro/hooks/otty-state.sh", linux)
        self.assertNotIn(".kiro/hooks", linux)

    def test_removes_otty_state_hooks(self) -> None:
        lines = (REPO_ROOT / ".chezmoiremove").read_text().splitlines()
        self.assertIn(".kiro/hooks/otty-state.json", lines)
        self.assertIn(".kiro/hooks/otty-state.sh", lines)


if __name__ == "__main__":
    unittest.main()
