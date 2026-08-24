# エージェント指示本文の共通化と Codex 対応実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 6 agentのdescriptionと本文を `.chezmoitemplates/agents/` に集約し、Claude Code、Kiro、Codex向け定義を同じ情報から生成する。

**Architecture:** 既存のClaude/Kiro descriptionと本文が一致することを確認してから、`description/` と `body/` へ分けて抽出する。各プラットフォームの名前、ツール、権限、sandboxは専用テンプレートに残し、descriptionと本文を `template` または `includeTemplate` で生成する。

**Tech Stack:** chezmoi、Go template、Markdown、JSON、TOML、Node.js

## Global Constraints

- 対象は `build-error-resolver`、`code-reviewer`、`doc-updater`、`planner`、`python-reviewer`、`refactor-cleaner` の6件とする。
- descriptionは `.chezmoitemplates/agents/description/` にAgent Manifestの `Name` を使ったテキストとして置く。
- 本文は `.chezmoitemplates/agents/body/` にAgent Manifestの `Name` を使ったMarkdownとして置く。
- Claude/Kiroの既存metadata、権限、MCP設定を維持する。
- Codexのモデルとreasoning effortは親セッションから継承する。
- Codex sandboxはレビュー・計画系を `read-only`、修正系を `workspace-write` とする。
- レビュー承認前にコミットしない。

## Agent Manifest

| Name | Description | Codex sandbox |
|---|---|---|
| `build-error-resolver` | `Build and TypeScript error resolution specialist. Use PROACTIVELY when build fails or type errors occur. Fixes build/type errors only with minimal diffs, no architectural edits. Focuses on getting the build green quickly.` | `workspace-write` |
| `code-reviewer` | `Expert code review specialist. Proactively reviews code for quality, security, and maintainability. Use immediately after writing or modifying code. MUST BE USED for all code changes.` | `read-only` |
| `doc-updater` | `Documentation and codemap specialist. Use PROACTIVELY for updating codemaps and documentation. Runs /update-codemaps and /update-docs, generates docs/CODEMAPS/*, updates READMEs and guides.` | `workspace-write` |
| `planner` | `Expert planning specialist for complex features and refactoring. Use PROACTIVELY when users request feature implementation, architectural changes, or complex refactoring. Automatically activated for planning tasks.` | `read-only` |
| `python-reviewer` | `Expert Python code reviewer specializing in PEP 8 compliance, Pythonic idioms, type hints, security, and performance. Use for all Python code changes. MUST BE USED for Python projects.` | `read-only` |
| `refactor-cleaner` | `Dead code cleanup and consolidation specialist. Use PROACTIVELY for removing unused code, duplicates, and refactoring. Runs analysis tools (knip, depcheck, ts-prune) to identify dead code and safely removes it.` | `workspace-write` |

---

### Task 1: 共通descriptionと本文を抽出する

**Files:**
- Create: `.chezmoitemplates/agents/description/*.txt` 6件
- Create: `.chezmoitemplates/agents/body/*.md` 6件

**Interfaces:**
- Consumes: Claude/Kiroの既存Markdown本文
- Produces: 3プラットフォームが参照する6件のdescriptionと本文

- [ ] **Step 1: Claude/Kiro本文が6件すべて一致することを確認する**

Run:

```bash
for agent_name in build-error-resolver code-reviewer doc-updater planner python-reviewer refactor-cleaner; do
  awk 'BEGIN{sep=0} /^---$/{sep++; next} sep>=2{print}' "dot_claude/agents/${agent_name}.md" > "/tmp/claude-${agent_name}.md"
  awk 'BEGIN{sep=0} /^---$/{sep++; next} sep>=2{print}' "dot_kiro/agents/${agent_name}.md" > "/tmp/kiro-${agent_name}.md"
  cmp "/tmp/claude-${agent_name}.md" "/tmp/kiro-${agent_name}.md"
done
```

Expected: exit 0。

- [ ] **Step 2: description/bodyディレクトリがまだ存在しないことを確認する**

Run:

```bash
test -d .chezmoitemplates/agents/description
test -d .chezmoitemplates/agents/body
```

Expected: exit 1。

- [ ] **Step 3: Claude定義からdescriptionと本文を機械的に抽出する**

Run:

```bash
mkdir -p .chezmoitemplates/agents/description .chezmoitemplates/agents/body
for agent_name in build-error-resolver code-reviewer doc-updater planner python-reviewer refactor-cleaner; do
  sed -n 's/^description: //p' "dot_claude/agents/${agent_name}.md" > ".chezmoitemplates/agents/description/${agent_name}.txt"
  awk 'BEGIN{sep=0} /^---$/{sep++; next} sep>=2{print}' "dot_claude/agents/${agent_name}.md" | sed '1{/^$/d;}' > ".chezmoitemplates/agents/body/${agent_name}.md"
done
```

Expected: description 6件と本文6件が作成される。

### Task 2: Claude/Kiro Markdownをテンプレート化する

**Files:**
- Rename and modify: 対象6件の `dot_claude/agents/*.md` を同名の `*.md.tmpl` へ変更
- Rename and modify: 対象6件の `dot_kiro/agents/*.md` を同名の `*.md.tmpl` へ変更

**Interfaces:**
- Consumes: Task 1の共通descriptionと本文
- Produces: 既存と同じfrontmatter・本文を持つClaude/Kiro Markdown

- [ ] **Step 1: 各Markdownのfrontmatterを維持してテンプレート化する**

各ファイルのYAML frontmatterは `description` だけを共通テンプレート参照へ変え、本文も共通テンプレート参照へ置き換えて `.tmpl` 接尾辞を付ける。`code-reviewer` の参照は次のとおり。

```gotemplate
description: {{ includeTemplate "agents/description/code-reviewer.txt" . | trim }}
{{ template "agents/body/code-reviewer.md" . }}
```

上記は `code-reviewer` の実例である。ほかの5件はAgent Manifestの `Name` をそのままテンプレート名に使う。

- [ ] **Step 2: 生成結果が変更前と一致することを確認する**

Run for each agent and platform:

```bash
chezmoi --no-pager execute-template < "dot_claude/agents/${agent_name}.md.tmpl" | cmp - <(git -P show "HEAD:dot_claude/agents/${agent_name}.md")
chezmoi --no-pager execute-template < "dot_kiro/agents/${agent_name}.md.tmpl" | cmp - <(git -P show "HEAD:dot_kiro/agents/${agent_name}.md")
```

Expected: 6件×2形式がすべて exit 0。

### Task 3: Kiro JSONをテンプレート化する

**Files:**
- Rename and modify: 対象6件の `dot_kiro/agents/*.json` を同名の `*.json.tmpl` へ変更

**Interfaces:**
- Consumes: Task 1の共通descriptionと本文
- Produces: 既存metadata・権限を維持し、共通descriptionと本文を持つKiro JSON

- [ ] **Step 1: JSONの `description` と `prompt` 以外を保存する**

各既存JSONの `description` と `prompt` を除いた正規化結果を比較基準として `/tmp/kiro-${agent_name}-metadata.json` に保存する。

```bash
jq -S 'del(.description, .prompt)' "dot_kiro/agents/${agent_name}.json" > "/tmp/kiro-${agent_name}-metadata.json"
```

- [ ] **Step 2: JSONテンプレートを作成する**

既存JSONの `description` と `prompt` を次のGo template式へ置き換え、`.json.tmpl` 接尾辞を付ける。

```gotemplate
{{ includeTemplate "agents/description/code-reviewer.txt" . | trim | toJson }}
{{ includeTemplate "agents/body/code-reviewer.md" . | trim | toJson }}
```

上記は `code-reviewer` の実例である。ほかの5件はAgent Manifestの `Name` をそのままテンプレート名に使う。

- [ ] **Step 3: 生成JSONを検証する**

Run for each agent:

```bash
chezmoi --no-pager execute-template < "dot_kiro/agents/${agent_name}.json.tmpl" > "/tmp/kiro-${agent_name}-rendered.json"
jq -e . "/tmp/kiro-${agent_name}-rendered.json" >/dev/null
jq -S 'del(.description, .prompt)' "/tmp/kiro-${agent_name}-rendered.json" | cmp - "/tmp/kiro-${agent_name}-metadata.json"
test "$(jq -r '.description' "/tmp/kiro-${agent_name}-rendered.json")" = "$(cat ".chezmoitemplates/agents/description/${agent_name}.txt")"
jq -r '.prompt' "/tmp/kiro-${agent_name}-rendered.json" | cmp - <(sed '${/^$/d;}' ".chezmoitemplates/agents/body/${agent_name}.md")
```

