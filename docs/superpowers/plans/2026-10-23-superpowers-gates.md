# superpowers-gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** すべてのリポジトリで、Claude Code、Codex、Kiro CLI（V3）が計画、spec、SDD の台帳を書く前に対応する superpowers の skill を読み直すよう、ユーザー単位のフックで止め、書いたあとに念を押し、圧縮のあとに未完了の台帳を読み直させる。

**Architecture:** MeetNote の `scripts/agent-hooks/`（ブランチ `feat/agent-hooks` の 4d430a73）を `dot_agents/hooks/superpowers-gates/` に写し、push の判定と using-superpowers の差し込みを除いて全体向けに直す。決まりは共有の `core.sh`、CLI ごとの入口は `claude`、`codex`、`kiro`。登録は既存の `dot_claude/modify_settings.json.tmpl`、`dot_codex/modify_private_hooks.json.tmpl`、`private_dot_kiro/hooks/` の決まりに従う。

**Tech Stack:** bash 3.2、`/usr/bin/plutil`、`jq`（登録のテンプレートだけ）、chezmoi、Python unittest

**Spec:** `~/git/MeetNote/docs/superpowers/specs/2026-10-23-agent-hooks-design.md`（MeetNote の MR !289）。全体向けに変えた点は下の「決まっていること」に書き、こちらが優先する。

## 決まっていること

- 入れるのは、計画（`docs/superpowers/plans/*.md` → writing-plans）、spec（`docs/superpowers/specs/` の下の `*.md` → brainstorming）、新しい台帳（`.superpowers/sdd/*/progress.md` → subagent-driven-development）の判定と、書き込み後の念押しと、圧縮のあとの台帳の読み直し。判定の中身（20 行の線、3600 秒、印は 1 回で消える、台帳は `create` だけ止める）は MeetNote と同じ
- 入れないもの: push の前の `make check`（MeetNote にしか Makefile の印が無い）、using-superpowers の差し込み（`superpowers-session-start.sh` がすでに行う。Codex には upstream に合わせて差し込まない）
- 外し方: CLI の環境の `SUPERPOWERS_GATES=off`
- 書き込み先のリポジトリのルートと、セッションの作業ディレクトリのリポジトリのルートの両方に `.agents/hooks/superpowers-gates/core.sh` があるときだけ、プロジェクト自身のフックに任せ、何もせずに 0 で終わる（CLI がプロジェクトのフックを読むのは、セッションを始めたプロジェクトだけのため。別の場所で始めたセッションからの書き込みは、この全体向けの判定が止める）
- 止めたときと念押しで示す SKILL.md は、リポジトリに `.agents/skills/<name>/SKILL.md` があればそのリポジトリからの相対パス、無ければ `~/.agents/skills/<name>/SKILL.md`。読んだ印は、どこにある `<name>/SKILL.md` を読んでも付く（`~/.claude/skills/<name>` は `~/.agents/skills/<name>` へのリンク）
- 読んだ印はセッションごとに 1 か所（`${TMPDIR}` ではなく `~/.local/state/superpowers-gates/<cli>/<session>/`）に置き、どのリポジトリへの書き込みにも効かせる。セッションの作業ディレクトリと書き込み先のリポジトリが違っても、読んだ印が使える（MeetNote 版は印をリポジトリの `.git` に置くため、別のリポジトリへの書き込みが読んでも通らない）。window は印のディレクトリの下に、リポジトリのルートと相対パスを `%` でつないだ名前で置く。30 日より古いセッションのディレクトリは、入口が起動のたびに消す
- git のリポジトリの外では何もしない
- 置き場所: `dot_agents/hooks/superpowers-gates/core.sh`（source されるだけ）、`executable_claude`、`executable_codex`、`executable_kiro`。配置先は `~/.agents/hooks/superpowers-gates/`

## Global Constraints

