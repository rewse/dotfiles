# Kiro CLI の Otty 完了通知と resume 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kiro CLI のターン終了時に返答の冒頭を載せた通知を Otty に出し、Otty の再起動後に同じ会話へ同じ起動オプションで戻れるようにする。

**Architecture:** バッジと承認待ちの通知は Kiro 本体の OSC 7501 に任せ、`otty-state` の hook と Otty の「Notify on Command Finish」をやめる。zsh のラッパー関数 `kiro-cli` がペインの tty と起動引数を環境変数で渡し、Python の hook が `SessionStart` で OSC 88 `arm`、`Stop` で OSC 777 の通知をその tty に書く。ラッパーは Kiro の終了後に OSC 88 `clear` を書く。

**Tech Stack:** Python 3 標準ライブラリ、zsh、chezmoi テンプレート、`unittest`、Kiro CLI v3 hooks、Otty 1.6.2

**Spec:** `docs/superpowers/specs/2026-10-24-kiro-otty-notify-resume-design.md`

## Global Constraints

- 配布は macOS だけ。Linux では `.chezmoiignore` で新しいファイルを外す。
- 環境変数は `KIRO_OTTY_TTY`（ペインの tty のパス）と `KIRO_OTTY_ARGS`（`kiro-cli` に渡した引数をシェルの書き方で引用し、空白でつないだ文字列）。
- 通知のタイトルは `Kiro — <cwd の末尾のディレクトリ名>`、本文は返答の冒頭100字。100字を超えたら99字に `…` を足す。
- `japanese-guard.py` の `is_english` が真の返答は通知しない。
- hook は stdout に何も出さず、どの失敗でも終了コード 0 で抜ける。tty への書き込みは1回の `os.write` で行う。
- OSC 88 の `cmd` は `kiro-cli`。値はすべて base64（UTF-8）。
- `~/.kiro/settings/cli.json` は `chezmoi apply` しない。実ファイルに利用者が足したモデル設定があり、適用すると消える。適用は対象を指定して行う。
- コミットメッセージは Conventional Commits。`dot_*` と `private_dot_*` に `docs:` は使わない。

## Review Focus

- 引数に空白や引用符を含む起動（`kiro-cli chat --agent 'my agent'`）。resume の `args` で同じ引数に戻ること。Task 2 のテスト `test_arm_keeps_quoted_arguments` で確かめる。
- 返答に `;`、ESC、BEL などの制御文字が入る場合（ANSI 色付きの出力を引用した返答など）。OSC 777 の区切りが壊れないこと。Task 2 のテスト `test_notification_strips_separators_and_controls` で確かめる。
- `KIRO_OTTY_TTY` が存在しないパスや書けないパスを指す場合。何も出さず終了コード 0 で終わること。Task 2 のテスト `test_unwritable_tty_is_ignored` で確かめる。
- `session_id` がない、または `/` を含む場合。何も書かないこと。Task 2 のテスト `test_rejects_bad_session_id` で確かめる。
- Kiro が 0 以外の終了コードで終わった場合。ラッパーは同じ終了コードを返し、`clear` も書くこと。Task 3 のテスト `test_wrapper_clears_and_keeps_exit_status` で確かめる。

---

### Task 1: バッジを Kiro 本体に任せ、Kiro の「Finished」通知を止める

**Files:**
- Delete: `private_dot_kiro/hooks/otty-state.json.tmpl`
- Delete: `private_dot_kiro/hooks/executable_otty-state.sh`
- Modify: `.chezmoiignore`（Linux ブロックの `.kiro/hooks/otty-state.json` と `.kiro/hooks/otty-state.sh` の2行を消す）
- Modify: `.chezmoiremove`（2つの旧パスを理由のコメントつきで足す）
- Modify: `dot_config/otty/config.toml`（`chezmoi add` で取り込む）
- Test: `tests/test_kiro_hooks.py`（`OTTY_STATE`、`test_otty_state`、`OttyStateTest` を消し、`ChezmoiIgnoreTest` を直す）

