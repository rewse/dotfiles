# Kiro の秘密パス確認廃止 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 秘密パスを理由にした Kiro の承認プロンプトを、permissions.yaml の ask ルールと redirect-guard hook の両方から取り除く。

**Architecture:** permissions.yaml.tmpl から shell の `ask` ルールを消し、`executable_redirect-guard-kiro.py` から秘密パス検査を消してリダイレクト検査だけを残す。テスト、`AGENTS.md`、共通ルールの記述を合わせて直し、この Mac に `chezmoi apply` する。

**Tech Stack:** Python 3（macOS システム Python 3.9 でも動くこと）、unittest、chezmoi テンプレート、Kiro CLI v3 permissions

**Spec:** `docs/superpowers/specs/2026-11-26-drop-kiro-secret-path-ask-design.md`

## Global Constraints

- hook のリダイレクト先検査（exit 2 でブロック）と `quoting_hazard` の検査は挙動を変えない。
- hook は `from __future__ import annotations` を保ち、macOS システム Python で動く。
- `main` エージェントのプリセットは `read-workspace` のまま変えない。
- コメントは英語で、現在のコードについて書く（以前の挙動は commit メッセージへ）。
- commit は Conventional Commits。`dot_*`/`private_dot_*` に `docs:` は使わず、`AGENTS.md` と `docs/` には `docs:` を使う。
- push する前に `uvx pre-commit run --all-files` と `uv run python -m unittest discover -s tests` を通す。push 自体は持ち主に確認してから行う。

## Review Focus

- 秘密パスとリダイレクトが両方あるコマンド（`cat ~/.ssh/id_rsa > ~/.zshrc`）は、これまでどおりブロックされる。Task 2 の `test_blocks_redirect_with_secret_path` で固定する。
- 秘密パスを含むだけのコマンド（`~/.aws/config`、グロブ、`$HOME`、ブレース、`<` 入力、シンボリックリンク、chezmoi ソースの mcporter テンプレート）は、hook が何も出力せず exit 0 になる。Task 2 の `test_ignores_secret_paths` で固定する。
- 削除後もリダイレクト検査が使う関数（`command_words`、`ROUGH_WORD`、`may_misplace_quotes`、`command_tokens`）が残っている。Task 2 Step 5 で既存のリダイレクト系テストがすべて通ることで確かめる。
- システム Python で import 時に落ちない。Task 2 で `test_runs_under_the_macos_system_python` を更新して確かめる。
- 共通ルールから「asks before reading credential stores」を消しても、`KIRO_HOME` を分ける理由が文として成り立つ。Task 3 Step 2 の置換後の文で確かめる。

---

### Task 1: permissions.yaml の ask ルールを削除する

**Files:**
- Modify: `private_dot_kiro/private_settings/private_permissions.yaml.tmpl:5-53`
- Modify: `tests/test_kiro_permissions.py`
- Modify: `tests/test_kiro_agent.py:54-63`

**Interfaces:**
- Consumes: なし
- Produces: `tests/test_kiro_permissions.py` が hook の `SECRET_PATTERNS` を読まなくなる。これで Task 2 が `SECRET_PATTERNS` を削除できる。

- [ ] **Step 0: spec と plan を Commit する**

```bash
git add docs/superpowers/specs/2026-11-26-drop-kiro-secret-path-ask-design.md docs/superpowers/plans/2026-11-26-drop-kiro-secret-path-ask.md
git commit -m "docs: plan removing the Kiro secret path ask"
```

- [ ] **Step 1: テストを書き換える**

`tests/test_kiro_permissions.py` から、`secret_patterns()`、`REDIRECT_GUARD_KIRO`、未使用になる `fnmatch` と `importlib.util` の import、`test_shell_has_only_the_secret_ask_rule`、`test_secret_patterns_cover_new_credential_stores`、`test_secret_patterns_are_sorted`、`test_secret_patterns_match_template_list`、`test_secret_locations_have_a_standalone_ask_rule` を削除する。`test_remaining_capabilities` の期待値から `("shell", "ask")` を外し、次を追加する。