- 外部コマンドは絶対パスで呼ぶ（`/usr/bin/plutil`、`/bin/mkdir`、`/bin/rm`、`/bin/date`、`/usr/bin/find`）。文字列の処理は bash の組み込みで書く
- フック自体が失敗したとき（JSON が読めない、リポジトリの外、`plutil` が無い、`HOME` が無い）は、何も出さずに終了コード 0 で通す。止めるのは決まりに当たったときだけ
- 出力は CLI ごとに、その CLI が読む形をひとつだけ出す
- `SUPERPOWERS_GATES=off` で、すべての入口が何もせずに 0 で終わる。止めたときのメッセージにこの変数を書かない
- メッセージは英語。パスはリポジトリからの相対パスか `~/` で始める形で書き、ホームの絶対パスを出さない
- bash は 3.2 で動く書き方にする（連想配列、`${var,,}`、`mapfile` を使わない）
- 登録のテンプレートは、すでに全部の登録があれば入力をバイト単位でそのまま返し、ほかの登録（otty、enforce-uv など）を消さない
- コミットの種類は AGENTS.md の「Commit types」に従う（`dot_*` は `feat:`/`fix:` など、`docs/` は `docs:`）
- push の前に `uvx pre-commit run --all-files` と `uv run python -m unittest discover -s tests` を通す

## Review Focus

- MeetNote のようにプロジェクトのフックを持つリポジトリ: 全体のフックは何もせず、メッセージも念押しも二重にならない（Task 1 `test_defers_to_project_hooks`）
- セッションの作業ディレクトリが別のリポジトリ: そこで skill を読んだあと、このリポジトリの計画に書ける（Task 1 `test_read_in_another_repo_unlocks_write`）
- skill を `~/.claude/skills/writing-plans/SKILL.md`（リンク）の側から読んだ: 印が付いて書き込みが通る（Task 1 `test_read_through_claude_skill_link_unlocks`）
- 登録のテンプレートを 2 回通す、ほかのフックがすでにある: 2 回目は入力と同じ、ほかの登録が残る（Task 1 `test_settings_template_is_idempotent`、Task 2 `test_codex_template_is_idempotent`）
- PATH が空のまま起動されたフック: 判定がそのまま働く（Task 1 `test_empty_path`）

---

### Task 1: 共有の判定と Claude Code

**Files:**
- Create: `dot_agents/hooks/superpowers-gates/core.sh`
- Create: `dot_agents/hooks/superpowers-gates/executable_claude`
- Modify: `dot_claude/modify_settings.json.tmpl`
- Create: `tests/test_superpowers_gates.py`

**Interfaces:**
- Consumes: MeetNote の `scripts/agent-hooks/core.sh` と `claude`（`git -C ~/git/MeetNote show 4d430a73:scripts/agent-hooks/core.sh`）
- Produces（`core.sh`。Task 2〜3 はこれだけを使う）:
  - `sg_disabled` → `SUPERPOWERS_GATES=off` なら 0
  - `sg_json_get <json> <keypath>`、`sg_json_escape <text>`、`sg_count_lines <text>`
  - `sg_repo_root <path-or-dir>` → worktree のルート、無ければ 1
  - `sg_defers <target-root> <session-cwd>` → 書き込み先のルートと、セッションの作業ディレクトリのルートの両方に `.agents/hooks/superpowers-gates/core.sh` があれば 0
  - `sg_state_dir <cli> <session-id>` → `$HOME/.local/state/superpowers-gates/<cli>/<session-id>`（作る。30 日より古い兄弟のディレクトリを消す）
  - `sg_skill_doc <repo-root> <skill>` → 示す SKILL.md のパス（`.agents/skills/<skill>/SKILL.md` か `~/.agents/skills/<skill>/SKILL.md`）
  - `sg_note_skill_read <state-dir> <text>`、`sg_skill_for_path <relpath>`、`sg_check_write <state-dir> <repo-root> <relpath> <kind> <changed-lines>`、`sg_reminder <repo-root> <relpath> <kind> <changed-lines>`、`sg_note_ledger <state-dir> <repo-root> <relpath>`、`sg_ledger_plan <repo-root> <ledger>`
  - `sg_compact_context <state-dir>` → このセッションが書いた台帳のうち未完了のものごとに 1 文、無ければ何も出さない