**Interfaces:**
- Consumes: なし
- Produces: `ChezmoiIgnoreTest.test_linux_ignores_only_otty_hooks`。Task 2 がここに新しいパスの `assertIn` を足す。

- [ ] **Step 1: テストを直す**

`ChezmoiIgnoreTest.test_linux_ignores_only_otty_hooks` の2つの `assertIn` を、旧パスがないことの確認に変える。

```python
self.assertNotIn(".kiro/hooks/otty-state.json", linux)
self.assertNotIn(".kiro/hooks/otty-state.sh", linux)
self.assertNotIn(".kiro/hooks", linux)
```

あわせて `.chezmoiremove` のテストを `ChezmoiIgnoreTest` に足す。

```python
def test_removes_otty_state_hooks(self) -> None:
    lines = (REPO_ROOT / ".chezmoiremove").read_text().splitlines()
    self.assertIn(".kiro/hooks/otty-state.json", lines)
    self.assertIn(".kiro/hooks/otty-state.sh", lines)
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks.ChezmoiIgnoreTest -v`
Expected: 2件とも FAIL

- [ ] **Step 3: `otty-state` の hook を消し、`.chezmoiignore` の2行を消して、`.chezmoiremove` に足す**

`.chezmoiremove` には、Kiro が OSC 7501 でバッジを出すようになり、`otty tab badge` のバッジがそれを隠すという理由を1行のコメントで書く。`.chezmoiignore` の Linux ブロックへの新しいパスの追加は Task 2 で行う。

- [ ] **Step 4: Otty の設定を変えて取り込む**

Run: `otty config unset privilege-notification-on-finish && otty config reload && chezmoi add ~/.config/otty/config.toml && git -P diff dot_config/otty/config.toml`
Expected: 差分は `privilege-notification-on-finish = true` の1行の削除だけ。

- [ ] **Step 5: テストが通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks -v`
Expected: すべて PASS

- [ ] **Step 6: 2つに分けてコミットする**

```bash
git add .chezmoiignore .chezmoiremove tests/test_kiro_hooks.py private_dot_kiro/hooks/otty-state.json.tmpl private_dot_kiro/hooks/executable_otty-state.sh
git commit -m "fix(kiro): let Kiro's program status drive the Otty tab badges"
git add dot_config/otty/config.toml
git commit -m "feat(otty): stop notifying when a command finishes"
```

### Task 2: 通知と resume の登録を行う hook

**Files:**
- Create: `dot_agents/hooks/executable_otty-kiro.py`
- Create: `private_dot_kiro/hooks/otty-kiro.json.tmpl`
- Modify: `.chezmoiignore`（Linux ブロックに `.agents/hooks/otty-kiro.py` と `.kiro/hooks/otty-kiro.json` を足す）
- Test: `tests/test_kiro_hooks.py`

**Interfaces:**
- Consumes: 同じディレクトリの `japanese-guard-kiro.py` の `final_answer(session: str, cwd: str | None) -> str` と `load_guard()`（戻り値の `is_english(text: str) -> bool` を使う）。どちらも `importlib` でファイルから読み込む。
- Produces: `~/.agents/hooks/otty-kiro.py session-start` と `~/.agents/hooks/otty-kiro.py stop`。stdin は Kiro の hook の JSON（`session_id`、`cwd`）。環境変数は `KIRO_OTTY_TTY` と `KIRO_OTTY_ARGS`。Task 3 のラッパーがこの2つを設定する。

- [ ] **Step 1: 失敗するテストを書く**

`ChezmoiIgnoreTest.test_linux_ignores_only_otty_hooks` に `self.assertIn(".agents/hooks/otty-kiro.py", linux)` と `self.assertIn(".kiro/hooks/otty-kiro.json", linux)` を足す。

`JapaneseGuardKiroTest` と同じく、一時ディレクトリの `hooks/` に `japanese-guard-kiro.py`、`otty-kiro.py`、`GUARD_STUB` の `japanese-guard.py` を置く。`HOME` を一時ディレクトリにして、`messages.jsonl` は `event()` と `say()` で作る。`KIRO_OTTY_TTY` には一時ファイルのパスを渡し、書き込まれたバイト列を読む。cwd は `/tmp/project`。OSC を解くヘルパー `osc_fields(data: bytes) -> list[str]`（`ESC ]` から `BEL` までを `;` で分ける）をテスト側に置く。`OttyKiroTest` に次のテストを書く。

```python
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
    values = dict(f.split("=", 1) for f in fields[2:])
    self.assertEqual(b64(values["cmd"]), "kiro-cli")
    self.assertEqual(b64(values["args"]), "chat --trust-all-tools --resume-id sess_test")
    self.assertEqual(b64(values["cwd"]), "/tmp/project")