```python
    def test_shell_has_no_rule(self) -> None:
        # approve-for-me judges every shell command.
        for rendered in (self.rendered, self.business):
            caps = {r["capability"] for r in rendered["rules"]}
            self.assertNotIn("shell", caps)
```

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run python -m unittest tests.test_kiro_permissions -v`
Expected: `test_shell_has_no_rule` と `test_remaining_capabilities` が FAIL（shell の ask ルールがまだある）

- [ ] **Step 3: テンプレートから shell の ask ルールを削除する**

`private_permissions.yaml.tmpl` の、`# Locations that may hold credentials.` のコメントから `- "*zsh/history*"` までを削除する。先頭の approve-for-me のコメントと、fs_read 以降のルールは残す。

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_permissions -v`
Expected: すべて PASS

- [ ] **Step 5: エージェントテストのコメントを書き直す**

`tests/test_kiro_agent.py` の `test_default_agent_uses_read_workspace_preset` のコメントを、ask ルールに頼らない理由に書き換える。内容は次の 3 点: read-workspace はワークスペースの読み取りを黙って許すだけで、シェルコマンドは approve-for-me の判定に残す。read-only-shell は読み取り専用コマンドをすべて自動で許してしまう。policies が空だと kiro-cli 3 は "Mode not found" で失敗する。アサーションは変えない。

- [ ] **Step 6: 通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_agent -v`
Expected: すべて PASS

- [ ] **Step 7: Commit**

```bash
git add private_dot_kiro/private_settings/private_permissions.yaml.tmpl tests/test_kiro_permissions.py tests/test_kiro_agent.py
git commit -m "feat(kiro): drop the shell ask rule for credential paths" -m "The prompt shows only that a path may hold credentials, not the command or why it runs, so approvers allowed it every time. approve-for-me now judges these commands."
```

### Task 2: hook の秘密パス検査を削除する

**Files:**
- Modify: `dot_agents/hooks/executable_redirect-guard-kiro.py`
- Modify: `tests/test_kiro_hooks.py:163-628`

**Interfaces:**
- Consumes: Task 1 の後、`tests/test_kiro_permissions.py` が `SECRET_PATTERNS` を使っていないこと。
- Produces: hook の出力は、exit 0 で何も出さないか、exit 2 で stderr に理由を出すかのどちらかになる。`permissionDecision` は出さない。

- [ ] **Step 1: テストを書き換える**

`tests/test_kiro_hooks.py` の `RedirectGuardKiroTest` から、`assert_asks` と次のテストを削除する: `test_asks_for_secret_paths_hidden_by_here_document_operators_in_quotes`、`test_asks_for_secret_paths_hidden_by_ansi_c_quoting`、`test_asks_for_secret_paths_hidden_by_quoted_expansions`、`test_asks_for_glob_that_expands_to_a_secret_path`、`test_asks_for_home_variables_and_braces_that_reach_a_secret_path`、`test_allows_braces_and_home_variables_without_secret_paths`、`test_asks_for_input_from_a_secret_path`、`test_asks_for_symlink_to_a_secret_path`、`test_asks_for_relative_paths_that_leave_a_secret_cwd`、`test_allows_relative_words_under_a_secret_looking_cwd`、`test_allows_commands_without_secret_paths`。`test_blocks_before_asking` は中身を変えずに `test_blocks_redirect_with_secret_path` へ改名する。次を追加する。

```python
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
```

`test_runs_under_the_macos_system_python` の 3 番目のケースを `("cat ~/.{a,}ws/config", 0, False)` に変える。

