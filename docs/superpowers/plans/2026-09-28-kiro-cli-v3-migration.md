# Kiro CLI v3 移行 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** chezmoi が配布する Kiro CLI 設定を v3 エンジン専用に書き換え、権限・hooks・otty バッジを v3 で現行と同等に動かす。

**Architecture:** 権限は `~/.kiro/settings/permissions.yaml`（ユーザースコープ）、hooks は `~/.kiro/hooks/*.json`（v3 単独ファイル形式）に移し、`default.json` からは v2 専用フィールドを除く。ドキュメント間で食い違う仕様は Task 1 で実機確認し、その結果（V1〜V8）を後続タスクが参照する。

**Tech Stack:** chezmoi テンプレート（Go template）、Kiro CLI v3、bash、Python 3 標準ライブラリ（`unittest`）、jq

**Spec:** `docs/superpowers/specs/2026-09-28-kiro-cli-v3-migration-design.md`

## Global Constraints

- v2 との互換は維持しない。
- 書き込み許可は `./**`、`~/Desktop/**`、`~/Downloads/**`、`/tmp/**` の4つに限る。
- `builder-mcp` の許可は hostname `7cf34ded5d65` のときだけ入れる。
- otty 関連（`otty-state.sh`、`otty-state.json`）は darwin のみ配布する。
- `Stop` hook は japanese-guard、otty-state の順に実行する。
- `enforce-uv.sh` は Claude Code・Codex の入力形式を引き続き扱う。
- コメントは英語、コミットは Conventional Commits。`dot_*` の変更に `docs:` を使わない。
- `chezmoi apply` は `--force` 付きで実行する（TTY なしでは失敗する）。
- テストは `python3 -m unittest discover -s tests` で実行する。CI は pre-commit（ruff、basedpyright、shellcheck）を回すので、コミット前に `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files` を通す。

## Review Focus

1. Linux ホストで hooks が壊れる: `.chezmoiignore` が `.kiro/hooks` 全体を除外したままだと enforce-uv と japanese-guard が配布されず、otty 用ファイルを除外し忘れると存在しない `otty` を呼ぶ。Task 3 のテストで除外対象を固定する。
2. 複合コマンドの素通り: `rg foo && rm -rf x` が `rg *` の許可で確認なしに通ると危険。Task 1 の V5 で v3 の分割挙動を確認し、Task 5 の E2E で確認を求められることを見る。
3. japanese-guard の無限ループ: 書き直し後の回答も英語だった場合に Stop が block を返し続ける。Task 3 のテストで2回目の Stop が通ることを固定する。
4. builder-mcp 許可の漏れ出し: hostname 条件の外に `mcp` ルールが出ると個人 Mac でも許可される。Task 2 のテストで条件ブロック内にあることを固定する。
5. 許可外パスへの書き込み: `~/.zshrc` のような許可外パスは確認を求められるべき。Task 5 の E2E で確認する。

---

### Task 1: v3 導入と前提の実機確認

**Files:**
- Modify: `docs/superpowers/plans/2026-09-28-kiro-cli-v3-migration.md`（末尾の「Task 1 の結果」節に記録）

**Interfaces:**
- Produces: 以下の確認結果 V1〜V8。後続タスクはこの節の値を使う。
  - V1: `chat.agentEngine` の値と、v3 で無効なキーの一覧（`chat.enableCheckpoint` を含むか）
  - V2: CLI が読む hook ファイルの場所（`~/.kiro/hooks/*.json` か）と、CLI で発火するトリガー名（`SessionStart` または `AgentSpawn` 等）
  - V3: `PreToolUse` の stdin でのシェルツール名とコマンド文字列のパス、`Stop` の stdin でのセッション ID・最終回答・再入フラグのキー名、`KIRO_SESSION_ID` 環境変数の有無
  - V4: 「常に許可」を選んだとき Kiro が `~/.kiro/settings/permissions.yaml` に書き込むか
  - V5: shell の `match: ["cat"]` が `cat foo` に一致するか。`rg foo && rm x` が部分ごとに評価されるか
  - V6: `@builtin/knowledge` に対応する capability 名
  - V7: MCP ツールを許可する `match` の書式（例 `@builder-mcp/*` か `builder-mcp/*`）
  - V8: `permissions.yaml` の `match` が `~` を展開するか