def test_arm_drops_every_resume_flag(self) -> None:
    out = self.run_hook(
        "session-start", args="chat -r --resume-picker --resume-id old --resume-id=old2"
    )
    self.assertEqual(arm_args(out), "chat --resume-id sess_test")

def test_arm_adds_chat_when_launched_without_arguments(self) -> None:
    self.assertEqual(arm_args(self.run_hook("session-start", args="")), "chat --resume-id sess_test")

def test_arm_keeps_quoted_arguments(self) -> None:
    out = self.run_hook("session-start", args="chat --agent 'my agent'")
    self.assertEqual(shlex.split(arm_args(out)), ["chat", "--agent", "my agent", "--resume-id", "sess_test"])

def test_stop_notifies_with_project_and_answer(self) -> None:
    self.write_session(event({"type": "user", "content": "q"}), say("## 結果\n\n**直した**よ。`a.py` を見てね"))
    self.assertEqual(osc_fields(self.run_hook("stop")), ["777", "notify", "Kiro — project", "結果 直したよ。a.py を見てね"])

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
    result = self.run_process("stop", tty=None)
    self.assertEqual((result.returncode, result.stdout), (0, ""))

def test_unwritable_tty_is_ignored(self) -> None:
    result = self.run_process("stop", tty=str(self.tmp / "missing/tty"))
    self.assertEqual((result.returncode, result.stdout, result.stderr), (0, "", ""))

def test_rejects_bad_session_id(self) -> None:
    for session_id in ("", "../x"):
        with self.subTest(session_id=session_id):
            self.assertEqual(self.run_hook("session-start", session_id=session_id), b"")
```

`run_hook(event, *, args="chat", session_id=SESSION_ID) -> bytes` は `run_process` を呼んで tty ファイルの中身を返す。`run_process(event, *, tty=<一時ファイル>, args="chat", session_id=SESSION_ID) -> subprocess.CompletedProcess[str]` は `python3 otty-kiro.py <event>` を実行する。テスト自体がラッパー経由の Kiro から動くこともあるので、環境変数は `os.environ` から `KIRO_OTTY_TTY` と `KIRO_OTTY_ARGS` を除いてから、渡す値だけを設定する。`b64(value: str) -> str` は base64 を解き、`arm_args(data: bytes) -> str` は `args` を解いて返す。`;` は `,` に置き換わる前提で、`test_notification_strips_separators_and_controls` は区切りの数と制御文字がないことだけを見る。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks.OttyKiroTest tests.test_kiro_hooks.ChezmoiIgnoreTest -v`
Expected: hook のファイルがないので FAIL

- [ ] **Step 3: `dot_agents/hooks/executable_otty-kiro.py` を書く**

関数は次のとおり。docstring には、Kiro の hook は制御端末を持たないのでラッパーが渡す tty のパスに書くこと、Kiro 本体の `done` は msg を置き換えさせないので通知は OSC 777 で出すことを書く。