- [ ] **Step 2: 失敗を確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks.RedirectGuardKiroTest -v`
Expected: `test_ignores_secret_paths` と `test_runs_under_the_macos_system_python` が FAIL（stdout に ask の JSON が出る）。後者はシステム Python がなければ skip になる。

- [ ] **Step 3: hook から秘密パス検査を削除する**

`main()` の `secrets = secret_paths(...)` 以降の ask 出力を削除し、`return 0` だけを残す。秘密パス検査だけが使う `SECRET_PATTERNS`、`HOME_VARIABLE`、`BRACE_LIST`、`MAX_BRACE_WORDS`、`is_secret`、`below`、`brace_alternatives`、`input_paths`、`secret_paths`、`reaches_secret`、`import fnmatch`、`import glob` を削除する。`ROUGH_WORD`、`command_words`、`may_misplace_quotes`、`command_tokens` はリダイレクト検査が使うので残す。

docstring の 1 行目を `"""Kiro CLI PreToolUse hook that blocks shell redirects outside allowed paths.` にし、「Secret paths」の段落、「and the secret path check adds rough words」、「A blocked redirect takes precedence over the ask.」を削る。`main()` のコメント「the secret path check still reads them」も削る。

- [ ] **Step 4: 消し残しがないことを確かめる**

Run: `rg -n -i "secret|fnmatch|glob\.|brace|HOME_VARIABLE" dot_agents/hooks/executable_redirect-guard-kiro.py`
Expected: 出力なし（exit 1）

- [ ] **Step 5: 通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks -v`
Expected: すべて PASS

- [ ] **Step 6: Commit**

```bash
git add dot_agents/hooks/executable_redirect-guard-kiro.py tests/test_kiro_hooks.py
git commit -m "feat(kiro): stop asking for expanded credential paths in the redirect guard" -m "The ask prompt gave approvers no command or purpose to judge, so it was always allowed. The hook now only blocks redirects outside the allowed paths."
```

### Task 3: ドキュメントを直し、配備して仕上げる

**Files:**
- Modify: `AGENTS.md:41`
- Modify: `.chezmoitemplates/rules/common-standards.md:116`
- Move: `docs/superpowers/specs/2026-11-26-drop-kiro-secret-path-ask-design.md` → `docs/superpowers/archive/specs/`
- Move: `docs/superpowers/plans/2026-11-26-drop-kiro-secret-path-ask.md` → `docs/superpowers/archive/plans/`

**Interfaces:**
- Consumes: Task 1 と Task 2 の変更
- Produces: なし

- [ ] **Step 1: AGENTS.md を直す**

41 行目の「The hook checks only redirect targets, which Kiro strips before matching rules, and paths that reach a credential location once the shell expands them, which the text-matching `ask` rule cannot see.」を「The hook checks only redirect targets, which Kiro strips before matching rules.」にする。

- [ ] **Step 2: 共通ルールを直す**

116 行目の「which lets approve-for-me judge commands and asks before reading credential stores, along with its MCP servers and hooks」を「which lets approve-for-me judge commands, along with its MCP servers and hooks」にする。

- [ ] **Step 3: 全体の検証を走らせる**

Run: `uvx pre-commit run --all-files && uv run python -m unittest discover -s tests`
Expected: pre-commit の hook がすべて Passed、unittest が OK。整形で変わったファイルがあれば次の commit に含める。

- [ ] **Step 4: ドキュメントを Commit する**

```bash
git add AGENTS.md
git commit -m "docs: describe the Kiro redirect guard as checking only redirects"
git add .chezmoitemplates/rules/common-standards.md
git commit -m "fix(rules): stop claiming Kiro permissions ask before credential reads"
```

- [ ] **Step 5: この Mac に配備する**

Run: `chezmoi --no-pager apply ~/.kiro/settings/permissions.yaml ~/.agents/hooks/redirect-guard-kiro.py ~/.agents/rules/common-standards.md && rg -c "zsh/history|credential stores" ~/.kiro/settings/permissions.yaml ~/.agents/hooks/redirect-guard-kiro.py ~/.agents/rules/common-standards.md`
Expected: apply が成功し、rg は一致なし（exit 1）

- [ ] **Step 6: spec と plan をアーカイブして Commit する**

```bash
git mv docs/superpowers/specs/2026-11-26-drop-kiro-secret-path-ask-design.md docs/superpowers/archive/specs/
git mv docs/superpowers/plans/2026-11-26-drop-kiro-secret-path-ask.md docs/superpowers/archive/plans/
git commit -m "docs: archive the Kiro secret path ask removal spec and plan"
```

- [ ] **Step 7: push の確認を持ち主に求める**

`main` への push は、持ち主の確認を得てから行う。