- 入口 `~/.agents/hooks/superpowers-gates/claude <event>`、`<event>` は `pre-tool-use`、`post-tool-use`、`session-start`

MeetNote の関数との違い: `ah_` を `sg_` にし、`ah_check_push`、`ah_is_push`、`ah_push_gate`、`record-check-pass` を持ってこない。`ah_session_context` の代わりに `sg_compact_context` を置き、using-superpowers の全文は出さない。メッセージの `.agents/skills/<skill>/SKILL.md` を `sg_skill_doc` の結果に置き換える。印の場所は上の「決まっていること」のとおりリポジトリから切り離す。各入口は `sg_disabled` のあと、書き込み先のリポジトリのルートを求めた直後に `sg_defers` を見る（Claude Code のセッションのルートは、Bash の `cd` に追従する `cwd` ではなく `${CLAUDE_PROJECT_DIR:-$cwd}`）（post-tool-use の読み取りでは `sg_defers` を見ない。読んだ印はどのリポジトリでも付ける）。

`claude session-start` は `source` が `compact` のときだけ `sg_compact_context`（印のディレクトリ。`sg_defers` は見ない）を `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"..."}}` で出し、ほかの `source` では何も出さない。

`modify_settings.json.tmpl` に足す登録（コマンドは `{{ .chezmoi.homeDir }}/.agents/hooks/superpowers-gates/claude <event>`）: `PreToolUse` の matcher `Write|Edit|MultiEdit`、`PostToolUse` の matcher `Read|Skill|Bash|Write|Edit|MultiEdit`、`SessionStart` の matcher `compact`、`UserPromptSubmit`（matcher なし。入力が `/writing-plans` などで始まるときに読んだ印を付ける）。既存の `has_hook` と「全部あれば素通し」の判定に 4 つを足す。

- [ ] **Step 1: テストを書く** — `tests/test_superpowers_gates.py`。各テストは `tempfile.TemporaryDirectory()` に偽の `HOME`（`.agents/skills/{writing-plans,brainstorming,subagent-driven-development}/SKILL.md` と、`.claude/skills/writing-plans` → `../../.agents/skills/writing-plans` のリンク）と、`git init` したリポジトリを作り、`env={"HOME": home, "PATH": "/usr/bin:/bin", "GIT_CONFIG_GLOBAL": "/dev/null"}` で入口を `subprocess.run(["bash", str(CLAUDE), event], input=json.dumps(payload), ...)` で呼ぶ。