- `resume_args(raw: str, session_id: str) -> str`: `shlex.split(raw)` から `-r`、`--resume`、`--resume-picker`、`--resume-id` とその次の値、`--resume-id=` で始まる語を除く。先頭が `chat` でなければ `chat` を前に足す。最後に `--resume-id <session_id>` を足して `shlex.join` で返す。
- `arm_sequence(args: str, cwd: str) -> bytes`: `ESC ]88;arm;cmd=<b64>;args=<b64>;cwd=<b64> BEL`。
- `notification_body(answer: str, limit: int = 100) -> str`: コードの囲みの行（` ``` ` で始まる行）を消し、行頭の `#`、`>`、`-`、`*`、`数字.` の記号、`**`、`__`、`` ` ``、`[text](url)` の `(url)` を外す。制御文字（C0、DEL、C1）を消し、`;` を `,` に置き換え、空白をまとめる。`limit` 字を超えたら `limit - 1` 字に `…` を足す。空なら `Response complete`。
- `notify_sequence(title: str, body: str) -> bytes`: `ESC ]777;notify;<title>;<body> BEL`。タイトルにも制御文字の除去と `;` の置き換えをかける。
- `write_tty(path: str, data: bytes) -> None`: `os.open(path, os.O_WRONLY | os.O_NOCTTY)` で開き、1回の `os.write` で書いて閉じる。
- `main(argv: list[str]) -> None`: `KIRO_OTTY_TTY` がなければ戻る。`session_id` が空か `/` を含めば戻る。`session-start` なら `arm_sequence(resume_args(KIRO_OTTY_ARGS, session_id), cwd)` を書く。`stop` なら `final_answer` で返答を取り、`is_english` が真なら戻り、`Kiro — <basename(cwd)>` と `notification_body` で通知を書く。
- `if __name__ == "__main__":` では `main(sys.argv)` を `try/except Exception: pass` で包む。

- [ ] **Step 4: `private_dot_kiro/hooks/otty-kiro.json.tmpl` を書き、`.chezmoiignore` の Linux ブロックに2行を足す**

形式は `agent-guards.json.tmpl` と同じ `"version": "v1"`。フックの名前は `otty-kiro-session-start` と `otty-kiro-stop`。コマンドは `{{ .chezmoi.homeDir }}/.agents/hooks/otty-kiro.py session-start` と `... stop`。`.chezmoiignore` の行はアルファベット順に入れる。

- [ ] **Step 5: テストが通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks -v`
Expected: すべて PASS

- [ ] **Step 6: コミットする**

```bash
git add dot_agents/hooks/executable_otty-kiro.py private_dot_kiro/hooks/otty-kiro.json.tmpl .chezmoiignore tests/test_kiro_hooks.py
git commit -m "feat(kiro): notify Otty with the answer and arm session resume"
```

### Task 3: `kiro-cli` のラッパー関数

**Files:**
- Modify: `dot_zshrc.tmpl`（`# <<< Terminal Integration` の中、`_notify_terminal_cwd` の後ろ）
- Test: `tests/test_kiro_hooks.py`

**Interfaces:**
- Consumes: Task 2 が読む `KIRO_OTTY_TTY` と `KIRO_OTTY_ARGS`。
- Produces: zsh 関数 `kiro-cli`。

- [ ] **Step 1: 失敗するテストを書く**

`KiroWrapperTest` を作る。`dot_zshrc.tmpl` から正規表現 `^kiro-cli\(\) \{\n.*?^\}\n`（`re.M | re.S`）で関数を取り出す。一時ディレクトリに偽の `kiro-cli` を置き、`PATH` の先頭に入れる。偽物は `KIRO_OTTY_TTY` と `KIRO_OTTY_ARGS` が設定されているときだけ `name=value` の行を出力し、`exit ${FAKE_STATUS:-0}` で終わる（設定の有無は `${VAR+x}` で見る）。tty を持たせるため、`script -q /dev/null zsh -fc '<関数>; kiro-cli "$@"; echo "status=$?"' zsh <引数>` で実行し、stdout をバイト列で受け取って `\r` を外す。`script` は stdin がソケットだと `tcgetattr` で失敗するので、`stdin=subprocess.DEVNULL` で起動する。出力の先頭には `^D` と `^H` が混ざるので、比較は `assertIn` と `assertRegex` で行う。環境変数は `os.environ` から `KIRO_OTTY_TTY` と `KIRO_OTTY_ARGS` を除いて渡す。ヘルパーは `run_wrapper(*args: str, fake_status: int = 0) -> bytes`。