- [ ] **Step 1: v2 セッションを退避する**

Run: `command cp -R ~/.kiro/sessions ~/.kiro/sessions-v2-backup && ls ~/.kiro/sessions-v2-backup | head -3`
Expected: 退避先に `cli` が表示される

- [ ] **Step 2: kiro-cli を v3 対応版に更新する**

Run: `kiro-cli update` （使えなければ `curl -fsSL https://cli.kiro.dev/install | bash`）の後に `kiro-cli --version && kiro-cli --help | rg -- '--v3'`
Expected: `--v3` の行が表示される

- [ ] **Step 3: 使い捨ての確認用設定で V1〜V8 を調べる**

`KIRO_HOME=$(mktemp -d)` を使い、実環境の `~/.kiro` を変えずに調べる。stdin を `/tmp/kiro-hook-<trigger>.json` に書き出すだけの hook（`cat > /tmp/kiro-hook-$TRIGGER.json`）を全トリガーに登録し、`kiro-cli --v3 chat` で1ターン回して発火したトリガーと入力を記録する。V1 は `kiro-cli settings list` と `kiro-cli --v3 diagnostic`、V4〜V8 は確認用 `permissions.yaml` を置いて実際に確認プロンプトの有無を見る。

- [ ] **Step 4: 結果を本ファイル末尾の「Task 1 の結果」節に書き、コミットする**

```bash
git add docs/superpowers/plans/2026-09-28-kiro-cli-v3-migration.md
git commit -m "docs: record Kiro CLI v3 behavior checks"
```

V2 で `~/.kiro/hooks/*.json` が読まれない、または V4 で Kiro が `permissions.yaml` に書き込むと分かった場合は、spec の代替手順（エージェント埋め込み hooks に戻す／実機ファイルを正として `chezmoi add`）に従って Task 2・3 の対象ファイルを読み替える。

### Task 2: permissions.yaml テンプレート

**Files:**
- Create: `dot_kiro/settings/private_permissions.yaml.tmpl`
- Test: `tests/test_kiro_permissions.py`

**Interfaces:**
- Consumes: V5、V6、V7、V8
- Produces: `~/.kiro/settings/permissions.yaml`。Task 4 はこれを前提に `toolsSettings` と `allowedTools` を消す。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_kiro_permissions.py` にテンプレート本文を文字列として読む `KiroPermissionsTest` を作る。

```python
def test_shell_patterns_are_globs(self) -> None:
    # Every quoted match value must be free of regex syntax.
    for value in self.match_values():
        with self.subTest(value=value):
            self.assertNotRegex(value, r"[\^$|()]|\.\*|\.\+")

def test_legacy_commands_are_kept(self) -> None:
    for pattern in ("rg", "git -P diff", "jq", "mcporter", "defaults read",
                    "docker compose logs", "journalctl* --no-pager*", "nslookup *"):
        with self.subTest(pattern=pattern):
            self.assertIn(f'"{pattern}', self.text)

def test_write_paths_are_limited(self) -> None:
    self.assertEqual(self.paths_for("fs_write"),
                     ["./**", "{{ .chezmoi.homeDir }}/Desktop/**",
                      "{{ .chezmoi.homeDir }}/Downloads/**", "/tmp/**"])

def test_builder_mcp_rule_is_host_gated(self) -> None:
    gate = self.text.index('{{- if eq .chezmoi.hostname "7cf34ded5d65" }}')
    end = self.text.index("{{- end }}", gate)
    self.assertIn("builder-mcp", self.text[gate:end])
    self.assertNotIn("builder-mcp", self.text[:gate] + self.text[end:])