| テスト | 入力 | 確かめること |
|---|---|---|
| `test_new_plan_is_blocked_without_read` | `Write` で `docs/superpowers/plans/x.md` | 終了 2、stderr に `Read ~/.agents/skills/writing-plans/SKILL.md before writing docs/superpowers/plans/x.md` |
| `test_repo_skill_copy_is_named` | リポジトリに `.agents/skills/writing-plans/SKILL.md` があるときの同じ `Write` | stderr に `Read .agents/skills/writing-plans/SKILL.md` |
| `test_read_unlocks_one_write` | `Read` の post で `$HOME/.agents/skills/writing-plans/SKILL.md`、`Write` を 2 回（別の計画） | 0、2 |
| `test_read_through_claude_skill_link_unlocks` | `Read` の post で `$HOME/.claude/skills/writing-plans/SKILL.md` | 次の `Write` が 0 |
| `test_read_in_another_repo_unlocks_write` | `cwd` が別のリポジトリ A の post で読み、リポジトリ B の計画を絶対パスで `Write` | 0 |
| `test_skill_tool_counts_as_read` | `Skill` の post で `superpowers:writing-plans` | 次の `Write` が 0 |
| `test_small_edit_is_allowed` | `Edit` で old 3 行、new 4 行 | 0 |
| `test_large_edit_in_window_is_allowed` | 読んで `Write`、同じファイルに 25 行の `Edit` | 0。window を 3601 秒前にすると 2 |
| `test_spec_subdirectory_is_gated` | `Write` で `docs/superpowers/specs/a/b c.md` | 2、stderr に `brainstorming/SKILL.md` |
| `test_new_ledger_needs_sdd_read` | 無い `.superpowers/sdd/p/progress.md` への `Write` | 2。SDD の SKILL.md を読んだあとは 0。ある台帳への 30 行の `Edit` は読まなくても 0 |
| `test_reminder_after_plan_write` | `Write` の post で計画 | stdout の JSON の `additionalContext` に `Self-Review checklist in ~/.agents/skills/writing-plans/SKILL.md` |
| `test_compact_names_unfinished_ledger` | 2 タスクの計画と `Task 1: complete` だけの台帳をセッションが書いたあと、`session-start` で `source: "compact"`（書いていない台帳では何も出ない） | `additionalContext` に `.superpowers/sdd/p/progress.md` と `re-read ~/.agents/skills/subagent-driven-development/SKILL.md` |
| `test_startup_prints_nothing` | 同じ台帳で `source: "startup"` | stdout が空 |
| `test_defers_to_project_hooks` | 作業ディレクトリのリポジトリに `.agents/hooks/superpowers-gates/core.sh` がある状態の、同じリポジトリの計画への `Write` と、その post | どちらも 0 で stdout と stderr が空 |
| `test_disabled_by_env` | `SUPERPOWERS_GATES=off` での計画への `Write` | 0、出力なし |
| `test_malformed_input_allows` | `{`、`{}` | 0、出力なし |
| `test_outside_git_repo_allows` | `git init` していないディレクトリの計画への `Write` | 0、出力なし |
| `test_empty_path` | `PATH` を空にした `Write`（読まずに）と、読んでからの `Write` | 2 と 0 |
| `test_old_sessions_are_pruned` | 31 日前の mtime にした別セッションのディレクトリがある状態で何かの hook を呼ぶ | そのディレクトリが消え、今のセッションのものは残る |
| `test_settings_template_registers_gates` | テンプレートの `{{ .chezmoi.homeDir }}` を `/home/u` に置き換えて `bash` で実行し、標準入力に `{}` | 出力の JSON に 3 つの登録（matcher とコマンド）がある |
| `test_settings_template_is_idempotent` | 1 回目の出力をもう一度入力、otty の登録を足した入力も | 2 回目は入力とバイト単位で同じ、otty の登録が残る |

- [ ] **Step 2: 失敗することを確かめる**

Run: `uv run python -m unittest tests.test_superpowers_gates -v`
Expected: FAIL（入口が無い）