Expected: JSON構文、metadata、prompt本文が6件すべて一致する。

### Task 4: Codex custom agentを追加する

**Files:**
- Create: `dot_codex/agents/build-error-resolver.toml.tmpl`
- Create: `dot_codex/agents/code-reviewer.toml.tmpl`
- Create: `dot_codex/agents/doc-updater.toml.tmpl`
- Create: `dot_codex/agents/planner.toml.tmpl`
- Create: `dot_codex/agents/python-reviewer.toml.tmpl`
- Create: `dot_codex/agents/refactor-cleaner.toml.tmpl`

**Interfaces:**
- Consumes: Task 1の共通descriptionと本文
- Produces: `~/.codex/agents/` に展開される6件のcustom agent TOML

- [ ] **Step 1: Codex agentディレクトリが未管理であることを確認する**

Run:

```bash
test -d dot_codex/agents
```

Expected: exit 1。

- [ ] **Step 2: 6件のTOMLテンプレートを作成する**

各ファイルはAgent Manifestの値を使って生成する。`code-reviewer.toml.tmpl` の完全な内容は次のとおり。

```toml
name = "code-reviewer"
description = {{ includeTemplate "agents/description/code-reviewer.txt" . | trim | toJson }}
sandbox_mode = "read-only"
developer_instructions = {{ includeTemplate "agents/body/code-reviewer.md" . | trim | toJson }}
```

ほかの5件も同じ4項目を持ち、Agent Manifestの `Name`、`Description`、`Codex sandbox` を使用する。`developer_instructions` のテンプレート名には同じ `Name` を使用する。

- [ ] **Step 3: TOMLの必須項目と本文を確認する**

Run for each agent:

```bash
chezmoi --no-pager execute-template < "dot_codex/agents/${agent_name}.toml.tmpl" > "/tmp/codex-${agent_name}.toml"
grep -Fqx "name = \"${agent_name}\"" "/tmp/codex-${agent_name}.toml"
grep -Fq 'description = ' "/tmp/codex-${agent_name}.toml"
grep -Fq 'sandbox_mode = ' "/tmp/codex-${agent_name}.toml"
grep -Fq 'developer_instructions = ' "/tmp/codex-${agent_name}.toml"
```

Expected: 6件すべて exit 0。

### Task 5: 全形式を適用・検証してレビューする

**Files:**
- Apply: `~/.claude/agents/` 対象6件
- Apply: `~/.kiro/agents/` 対象12件
- Apply: `~/.codex/agents/` 対象6件

**Interfaces:**
- Consumes: Task 1からTask 4の生成テンプレート
- Produces: 3プラットフォームで利用可能な6 agent

- [ ] **Step 1: 対象agentディレクトリをchezmoiで反映する**

```bash
chezmoi --no-pager apply /Users/shibtats/.claude/agents /Users/shibtats/.kiro/agents /Users/shibtats/.codex/agents
```

- [ ] **Step 2: 展開されたファイル数を確認する**

```bash
find /Users/shibtats/.codex/agents -maxdepth 1 -name '*.toml' | wc -l
```

Expected: 6。

- [ ] **Step 3: Codexが設定を読み込めることを確認する**

```bash
codex features list | cat
```

Expected: 設定エラーなく終了し、`multi_agent` が `true`。

- [ ] **Step 4: 全差分を検証する**

```bash
git -P diff --check
git -P status --short
git -P diff --stat | cat
```

Expected: 設計書、計画書、共通description 6件、共通本文6件、Claude/Kiroテンプレート化、Codex TOML 6件だけが差分に含まれる。

- [ ] **Step 5: ユーザーレビューを受ける**

差分と検証結果を提示し、承認を待つ。承認前にコミットしない。

- [ ] **Step 6: レビュー承認後にコミットする**

```bash
git -P add -- .kiro/specs/codex-shared-agents .chezmoitemplates/agents dot_claude/agents dot_kiro/agents dot_codex/agents
git -P commit -m "feat(agents): share agent prompts across clients"
```

新しいCodexセッションを開始し、`code-reviewer` subagentを明示して最終確認する。
