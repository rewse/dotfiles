# Kiro approve-for-me 移行 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kiro の shell 自動承認を approve-for-me に任せ、permissions.yaml とフックを最小限にする。

**Architecture:** user スコープの permissions.yaml に `policies: [approve-for-me]` を書き、手書きのルールは秘密のパスの ask、fs_read / fs_write、skill、subagent、業務用 host の mcp allow だけにする。`redirect-guard-kiro.py` は、リダイレクト先のチェック（exit 2）と、展開後のパスによる秘密のパスのチェック（`permissionDecision: ask`）だけを持つ小さなスクリプトに書き直す。

**Tech Stack:** chezmoi テンプレート（Go template）、Kiro CLI v3 permissions、Python 3.9 互換の標準ライブラリ、unittest。

**Spec:** `docs/superpowers/archive/specs/2026-11-23-kiro-approve-for-me-design.md`

## Global Constraints

- フックは macOS の `/usr/bin/python3`（3.9）で動くこと。3.10 以降の構文（`X | None` の注釈、`match`）と `itertools.pairwise` は使わない
- 検証コマンドは `uv run python -m unittest discover -s tests` と `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files`（新しいファイルは stage してから）
- 公開リポジトリなので、コミットメッセージとコメントには変更内容と理由だけを書き、脆弱性の指摘や Issue には触れない
- コメントは今のコードについて書き、以前の挙動は書かない
- 一覧はアルファベット順にそろえる（`$secretPaths`、`SECRET_PATTERNS`）
- `private_dot_kiro/private_agents/private_main.json.tmpl` の `permissions` キーと `read-workspace` は変えない
- `dot_config/mcporter/private_mcporter.json.tmpl` の `"imports": []` は残す

## Review Focus

- ヒアドキュメントの本文にある `>` や `'`（`cat <<'EOF' > /tmp/x` の本文に `a > ~/.zshrc` と `it's`）を、リダイレクトとして誤検知しないこと
- クォートの中の `>`（`echo "a > b"`、`git log --format='%h > %s'`）を、リダイレクトとして扱わないこと
- `#` の扱い。bash は単語の途中の `#` をコメントにしないので、`x#y > ~/f` はブロックすること
- `cd /tmp && echo x > rel` のように、ディレクトリを移動してから相対パスに書き込むものはブロックすること
- `~/.ssh` へのシンボリックリンクを経由したパス（`link/id_ed25519`）でも、秘密のパスとして確認を出すこと

上の 5 件は、Task 2 の Step 1 の表に入れてある。

---

### Task 1: permissions.yaml を approve-for-me 前提に縮める

**Files:**
- Modify: `private_dot_kiro/private_settings/private_permissions.yaml.tmpl`
- Modify: `tests/test_kiro_permissions.py`
- Modify: `AGENTS.md`（22 行目の `mcporter call` allow の更新指示を削除し、40 行目付近の permissions の説明を approve-for-me に合わせる）
- Modify: `.chezmoitemplates/rules/common-standards.md`（Kiro CLI in Scripts の permissions.yaml の説明）

**Interfaces:**
- Produces: レンダリング後の YAML は、トップレベルに `policies: ["approve-for-me"]` と `rules` を持つ。`rules` は次のとおり。業務用 host のときだけ、最後に mcp allow `builder-mcp/ReadInternalWebsites` が加わる
  - shell ask 1 本（`$secretPaths`）
  - fs_read allow（今の 6 パターン）
  - fs_write allow（今の 5 パターン）
  - skill allow
  - subagent allow

- [ ] **Step 1: テストを書き直す**

`tests/test_kiro_permissions.py` から、削除する shell allow、agent-browser、mcporter、chezmoi、anydoc、sysctl、web_fetch / web_search を前提にしたテストを消す。テンプレートのレンダリングと matcher のヘルパーは、残すテストが使う分だけ残す。次のテストを置く。`self.rendered` はレンダリング結果の dict、`self.rules` はその `rules`。

