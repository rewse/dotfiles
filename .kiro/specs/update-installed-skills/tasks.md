# インストール済みスキル更新の実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development or inline execution to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `run_install-skills.sh` の全対象を取得元の最新版へ更新し、現行 lock に登録し、部分的な失敗を成功扱いにしない。

**Architecture:** ディレクトリの存在に基づく `skills update` を廃止し、取得元が明示された `skills add` を毎回実行する。各外部コマンドは共通の失敗カウンターへ記録し、すべての処理を終えた後で終了コードを決定する。

**Tech Stack:** Bash 3.2以降、skills CLI 1.5.23、uv、OfficeCLI、jq

## Global Constraints

- 旧 `~/.agents/.skill-lock.json` は現行 lock の検証後に削除する。
- 現行 lock は `${XDG_STATE_HOME:-$HOME/.local/state}/skills/.skill-lock.json` とする。
- 個別処理が失敗しても残りを続行し、1件以上失敗した場合は最後に非ゼロ終了する。
- スキル内容へのローカルパッチと OfficeCLI 自体の更新は行わない。
- コミットは明示的に依頼された場合だけ行う。

---

### Task 1: 更新処理と失敗集計

**Files:**
- Modify: `run_install-skills.sh`
- Reference: `.kiro/specs/update-installed-skills/design.md`

**Interfaces:**
- Consumes: `install_skills <owner/repo> <skill>...` と `install_skills_claude_only <owner/repo> <skill>...`
- Produces: 全対象への `skills add`、`failures` カウンター、最後の終了コード

- [ ] **Step 1: 現行処理が未登録スキルを更新できないことを確認する**

Run:

```bash
before=$(shasum -a 256 ~/.agents/skills/tavily-search/SKILL.md | cut -d' ' -f1)
skills update tavily-search -g </dev/null
after=$(shasum -a 256 ~/.agents/skills/tavily-search/SKILL.md | cut -d' ' -f1)
test "$before" = "$after"
```

Expected: `No installed skills found matching: tavily-search` が表示され、ハッシュが変わらない。

- [ ] **Step 2: 毎回 add する更新処理を実装する**

`install_skills` は各対象について次を実行する。

```bash
if ! skills add "$repo" --skill "$skill" -g "${AGENTS[@]}" -y < /dev/null; then
  echo "Failed to update skill: $skill" >&2
  failures=$((failures + 1))
fi
```

`install_skills_claude_only` も `--agent claude-code` で同じ失敗集計を行う。`AGENTS` は文字列ではなくBash配列にし、未使用の `AGENTS_NO_CLAUDE` を削除する。

- [ ] **Step 3: 補助処理を失敗集計へ含める**

ppt-master の `uv venv`、`uv pip install`、OfficeCLI の `skills codex` と各 `skills install` をそれぞれ `if ! ...; then` で囲み、処理名を標準エラーへ表示して `failures` を加算する。OfficeCLI が PATH にない場合も `find officecli` の失敗を記録する。

- [ ] **Step 4: 最終終了判定を追加する**

ファイル末尾へ次を追加する。

```bash
if [ "$failures" -ne 0 ]; then
  echo "$failures skill installation step(s) failed" >&2
  exit 1
fi
```

- [ ] **Step 5: シェル構文を検証する**

Run:

```bash
bash -n run_install-skills.sh
```

Expected: 終了コード0、出力なし。

### Task 2: 全対象の更新と配布検証

**Files:**
- Execute: `run_install-skills.sh`
- Inspect: `${XDG_STATE_HOME:-$HOME/.local/state}/skills/.skill-lock.json`
- Inspect: `~/.agents/skills/`, `~/.claude/skills/`, `~/.kiro/skills/`

**Interfaces:**
- Consumes: Task 1で修正したスクリプト
- Produces: 最新のスキル本体、現行 lock の取得元情報、エージェント向けリンク、旧 lock の削除

- [ ] **Step 1: スクリプト全体を実行する**

Run:

```bash
bash run_install-skills.sh
```

Expected: 全対象の処理を継続し、すべて成功した場合は終了コード0。

- [ ] **Step 2: 現行 lock の登録を検証する**

`run_install-skills.sh` から `install_skills` 系の対象名を抽出し、各名前について次が空でないことを確認する。

```bash
jq -er --arg skill "$skill" '.skills[$skill] | .source and .sourceUrl and .skillPath and .skillFolderHash' \
  "${XDG_STATE_HOME:-$HOME/.local/state}/skills/.skill-lock.json"
```

Expected: skills CLI 管理対象29件すべてが成功する。

- [ ] **Step 3: 旧 lock を削除する**

現行 lock に全対象が取得元付きで登録されたことを確認してから削除する。

```bash
rm "$HOME/.agents/.skill-lock.json"
test ! -e "$HOME/.agents/.skill-lock.json"
```

Expected: 旧 lock が存在せず、`skills list -g --json` が現行 lock の取得元情報を表示する。

- [ ] **Step 4: 取得元との内容一致を検証する**

取得元ごとに一時ディレクトリへ最新コミットをcloneし、lockの `skillPath` にあるディレクトリと `~/.agents/skills/<name>` を比較する。Claude専用の `pdf` は `~/.claude/skills/pdf` と比較する。

Expected: 全対象で差分なし。

- [ ] **Step 5: 配布リンクとOfficeCLIスキルを検証する**

Run:

```bash
for skill in $(jq -r '.skills | keys[]' "${XDG_STATE_HOME:-$HOME/.local/state}/skills/.skill-lock.json"); do
  test -e "$HOME/.agents/skills/$skill" || test -e "$HOME/.claude/skills/$skill"
done
for skill in officecli officecli-docx officecli-pptx officecli-xlsx; do
  test -f "$HOME/.agents/skills/$skill/SKILL.md"
done
```

対象スキルについて Claude Code と Kiro CLI のリンク先が `~/.agents/skills/<name>` であることも確認する。

Expected: 全確認が成功する。

- [ ] **Step 6: 差分をレビューする**

Run:

```bash
git -P diff --check
git -P diff -- run_install-skills.sh .kiro/specs/update-installed-skills/
git -P status --short
```

Expected: whitespaceエラーなし。意図したスクリプトとspecだけが変更されている。
