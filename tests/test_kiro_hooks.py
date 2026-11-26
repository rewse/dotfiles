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
import sys
import tempfile
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
ENFORCE_UV = REPO_ROOT / "dot_agents/hooks/executable_enforce-uv.sh"
JAPANESE_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_japanese-guard-kiro.py"
OTTY_KIRO = REPO_ROOT / "dot_agents/hooks/executable_otty-kiro.py"
REDIRECT_GUARD_KIRO = REPO_ROOT / "dot_agents/hooks/executable_redirect-guard-kiro.py"
HOOKS_DIR = REPO_ROOT / "private_dot_kiro/hooks"
CHEZMOIIGNORE = REPO_ROOT / ".chezmoiignore"
SYSTEM_PYTHON = pathlib.Path("/usr/bin/python3")
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
        # /tmp is an allowed root, so the fake home must live elsewhere; Linux
        # puts tempfile's default directory under /tmp.
        self.tmp = pathlib.Path(tempfile.mkdtemp(dir="/var/tmp")).resolve()
        self.addCleanup(shutil.rmtree, self.tmp)
        self.home = self.tmp / "home"
        self.workspace = self.home / "project"
        self.workspace.mkdir(parents=True)
        (self.home / ".zshrc").write_text("")

    def run_guard(
        self,
        command: str,
        tool_cwd: str | None = None,
        session_cwd: pathlib.Path | None = None,
    ) -> subprocess.CompletedProcess[str]:
        payload = kiro_payload(command)
        payload["cwd"] = str(session_cwd or self.workspace)
        payload["tool_input"]["cwd"] = tool_cwd
        return self.run_raw(json.dumps(payload))

    def run_raw(self, stdin: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(REDIRECT_GUARD_KIRO)],
            input=stdin,
            capture_output=True,
            text=True,
            env=dict(os.environ, HOME=str(self.home)),
            check=False,
        )

    def assert_blocked(self, command: str, tool_cwd: str | None = None) -> None:
        result = self.run_guard(command, tool_cwd)
        self.assertEqual(result.returncode, 2, result.stdout)
        self.assertIn("write tool", result.stderr)
        self.assertEqual(result.stdout, "")

    def assert_silent(
        self,
        command: str,
        tool_cwd: str | None = None,
        session_cwd: pathlib.Path | None = None,
    ) -> None:
        result = self.run_guard(command, tool_cwd, session_cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(result.stderr, "")


    def test_blocks_redirects_outside_allowed_paths(self) -> None:
        for command in (
            "git log > ~/.zshrc",
            "git log >> ~/.zshrc",
            "git log &> ~/.zshrc",
            "git log >| ~/.zshrc",
            "echo hi >> /etc/hosts",
            "echo hi > ../out.txt",
            "echo hi 2> ~/err.txt",
            "cat <> ~/out.txt",
            "rg x && echo hi > ~/out.txt",
            "echo $(echo hi > ~/out.txt)",
            # zsh reads `!` after the operator as clobbering, not as the target.
            "echo x >! ~/.zshrc",
            "echo x >!~/.zshrc",
            "echo x 2>! ~/.zshrc",
            "echo x >! /etc/x",
            "echo x >>! ~/.zshrc",
            "echo x &>! ~/.zshrc",
            "echo x >&! ~/.zshrc",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_allows_redirects_inside_allowed_paths(self) -> None:
        for command in (
            "git log > /tmp/x",
            "git log > out.txt",
            "git log > /dev/null",
            "git log 2>&1",
            "echo hi >> sub/out.txt",
            "echo hi > ~/Desktop/out.txt",
            "echo hi > ~/Downloads/out.txt",
            f"echo hi > {self.workspace}/out.txt",
            "rg x > /dev/stdout 2>&1",
            "rg x >&2",
            "cat <<EOF",
            "git log >! /tmp/x",
            "git log >!out.txt",
        ):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_blocks_targets_it_cannot_resolve(self) -> None:
        for command in (
            "git log > $HOME/x",
            "git log > `pwd`/x",
            "echo hi >(cat)",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_blocks_writes_to_the_terminal(self) -> None:
        self.assert_blocked("printf x > /dev/tty")

    def test_allows_redirect_characters_inside_quotes(self) -> None:
        for command in (
            'echo "a > b"',
            "git log --format='%h > %s'",
            "echo 'a>b'",
            'echo "a >> b"',
        ):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_ignores_here_document_bodies(self) -> None:
        for command in (
            "cat <<'EOF' > /tmp/x\na > ~/.zshrc\nit's\nEOF",
            "git commit -F - <<'EOF'\nfix: don't stop\nEOF",
            "cat > new.py <<'EOF'\nprint('hi'); x = (1 | 2) & 3\nln -s ~ l\nEOF",
            "cat > new.md <<EOF\nplain; text | here\nEOF",
            "cat <<-EOF > new.txt\n\tbody\n\tEOF\n",
        ):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_blocks_here_document_bodies_that_run_commands(self) -> None:
        # An unquoted body expands $(...) before the command runs.
        self.assert_blocked("cat <<EOF > /tmp/x\n$(echo x > ~/.zshrc)\nEOF")

    def test_blocks_redirects_hidden_by_hash_or_fused_punctuation(self) -> None:
        # Bash starts a comment only at a word boundary, so x#y is one word.
        for command in (
            "x#y > ~/f",
            "printf x#y >> /etc/passwd",
            "echo hi;> ~/out.txt",
            "echo hi;>>~/out.txt",
            "(echo hi)>~/out.txt",
            "rg x;>(cat)",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_allows_fused_punctuation_inside_allowed_paths(self) -> None:
        for command in ("echo hi;> out.txt", "(echo hi)>/tmp/x", "echo a;>&2"):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_blocks_commands_it_cannot_tokenize(self) -> None:
        # Bash reads #' as a comment, so the redirect still runs.
        for command in ("echo 'x > ~/f", "echo x > ~/.zshrc #'"):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_blocks_redirects_hidden_by_quotes_in_comments(self) -> None:
        # Bash ignores quotes inside comments, so an apostrophe in each of two
        # comments must not join the lines between them into one string.
        (self.workspace / ".zshrc").write_text("")
        for command in (
            "echo a # don't\necho x > ~/.zshrc # can't\n",
            "echo a # don't\ncd ~\necho x > .zshrc # can't",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_blocks_redirects_hidden_by_here_document_operators_in_quotes(
        self,
    ) -> None:
        # A << on a line that begins inside a quote opened earlier is part of
        # the string, so the lines after it are commands.
        for command in (
            'echo "\n<<EOF\n"\necho x > ~/.zshrc\necho "\nEOF\n"',
            "echo '\ncat <<EOF\n'\necho x > ~/.zshrc\necho '\nEOF\n'",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)


    def test_blocks_ansi_c_quoting_with_redirects(self) -> None:
        # Bash reads \' inside $'...' as an escaped quote and shlex does not,
        # so a $'...' command with > or << is blocked whatever its target.
        for command in (
            "echo $'\\'\n<<EOF\n'\necho x > ~/.zshrc\nEOF",
            "echo $'a\\'b' > /tmp/x",
            "echo $'\\'' > ~/.zshrc",
            "cat $'a' <<EOF\nx\nEOF",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_allows_ansi_c_quoting_without_redirects(self) -> None:
        self.assert_silent("printf $'a\\\\n'")


    def test_blocks_redirects_inside_quoted_expansions(self) -> None:
        # Bash parses $(...), ${...}, and backticks inside double quotes as
        # nested code with quotes and redirects of their own.
        for command in (
            'echo "$(echo x > ~/.zshrc)"',
            'echo "`echo x > ~/.zshrc`"',
            'echo "$(echo " a " > ~/.zshrc)"',
            'echo "${x:-"\'"}" > ~/.zshrc "${x:-"\'"}"',
            'echo "$(echo " <<EOF ")"\necho x > ~/.zshrc\nEOF',
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_allows_quoted_expansions_with_allowed_redirects(self) -> None:
        for command in (
            'echo "$(date)" > out.txt',
            'echo "${HOME}" > out.txt',
            "git commit -m \"$(cat <<'EOF'\nfix: it's\nEOF\n)\"",
        ):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_allows_redirect_characters_in_literal_message_bodies(self) -> None:
        # A quoted here-document delimiter makes the body literal data.
        for delimiter in ("'EOF'", '"EOF"'):
            for body in (
                "feat: a -> b",
                "x => y",
                "requires foo >= 1.2",
                "> quote",
                'say "hi" > it\'s $(not run)',
            ):
                for prefix in ("git commit -m", "gh pr create --body"):
                    command = f'{prefix} "$(cat <<{delimiter}\n{body}\nEOF\n)"'
                    with self.subTest(command=command):
                        self.assert_silent(command)
        self.assert_silent(
            'gh pr create --title "t" --body "$(cat <<\'A\'\n> a\nA\n)"'
            " --label \"$(cat <<'B'\nb -> c\nB\n)\""
        )

    def test_blocks_redirects_around_literal_message_bodies(self) -> None:
        for command in (
            # Bash expands an unquoted delimiter's body.
            'git commit -m "$(cat <<EOF\n$(echo x > ~/.zshrc)\nEOF\n)"',
            'git commit -m "$(cat <<EOF\na -> b\nEOF\n)"',
            # The body ends at the first delimiter line.
            "git commit -m \"$(cat <<'EOF'\nx\nEOF\necho x > ~/.zshrc\nEOF\n)\"",
            # Text after the span is still checked.
            "git commit -m \"$(cat <<'EOF'\nx\nEOF\n)\" > ~/.zshrc",
            'echo "$(cat <<\'EOF\'\nx\nEOF\n)" "$(echo x > ~/.zshrc)"',
            # The span starts inside a comment, a string, or misplaced quotes.
            "echo # \"$(cat <<'EOF'\necho x > ~/.zshrc\nEOF\n)\"",
            "echo ' \"$(cat <<'EOF'\n' > ~/.zshrc\nEOF\n)\"",
            'echo "$(echo " "$(cat <<\'EOF\'\n")" > ~/.zshrc\nEOF\n)"',
            "echo $'\\'' \"$(cat <<'EOF'\n> ~/.zshrc\nEOF\n)\"",
            "cat <<E\n\"$(cat <<'EOF'\nE\necho x > ~/.zshrc\nEOF\n)\"",
            # Inside $(...), bash 5 ends the body at a line starting "EOF)".
            'echo "$(cat <<\'EOF\'\nEOF)" > ~/.zshrc\nx\nEOF\n)"',
            'echo "$(cat <<\'EOF\'\nEOF)"; echo x > ~/.zshrc; : "\nEOF\n)"',
            # Any body line that starts with the delimiter is not trusted.
            "echo \"$(cat <<'EOF'\nEOF \necho x > ~/.zshrc\nEOF\n)\"",
            "echo \"$(cat <<'EOF'\n\tEOF\necho x > ~/.zshrc\nEOF\n)\"",
            "echo \"$(cat <<'EOF'\nEOFX > ~/.zshrc\nEOF\n)\"",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_ignores_bash_3_body_lines_that_close_the_substitution(self) -> None:
        # Bash 3.2 ends $(...) at a body line starting `)"`; Kiro runs commands
        # with zsh and bash 5, which read the line as body text, so it passes.
        self.assert_silent('echo "$(cat <<\'EOF\'\n)" > ~/.zshrc\nEOF\n)"')


    def test_allows_comments_around_allowed_redirects(self) -> None:
        for command in (
            "echo hi > out.txt # note",
            "# note\necho hi > out.txt",
            "echo a # it's\necho b > out.txt # isn't",
        ):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_blocks_relative_redirect_after_cd(self) -> None:
        # The workspace has its own .zshrc, so only the directory change matters.
        (self.workspace / ".zshrc").write_text("")
        for command in (
            "cd /tmp && echo x > rel",
            "cd ~ && echo x > .zshrc",
            "pushd ~; echo x > .zshrc",
            "popd && echo x > .zshrc",
            "cd ~\necho x > .zshrc",
            # A misread here-document operator must not hide a directory
            # change, so a cd counts even inside a body.
            "cat <<'EOF' > out.txt\ncd ~\nEOF",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_blocks_lines_after_arithmetic_shifts(self) -> None:
        # << inside $((...)) or ((...)) shifts bits and starts no here-document,
        # so the lines after it are commands.
        (self.workspace / ".zshrc").write_text("")
        for command in (
            "echo $((1<<mount))\ncd ~\necho x > .zshrc\nmount",
            "echo $(( (1) << mount ))\ncd ~\necho x > .zshrc\nmount",
            "((a<<b))\necho x > ~/.zshrc\nb",
            "echo $((1\n<<x))\necho x > ~/.zshrc\nx",
        ):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_allows_arithmetic_shifts_with_allowed_redirects(self) -> None:
        for command in (
            "echo $((1<<2)) > out.txt",
            "((x = 1 << 2)); echo $x > out.txt",
        ):
            with self.subTest(command=command):
                self.assert_silent(command)

    def test_blocks_symlinks_out_of_allowed_paths(self) -> None:
        tmp_dir = pathlib.Path(tempfile.mkdtemp(dir="/tmp"))
        self.addCleanup(shutil.rmtree, tmp_dir)
        (tmp_dir / "zshrc").symlink_to(self.home / ".zshrc")
        (self.workspace / "link").symlink_to(self.home)
        for command in (f"git log > {tmp_dir}/zshrc", "echo hi > link/out.txt"):
            with self.subTest(command=command):
                self.assert_blocked(command)

    def test_tool_cwd_does_not_widen_allowed_paths(self) -> None:
        for command, tool_cwd in (
            ("echo hi > /etc/hosts", "/"),
            ("echo hi > etc/hosts", "/"),
            ("echo hi > out.txt", str(self.home)),
        ):
            with self.subTest(command=command, tool_cwd=tool_cwd):
                self.assert_blocked(command, tool_cwd)

    def test_tool_cwd_resolves_relative_targets(self) -> None:
        (self.workspace / "sub").mkdir()
        self.assert_silent("echo hi > out.txt", str(self.workspace / "sub"))
        self.assert_silent("echo hi > out.txt", "sub")
        self.assert_silent("echo hi > ../out.txt", "sub")
        self.assert_blocked("echo hi > ../../out.txt", "sub")




    def test_runs_under_the_macos_system_python(self) -> None:
        if not SYSTEM_PYTHON.exists():
            self.skipTest("needs the macOS system Python")
        (self.home / ".aws").mkdir()
        (self.home / ".aws" / "config").write_text("")
        for command, code, asks in (
            ("echo x >! ~/.zshrc", 2, False),
            ("git log > out.txt", 0, False),
            ("cat ~/.{a,}ws/config", 0, False),
        ):
            payload = kiro_payload(command)
            payload["cwd"] = str(self.workspace)
            with self.subTest(command=command):
                result = subprocess.run(
                    [str(SYSTEM_PYTHON), str(REDIRECT_GUARD_KIRO)],
                    input=json.dumps(payload),
                    capture_output=True,
                    text=True,
                    env=dict(os.environ, HOME=str(self.home)),
                    check=False,
                )
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertEqual('"ask"' in result.stdout, asks, result.stdout)





    def test_blocks_payloads_it_cannot_read(self) -> None:
        for stdin in (
            "not json",
            "[]",
            json.dumps({"cwd": "/tmp", "tool_input": "git log > ~/.zshrc"}),
            json.dumps({"cwd": "/tmp", "tool_input": {"command": ["git", "log"]}}),
            json.dumps({"cwd": 1, "tool_input": {"command": "git log"}}),
        ):
            with self.subTest(stdin=stdin):
                result = self.run_raw(stdin)
                self.assertEqual(result.returncode, 2)
                self.assertIn("cannot read the hook input", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_blocks_redirect_with_secret_path(self) -> None:
        self.assert_blocked("cat ~/.ssh/id_rsa > ~/.zshrc")

    def test_ignores_secret_paths(self) -> None:
        (self.home / ".aws").mkdir()
        (self.home / ".aws" / "config").write_text("")
        (self.workspace / "link").symlink_to(self.home / ".aws")
        for command in (
            "cat ~/.aws/config",
            "cat $HOME/.a?s/config",
            "cat ~/.{a,}ws/config",
            "cat < ~/.ssh/id_ed25519",
            "cat link/config",
            "cat dot_config/mcporter/private_mcporter.json.tmpl",
        ):
            with self.subTest(command=command):
                self.assert_silent(command)




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
        python: str = "python3",
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
            [python, str(self.script), event_name],
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

    def test_arm_drops_the_first_question(self) -> None:
        # Resuming must not ask the launch question again, least of all with
        # --trust-all-tools.
        out = self.run_hook(
            "session-start",
            args="chat --trust-all-tools --model m --effort=high 'fix the tests'",
        )
        self.assertEqual(
            shlex.split(arm_args(out)),
            [
                "chat",
                "--trust-all-tools",
                "--model",
                "m",
                "--effort=high",
                "--resume-id",
                "sess_test",
            ],
        )

    def test_does_not_arm_non_interactive_runs(self) -> None:
        out = self.run_hook("session-start", args="chat --no-interactive 'run it'")
        self.assertEqual(out, b"")

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

    @unittest.skipUnless(SYSTEM_PYTHON.exists(), "needs the macOS system Python")
    def test_runs_on_the_system_python(self) -> None:
        # Kiro's hook environment can resolve python3 to /usr/bin/python3.
        self.write_session(say("日本語の回答"))
        for event_name, osc in (("session-start", "88"), ("stop", "777")):
            with self.subTest(event_name=event_name):
                self.tty.write_bytes(b"")
                result = self.run_process(event_name, python=str(SYSTEM_PYTHON))
                self.assertEqual((result.returncode, result.stderr), (0, ""))
                self.assertEqual(osc_fields(self.tty.read_bytes())[0], osc)

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
        command = ["zsh", "-fc", code, "zsh", *args]
        if sys.platform == "darwin":
            script = ["script", "-q", "/dev/null", *command]
        else:
            # util-linux script(1) runs one command string through $SHELL,
            # whose startup files could put the real kiro-cli back on PATH.
            env["SHELL"] = "/bin/sh"
            script = ["script", "-q", "-c", shlex.join(command), "/dev/null"]
        result = subprocess.run(
            script,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            env=env,
            check=True,
        )
        return result.stdout.replace(b"\r", b"")

    def test_wrapper_passes_tty_and_quoted_arguments(self) -> None:
        out = self.run_wrapper("chat", "--agent", "my agent")
        self.assertRegex(out, rb"KIRO_OTTY_TTY=/dev/(ttys|pts/)\d+\n")
        self.assertIn(b"KIRO_OTTY_ARGS=chat --agent 'my agent'\n", out)

    def test_wrapper_clears_and_keeps_exit_status(self) -> None:
        out = self.run_wrapper("chat", fake_status=3)
        self.assertIn(b"\x1b]88;clear\x07", out)
        self.assertIn(b"status=3\n", out)

    def test_wrapper_treats_no_arguments_as_chat(self) -> None:
        out = self.run_wrapper()
        self.assertRegex(out, rb"KIRO_OTTY_TTY=/dev/(ttys|pts/)\d+\n")
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