```

`match_values()` は `"..."` で囲まれた `match` 配下の値、`paths_for(capability)` はそのルールの `match` 配列を返すヘルパーとしてテスト内に書く（YAML ライブラリは使わない）。V8 で `~` が展開されると分かったら、パスは `~/Desktop/**` 形式にしてテストの期待値も合わせる。

- [ ] **Step 2: 失敗を確認する**

Run: `python3 -m unittest tests.test_kiro_permissions -v`
Expected: FAIL（`FileNotFoundError`）

- [ ] **Step 3: テンプレートを書く**

`dot_kiro/agents/default.json.tmpl` の `allowedCommands` を spec の変換規則で移す。`X( .*)?` は V5 に応じて `X` と `X *`（または `X*` 1件）、`(a|b)` は展開、`.+`/`.*` は `*`。ルールは capability 単位にまとめ、`shell`、`fs_read`、`fs_write`、`web_fetch`、`web_search`、`subagent`、V6 の capability、hostname 条件付きの `mcp`（V7 書式で `builder-mcp` の全ツール）の順に並べる。すべて `effect: allow`。`shell` の `match` 配列はアルファベット順を保つ。

- [ ] **Step 4: テストとレンダリングを確認する**

Run: `python3 -m unittest tests.test_kiro_permissions -v && chezmoi execute-template < dot_kiro/settings/private_permissions.yaml.tmpl > /tmp/permissions.yaml && KIRO_HOME=$(mktemp -d) sh -c 'mkdir -p $KIRO_HOME/settings && command cp /tmp/permissions.yaml $KIRO_HOME/settings/ && kiro-cli --v3 diagnostic'`
Expected: テスト PASS、diagnostic に permissions のエラーなし

- [ ] **Step 5: コミットする**

```bash
git add dot_kiro/settings/private_permissions.yaml.tmpl tests/test_kiro_permissions.py
git commit -m "feat(kiro): define v3 permissions in permissions.yaml"
```

### Task 3: v3 hooks とスクリプトの入力対応

**Files:**
- Create: `dot_kiro/hooks/agent-guards.json.tmpl`, `dot_kiro/hooks/otty-state.json.tmpl`
- Modify: `.chezmoiignore:23`, `dot_agents/hooks/executable_enforce-uv.sh:7`, `dot_agents/hooks/executable_japanese-guard-kiro.py`, `dot_kiro/hooks/executable_otty-state.sh:19-20`
- Test: `tests/test_kiro_hooks.py`

**Interfaces:**
- Consumes: V2、V3
- Produces: `~/.kiro/hooks/agent-guards.json`（全 OS）、`~/.kiro/hooks/otty-state.json`（darwin）。Task 4 はこれを前提にエージェントの `hooks` を消す。

hook ファイルの形式:

```json
{"version": "v1", "hooks": [{"name": "enforce-uv", "trigger": "PreToolUse", "matcher": "<V3 shell tool name>", "action": {"type": "command", "command": "{{ .chezmoi.homeDir }}/.agents/hooks/enforce-uv.sh"}}]}
```

`agent-guards.json.tmpl` は `enforce-uv`（PreToolUse）と `japanese-guard`（Stop）。`otty-state.json.tmpl` は全体を `{{ if eq .chezmoi.os "darwin" }}` で囲まず、`.chezmoiignore` で除外する。中身は V2 のセッション開始トリガーと `Stop` で `otty-state.sh idle`、`UserPromptSubmit`・`PreToolUse`・`PostToolUse` で `otty-state.sh processing`。

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_kiro_hooks.py`:

```python
class EnforceUvTest(unittest.TestCase):
    # Runs dot_agents/hooks/executable_enforce-uv.sh with bash and JSON on stdin.
    def test_blocks_pip_in_claude_and_kiro_v3_payloads(self) -> None:
        for payload in (CLAUDE_SHELL_PAYLOAD, KIRO_V3_SHELL_PAYLOAD):
            with self.subTest(payload=payload):
                self.assertEqual(run_enforce_uv(payload, "pip install foo").returncode, 2)

    def test_allows_uv(self) -> None:
        self.assertEqual(run_enforce_uv(KIRO_V3_SHELL_PAYLOAD, "uv add foo").returncode, 0)

class JapaneseGuardKiroTest(unittest.TestCase):
    # Copies the hook into a temp dir next to a stub japanese-guard.py whose
    # is_english() returns text.startswith("EN") and REASON is "{quoted}",
    # and sets TMPDIR to that dir so markers stay isolated.
    def test_blocks_english_answer(self) -> None:
        out = self.run_stop(response="EN answer")
        self.assertEqual(json.loads(out)["decision"], "block")

    def test_passes_japanese_answer(self) -> None:
        self.assertEqual(self.run_stop(response="日本語の回答"), "")

    def test_second_stop_in_same_turn_passes(self) -> None:
        self.run_stop(response="EN answer")
        self.assertEqual(self.run_stop(response="EN again", reentry=True), "")

class ChezmoiIgnoreTest(unittest.TestCase):
    def test_linux_ignores_only_otty_hooks(self) -> None:
        linux = linux_block(read(".chezmoiignore"))
        self.assertIn(".kiro/hooks/otty-state.sh", linux)
        self.assertIn(".kiro/hooks/otty-state.json", linux)
        self.assertNotIn(".kiro/hooks\n", linux)
```

`KIRO_V3_SHELL_PAYLOAD` と `run_stop()` が作る Stop 入力は V3 のキー名で組む。`reentry=True` は、V3 に再入フラグがあればそれを立て、なければ同じセッション ID で2回呼ぶだけにする。`linux_block()` は `.chezmoiignore` の `{{- else }}` から最初の `{{- end }}` までを返す。

- [ ] **Step 2: 失敗を確認する**

Run: `python3 -m unittest tests.test_kiro_hooks -v`
Expected: `KIRO_V3_SHELL_PAYLOAD` の形が現行と違えば EnforceUvTest が、`.chezmoiignore` のテストが FAIL

- [ ] **Step 3: スクリプトと設定を直す**

- `enforce-uv.sh`: V3 のコマンド文字列パスが `.tool_input.command` と違う場合だけ、jq の `//` でそのパスを追加する。
- `japanese-guard-kiro.py`: V3 のキー名に合わせる。再入フラグがあれば marker を廃止して `if data.get("<V3 flag>"): return` にし、docstring を現状に合わせて書き直す。
- `otty-state.sh`: V3 で `KIRO_SESSION_ID` がない場合は `SESSION=${KIRO_SESSION_ID:-$(jq -r '.session_id // empty' 2>/dev/null)}` でキャッシュキーを作る（V3 のキー名に合わせる）。
- `.chezmoiignore`: Linux ブロックの `.kiro/hooks` を `.kiro/hooks/otty-state.json` と `.kiro/hooks/otty-state.sh` に置き換える（アルファベット順）。
- hook ファイル2つを作る。

- [ ] **Step 4: テストとレンダリングを確認する**

Run: `python3 -m unittest tests.test_kiro_hooks -v && for f in dot_kiro/hooks/*.json.tmpl; do chezmoi execute-template < "$f" | jq -e .version; done`
Expected: テスト PASS、各ファイルで `"v1"`

- [ ] **Step 5: コミットする**

```bash
git add .chezmoiignore dot_agents/hooks dot_kiro/hooks tests/test_kiro_hooks.py
git commit -m "feat(kiro): move hooks to v3 hook files"
```

### Task 4: default エージェントと cli.json の v3 化

**Files:**
- Modify: `dot_kiro/agents/default.json.tmpl`, `dot_kiro/settings/private_cli.json.tmpl`
- Test: `tests/test_kiro_agent.py`

**Interfaces:**
- Consumes: Task 2 の `permissions.yaml`、Task 3 の hook ファイル、V1

- [ ] **Step 1: 失敗するテストを書く**

```python
def test_default_agent_has_no_v2_fields(self) -> None:
    for key in ("toolsSettings", "allowedTools", '"hooks"', "useLegacyMcpJson"):
        with self.subTest(key=key):
            self.assertNotIn(key, AGENT.read_text())
    self.assertIn('"includeMcpJson": true', AGENT.read_text())

def test_cli_selects_v3_engine(self) -> None:
    self.assertIn('"chat.agentEngine": "<V1 value>"', CLI.read_text())
```

V1 で無効と分かったキーごとに `assertNotIn` を足す。

- [ ] **Step 2: 失敗を確認する**

Run: `python3 -m unittest tests.test_kiro_agent -v`
Expected: FAIL

- [ ] **Step 3: 2ファイルを書き換える**

`default.json.tmpl` から4フィールドを削り、`includeMcpJson: true` を `mcpServers` の後に置く。`cli.json.tmpl` に `chat.agentEngine` をキー順（アルファベット順）の位置で足し、V1 の無効キーを消す。末尾改行なしの挙動は維持する。

- [ ] **Step 4: テストと diagnostic を確認する**

Run: `python3 -m unittest discover -s tests && chezmoi diff ~/.kiro | head -200 && chezmoi apply --force ~/.kiro ~/.agents/hooks && kiro-cli --v3 diagnostic`
Expected: 全テスト PASS、diff は Task 2〜4 の変更だけ、diagnostic にエラーなし

- [ ] **Step 5: コミットする**

```bash
git add dot_kiro/agents/default.json.tmpl dot_kiro/settings/private_cli.json.tmpl tests/test_kiro_agent.py
git commit -m "feat(kiro): switch the default agent to the v3 engine"
```

### Task 5: ドキュメント更新と E2E 確認

**Files:**
- Modify: `AGENTS.md`（Managed files 節）, `README.md:97` 付近

- [ ] **Step 1: ドキュメントを更新する**

`AGENTS.md` に「Kiro の権限は `dot_kiro/settings/private_permissions.yaml.tmpl`、hooks は `dot_kiro/hooks/*.json.tmpl` に置き、エージェントに埋め込まない」旨を1〜2文で足す（V4 で実機ファイルを正とした場合はその旨）。`README.md` のツリーに `hooks/` と `settings/` の役割を追記する。

- [ ] **Step 2: v3 セッションで E2E を確認する**

`kiro-cli chat`（`--v3` なしで v3 が起動すること自体も確認）で次を順に試す。

- `rg`、`git -P diff`、`jq` が確認なしで実行される
- `rg foo && rm /tmp/kiro-e2e-x` と `~/.zshrc` への書き込みが確認を求められる
- `pip install foo` が enforce-uv にブロックされる
- 英語で答えるよう頼むと japanese-guard が一度だけ書き直しを求める
- otty のタブバッジが実行中と完了に切り替わる
- 業務用 Mac で `builder-mcp` の `ReadInternalWebsites` が確認なしで使える

Expected: すべて期待どおり。外れた項目は該当タスクに戻って直す。

- [ ] **Step 3: pre-commit を通してコミットする**

```bash
uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files
git add AGENTS.md README.md
git commit -m "docs: describe Kiro CLI v3 permissions and hooks layout"
```

- [ ] **Step 4: Linux ホストを確認する**

Linux ホストで `cat /etc/os-release` が AL2 でないこと、`kiro-cli --help | rg -- '--v3'` が出ること、`chezmoi apply --force` 後に `~/.kiro/hooks/agent-guards.json` があり `otty-state.*` がないことを確認する。

## Task 1 の結果

（Task 1 で記入する）