- [ ] **Step 3: `core.sh`、`executable_claude`、テンプレートを書く**

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run python -m unittest tests.test_superpowers_gates -v`
Expected: `Ran 21 tests` と `OK`

- [ ] **Step 5: コミット**

```bash
git add dot_agents/hooks/superpowers-gates dot_claude/modify_settings.json.tmpl tests/test_superpowers_gates.py
git commit -m "feat(agents): gate plan, spec and ledger writes on reading their superpowers skill"
```

### Task 2: Codex

**Files:**
- Create: `dot_agents/hooks/superpowers-gates/executable_codex`
- Modify: `dot_codex/modify_private_hooks.json.tmpl`
- Modify: `tests/test_superpowers_gates.py`

**Interfaces:**
- Consumes: Task 1 の `core.sh` の関数。MeetNote の `scripts/agent-hooks/codex`（4d430a73。`*** Delete File:` を数えない枠として持つ直しが入った版）
- Produces: `~/.agents/hooks/superpowers-gates/codex <event>`、`<event>` は `pre-tool-use`、`post-tool-use`、`user-prompt-submit`、`post-compact`

MeetNote の `codex` との違い: push の分岐と `session-start` を持たない。`post-compact` は `sg_compact_context` を `{"hookSpecificOutput":{"hookEventName":"PostCompact","additionalContext":"..."}}` で出し、台帳が無ければ何も出さない。

`modify_private_hooks.json.tmpl` に足す登録（コマンドは `{{ .chezmoi.homeDir }}/.agents/hooks/superpowers-gates/codex <event>`）: `PreToolUse` の matcher `^apply_patch$`、`PostToolUse` の matcher `^(apply_patch|Bash)$`（Bash は skill を読んだ印のためだけ）、`UserPromptSubmit`、`PostCompact`。

- [ ] **Step 1: テストを足す**

| テスト | 確かめること |
|---|---|
| `test_codex_add_plan_is_blocked` | `*** Add File: docs/superpowers/plans/x.md` の patch → 2 |
| `test_codex_cat_skill_counts_as_read` | `Bash` の post で `cat ~/.agents/skills/writing-plans/SKILL.md` のあと同じ patch → 0 |
| `test_codex_small_update_is_allowed` | Update で `+` 3 行、`-` 2 行 → 0 |
| `test_codex_dash_prefixed_lines_count` | Update で `----` と `++x` を 11 組 → 2 |
| `test_codex_delete_does_not_hide_a_plan` | Add 計画 / Delete x / Add y → 2。Update 計画（+25）/ Delete x / Update y（+1）→ 2 |
| `test_codex_prompt_mention_counts_as_read` | `prompt: "use $writing-plans"` のあと Add → 0 |
| `test_codex_reminder_after_add` | 計画の Add の post → `additionalContext` に `Self-Review checklist` |
| `test_codex_post_compact_names_ledger` | セッションが書いた未完了の台帳で `post-compact` → `hookEventName` が `PostCompact`、台帳のパス |
| `test_codex_template_is_idempotent` | テンプレートを `{}` で実行 → 4 つの登録、`session-start` の登録は無い。出力を再入力 → 同じ。既存の `enforce-uv` と otty の登録が残る |

- [ ] **Step 2: 失敗することを確かめる**

Run: `uv run python -m unittest tests.test_superpowers_gates -v`
Expected: 新しい 9 件が FAIL

- [ ] **Step 3: `executable_codex` とテンプレートを書く**

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run python -m unittest tests.test_superpowers_gates -v`
Expected: `Ran 30 tests` と `OK`

- [ ] **Step 5: コミット**

```bash
git add dot_agents/hooks/superpowers-gates/executable_codex dot_codex/modify_private_hooks.json.tmpl tests/test_superpowers_gates.py
git commit -m "feat(agents): add the superpowers gates to Codex"
```

### Task 3: Kiro CLI（V3）

**Files:**
- Create: `dot_agents/hooks/superpowers-gates/executable_kiro`
- Create: `private_dot_kiro/hooks/superpowers-gates.json.tmpl`
- Modify: `tests/test_superpowers_gates.py`

**Interfaces:**
- Consumes: Task 1 の `core.sh` の関数。MeetNote の `scripts/agent-hooks/kiro`（4d430a73）。Kiro の入力: 読み取りは `read_file` の `tool_input.path`、`fs_write` は `{path, text}`、`fs_append` は `{path, text}`、`str_replace` は `{path, oldStr, newStr, replace_all}`。SessionStart に開始と圧縮の区別は無い
- Produces: `~/.agents/hooks/superpowers-gates/kiro <event>`、`<event>` は `pre-tool-use`、`post-tool-use`、`user-prompt-submit`

MeetNote の `kiro` との違い: push の分岐と `session-start` を持たない（圧縮の区別が無いので台帳の読み直しも出さない）。止めるメッセージには `sg_reminder` の文を ` After writing: ` で続ける。

`superpowers-gates.json.tmpl`: `{"version":"v1","hooks":[...]}`、名前は `superpowers-gates-pre-tool-use` などにする。`PreToolUse` の matcher `^(fs_write|fs_append|str_replace)$`、`PostToolUse` の matcher `^read_file$`、`UserPromptSubmit`。コマンドは `{{ .chezmoi.homeDir }}/.agents/hooks/superpowers-gates/kiro <event>`。

- [ ] **Step 1: テストを足す**