```python
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
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks.KiroWrapperTest -v`
Expected: 関数が見つからないので FAIL

- [ ] **Step 3: `dot_zshrc.tmpl` に関数を書く**

第1引数が `chat` か、引数がないときだけ、`KIRO_OTTY_TTY="$TTY" KIRO_OTTY_ARGS="${(j: :)${(q-)@}}" command kiro-cli "$@"` で起動し、終了コードを取っておく。`$TTY` が空でなければ `printf '\e]88;clear\a' > "$TTY"` を書き、取っておいた終了コードで `return` する。それ以外の引数では `command kiro-cli "$@"` をそのまま返す。関数の上のコメントには、Kiro の hook が制御端末を持たないので tty のパスを渡すこと、終了時の hook がないので resume の登録をここで取り消すことを書く。

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks tests.test_zprofile_path -v`
Expected: すべて PASS

- [ ] **Step 5: コミットする**

```bash
git add dot_zshrc.tmpl tests/test_kiro_hooks.py
git commit -m "feat(zsh): pass the pane tty and launch options to Kiro hooks"
```

### Task 4: 適用と実機での確認

**Files:**
- Modify: 確認で問題が見つかったファイルだけ

**Interfaces:**
- Consumes: Task 1〜3 のすべて。
- Produces: なし。

- [ ] **Step 1: 全体の検査を通す**

Run: `uvx pre-commit run --all-files && uv run python -m unittest discover -s tests`
Expected: すべて Passed / OK。hook が整形したファイルがあればコミットする。

- [ ] **Step 2: 対象を指定して適用する**

Run: `chezmoi apply ~/.zshrc ~/.agents/hooks/otty-kiro.py ~/.kiro/hooks ~/.config/otty/config.toml && ls ~/.kiro/hooks/`
Expected: `otty-kiro.json` があり、`otty-state.json` と `otty-state.sh` がない。`~/.kiro/settings/cli.json` には触れない。

- [ ] **Step 3: 利用者に実機で確かめてもらう**

新しい Otty のペインで `ka` を起動し、次を順に確かめる。結果を聞き取って記録する。

1. 少し時間のかかる依頼を出して別のタブに切り替えると、「Kiro — <プロジェクト名>」と返答の冒頭が載った通知が1つだけ出る。「kiro-cli / Finished」は出ない。
2. 承認が必要な操作を `--trust-all-tools` なしの `k` で頼むと、タブに手のアイコンが付き、別のタブにいれば承認待ちの通知が出る。
3. `/quit` で終えたタブは、Otty を再起動しても Kiro が復活しない。
4. Kiro を動かしたまま Otty を終了して起動し直すと、同じ会話が `--trust-all-tools` 付きで戻る。戻ったあとのターンでも 1 の通知が出る（Otty がシェルを通して起動したかがここで分かる）。
5. `/load` で別の会話に切り替えてから Otty を再起動すると、切り替えた先の会話が戻る。

- [ ] **Step 4: 確認で分かったことを設計書に反映する**

4 か 5 が期待どおりでなければ、原因と取った対応を設計書の「実装するときに確かめること」に書き、修正とあわせてコミットする。期待どおりなら、その項目を確かめた事実として「制約」に移す。

```bash
git add docs/superpowers/specs/2026-10-24-kiro-otty-notify-resume-design.md
git commit -m "docs: record the verified Otty resume behavior for Kiro CLI"
```