```python
def test_policies_enable_approve_for_me(self) -> None:
    self.assertEqual(self.rendered["policies"], ["approve-for-me"])

def test_shell_has_only_the_secret_ask_rule(self) -> None:
    shell = [r for r in self.rules if r["capability"] == "shell"]
    self.assertEqual([r["effect"] for r in shell], ["ask"])
    self.assertEqual(tuple(shell[0]["match"]), secret_patterns())

def test_web_capabilities_have_no_rule(self) -> None:
    caps = {r["capability"] for r in self.rules}
    self.assertFalse({"web_fetch", "web_search"} & caps)

def test_remaining_capabilities(self) -> None:
    # Rendered for a personal host.
    self.assertEqual(
        sorted((r["capability"], r["effect"]) for r in self.rules),
        [("fs_read", "allow"), ("fs_write", "allow"), ("shell", "ask"),
         ("skill", "allow"), ("subagent", "allow")],
    )
```

既存の `test_read_paths_include_cwd`、`test_write_paths_are_limited`、`test_secret_patterns_*`、`test_rules_have_no_deny`、`test_secret_locations_have_a_standalone_ask_rule`、`test_builder_mcp_rule_is_host_gated` は、新しい形に合わせて残す。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run python -m unittest tests.test_kiro_permissions -v`
Expected: `test_policies_enable_approve_for_me` と `test_shell_has_only_the_secret_ask_rule` が FAIL

- [ ] **Step 3: テンプレートを書き換える**

`rules:` の前に `policies: ["approve-for-me"]` を追加する。shell の allow 6 本と、web_fetch / web_search のルールを削除する。冒頭のコメントには次の 3 点を書く。
- ルールで決まらない操作は approve-for-me が判断すること
- ask は allow と evaluate より強いこと
- リダイレクトとグロブで書いた秘密のパスは redirect-guard-kiro.py が見ること

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_permissions -v`
Expected: PASS

Run: `chezmoi execute-template < private_dot_kiro/private_settings/private_permissions.yaml.tmpl | uv run --with pyyaml python -c 'import sys,yaml; print(yaml.safe_load(sys.stdin)["policies"])'`
Expected: `['approve-for-me']`

- [ ] **Step 5: ドキュメントを直す**

- AGENTS.md の、mcporter のサーバーを変えたときの指示から、`mcporter call` allow の更新を外す。SKILL.md の更新指示は残す
- AGENTS.md の Kiro CLI v3 の段落にある「MCP tool は正確な名前でだけ allow する」は残す
- common-standards の Kiro CLI in Scripts で、`main` エージェントの説明を「approve-for-me が判断し、秘密のパスは確認を出す」という内容に直す

- [ ] **Step 6: 全体の検証とコミット**

Run: `uv run python -m unittest tests.test_kiro_permissions tests.test_kiro_agent` と pre-commit
Expected: すべて PASS。フックのテストは Task 2 で直すので、このタスクでは触らない

```bash
git add private_dot_kiro/private_settings/private_permissions.yaml.tmpl tests/test_kiro_permissions.py AGENTS.md .chezmoitemplates/rules/common-standards.md
git commit -m "refactor(kiro): let approve-for-me judge commands no rule settles"
```

### Task 2: redirect-guard-kiro.py を二つのチェックだけに書き直す

**Files:**
- Modify: `dot_agents/hooks/executable_redirect-guard-kiro.py`（全面的に書き直す）
- Modify: `tests/test_kiro_hooks.py`（`RedirectGuardKiroTest` を書き直す。他のクラスは触らない）

**Interfaces:**
- Consumes: Task 1 の `$secretPaths` と同じ並びの `SECRET_PATTERNS`。`test_secret_patterns_match_template_list` が両者を比べる
- Produces: `main() -> int` は、標準入力から Kiro PreToolUse の JSON（`cwd`、`tool_input.command`、`tool_input.cwd`）を読み、次のどれかを返す
  - リダイレクト先が許可外: stderr に理由を書いて 2 を返す
  - 秘密のパスに当たる: 標準出力に `{"hookSpecificOutput": {"permissionDecision": "ask", "permissionDecisionReason": "<理由>"}}` を書いて 0 を返す
  - どちらでもない: 何も書かずに 0 を返す
- Produces: `blocked_targets(command: str, root_cwd: str, cwd: Optional[str] = None) -> List[str]` と `secret_paths(command: str, root_cwd: str, cwd: Optional[str] = None) -> List[str]`

- [ ] **Step 1: テストを書く**