| テスト | 確かめること |
|---|---|
| `test_kiro_new_plan_is_blocked` | 計画への `fs_write` → 2、stderr に `Read ~/.agents/skills/writing-plans/SKILL.md` と `Self-Review checklist` |
| `test_kiro_read_file_counts` | `read_file` の post（`path` が `$HOME/.agents/skills/writing-plans/SKILL.md`）のあと同じ書き込み → 0 |
| `test_kiro_small_replace_is_allowed` | 5 行の `str_replace` → 0 |
| `test_kiro_append_to_missing_file_is_a_create` | 無い計画への `fs_append`（3 行）→ 2 |
| `test_kiro_hooks_file_is_valid` | テンプレートを `/home/u` に置き換えて JSON として読め、matcher が `^` と `$` で囲まれ、コマンドが `/home/u/.agents/hooks/superpowers-gates/kiro ` で始まる |

- [ ] **Step 2: 失敗することを確かめる**

Run: `uv run python -m unittest tests.test_superpowers_gates -v`
Expected: 新しい 5 件が FAIL

- [ ] **Step 3: `executable_kiro` とフックの設定を書く**

- [ ] **Step 4: 通ることを確かめる**

Run: `uv run python -m unittest tests.test_superpowers_gates tests.test_kiro_hooks -v`
Expected: `OK`（`test_superpowers_gates` は 35 件）

- [ ] **Step 5: コミット**

```bash
git add dot_agents/hooks/superpowers-gates/executable_kiro private_dot_kiro/hooks/superpowers-gates.json.tmpl tests/test_superpowers_gates.py
git commit -m "feat(agents): add the superpowers gates to Kiro CLI"
```

### Task 4: 反映して確かめる

コントローラーが Tats と行う。どれかの Expected が外れたら、その CLI のタスクに戻って直す。

- [ ] **Step 1: 全体の検査**

Run: `uvx pre-commit run --all-files` と `uv run python -m unittest discover -s tests`
Expected: どちらも PASS

- [ ] **Step 2: 差分を見てから反映する** — Codex の登録の変更は最初の `chezmoi apply` の前にすべて済ませる。Codex はフックの信頼を定義のハッシュごとに持つため、定義を変えると承認し直しになる。

Run: `chezmoi diff` を確かめたあと `chezmoi apply`
Expected: 差分が `~/.agents/hooks/superpowers-gates/`、`~/.claude/settings.json` の 4 つの登録、`~/.codex/hooks.json` の 4 つの登録、`~/.kiro/hooks/superpowers-gates.json` だけ

- [ ] **Step 2b: Codex でフックを承認する** — Codex の `/hooks` で、新しい 4 つのフック（PreToolUse、PostToolUse、UserPromptSubmit、PostCompact）を承認する。承認するまで動かない。

- [ ] **Step 3: MeetNote 以外のリポジトリで確かめる** — chezmoi のリポジトリで、各 CLI の新しいセッションに、skill を読ませずに `docs/superpowers/plans/2026-10-23-smoke.md` に 1 行書くよう頼む。Kiro はコントローラーが `kiro-cli chat --no-interactive --v3 --trust-tools=read_file,fs_write` で行い、Claude Code と Codex は Tats が行う。

Expected: Kiro は書き込みが止まり、メッセージに `~/.agents/skills/writing-plans/SKILL.md` と Self-Review の文が出る。Claude Code と Codex は、止まるか、先に skill を読んで通り、書いたあとに Self-Review の念押しが出る。どれもコミットさせず、smoke のファイルは消す。

- [ ] **Step 4: MeetNote では二重にならないことを確かめる** — MeetNote のブランチ `feat/agent-hooks` で Kiro に同じことを頼む。

Expected: 止めるメッセージが 1 つだけ（`.agents/skills/writing-plans/SKILL.md` を示す MeetNote 側のもの）

- [ ] **Step 5: 計画をコミットし、push を Tats に確かめる**

```bash
git add docs/superpowers/plans/2026-10-23-superpowers-gates.md
git commit -m "docs(plan): add the superpowers gates plan"
```