`RedirectGuardKiroTest` を、次の表で書き直す。既存のテストのうち、リダイレクト、ヒアドキュメント、クォート、コメント、cd、シンボリックリンクを扱うものは、入出力をそのまま流用してよい。出力オプション、再帰読み取り、mcporter、chezmoi のテストは削除する。

| コマンド（session cwd は一時ディレクトリ） | 期待 |
|---|---|
| `git log > ~/.zshrc` | exit 2 |
| `git log >> ~/.zshrc`、`git log &> ~/.zshrc`、`git log >\| ~/.zshrc` | exit 2 |
| `git log > /tmp/x`、`git log > out.txt`、`git log > /dev/null`、`git log 2>&1` | exit 0、出力なし |
| `git log > $HOME/x`、`` git log > `pwd`/x `` | exit 2 |
| `echo "a > b"`、`git log --format='%h > %s'` | exit 0、出力なし |
| `cat <<'EOF' > /tmp/x`。本文は `a > ~/.zshrc` と `it's` | exit 0、出力なし |
| `x#y > ~/f` | exit 2 |
| `cd /tmp && echo x > rel` | exit 2 |
| `echo 'x > ~/f`（閉じていないクォートと `>`） | exit 2 |
| `/tmp` 配下に置いた、`~/.zshrc` へのシンボリックリンクへのリダイレクト | exit 2 |
| `git diff --no-index ~/.a?s/c* /dev/null`（`HOME` を一時ディレクトリにして `.aws/credentials` を作る） | ask |
| `cat < ~/.ssh/id_ed25519` | ask |
| 一時ディレクトリに `~/.ssh` へのリンク `link` を作ってから `cat link/id_ed25519` | ask |
| `rg foo src`、`cat README.md` | exit 0、出力なし |

ask のテストでは、標準出力を JSON として読み、`permissionDecision` が `"ask"` で、`permissionDecisionReason` が空でないことを確かめる。

- [ ] **Step 2: テストが失敗することを確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks -v`
Expected: ask を期待するテストが FAIL（今のフックは exit 2 を返すか、何も返さない）

- [ ] **Step 3: フックを書き直す**

- モジュールの docstring には、残す二つのチェックと、それぞれが要る理由を書く。理由は、Kiro がリダイレクトを外してから照合することと、ask ルールが文字列でしか照合しないこと
- 今のファイルからは、Step 1 の表を通すのに要るものだけを残す。`SECRET_PATTERNS`、`allowed_roots`、`resolve`、`is_allowed`、`is_secret`、`input_paths`、`tokenize`、ヒアドキュメントと算術展開の処理などがこれに当たる
- `OUTPUT_OPTIONS`、`FILE_READERS`、`TREE_READERS`、`SECRET_SUFFIXES`、mcporter と chezmoi の関数は削除する
- `LINK_COMMANDS` による複合コマンドの判定は、表のシンボリックリンクの行を通すのに要らなければ削除する
- `secret_paths` は、字句解析した全トークン（`<` の入力元を含む）に `input_paths` を当て、`is_secret` に当たったトークンを返す

- [ ] **Step 4: テストが通ることを確かめる**

Run: `uv run python -m unittest tests.test_kiro_hooks -v`
Expected: PASS

Run: `printf '%s' '{"cwd":"/tmp","tool_input":{"command":"git log > ~/.zshrc"}}' | /usr/bin/python3 dot_agents/hooks/executable_redirect-guard-kiro.py; echo $?`
Expected: `2`

- [ ] **Step 5: 全体の検証とコミット**

Run: `uv run python -m unittest discover -s tests` と pre-commit
Expected: すべて PASS

```bash
git add dot_agents/hooks/executable_redirect-guard-kiro.py tests/test_kiro_hooks.py
git commit -m "refactor(kiro): reduce the redirect guard to redirects and secret paths"
```

## マージ後

- Apply: 各 host で `chezmoi apply ~/.kiro/settings/permissions.yaml ~/.agents/hooks/redirect-guard-kiro.py ~/.agents/rules/common-standards.md`
- Verify: 新しい Kiro セッションで `/permissions` を開き、approve for me が有効と表示されること
- Verify: そのセッションで `cat ~/.aws/config` を頼むと確認が出ること。グロブで書いた `cat ~/.a?s/config` でも確認が出ること。これで Kiro がフックの ask 応答を受け付けることを確かめる
