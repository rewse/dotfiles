# プロジェクト指示ファイルのフォールバック実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 各エージェントのネイティブなプロジェクト指示がない場合に、ほかのエージェント向け指示をフォールバックとして読む共通ルールを配布する。

**Architecture:** 互換ルールの本文を `.chezmoitemplates/rules/` に置き、`~/.agents/rules/` 用テンプレートから展開する。Codex は既存 glob で本文を取り込み、Claude Code と Kiro は `~/.agents/rules/` へのシンボリックリンクで同じ本文を参照する。

**Tech Stack:** chezmoi、Go template、Markdown

## Global Constraints

- 対象はプロジェクトルートの指示だけとし、ユーザールートの `~/.codex`、`~/.claude`、`~/.kiro` には適用しない。
- ネイティブ指示が存在する場合は代替指示を読まない。
- ネイティブ指示が存在せず、複数の代替指示が存在する場合はすべて読む。
- 存在しない代替指示は無視する。
- 互換ルール本文は英語で記述する。

---

### Task 1: 共通フォールバックルールを作成する

**Files:**
- Create: `.chezmoitemplates/rules/project-instruction-fallbacks.md`
- Create: `dot_agents/rules/project-instruction-fallbacks.md.tmpl`

**Interfaces:**
- Consumes: chezmoi の `template "rules/project-instruction-fallbacks.md"` 関数
- Produces: Codex の生成済み `AGENTS.md` と `~/.agents/rules/project-instruction-fallbacks.md` に入る共通ルール

- [ ] **Step 1: 共通ルールが存在しないことを確認する**

Run:

```bash
test -f .chezmoitemplates/rules/project-instruction-fallbacks.md
```

Expected: exit 1。

- [ ] **Step 2: 共通ルール本文を作成する**

`.chezmoitemplates/rules/project-instruction-fallbacks.md` を次の内容にする。

```markdown
# Project Instruction Fallbacks

Apply these fallbacks only to instruction sources in the project root. Do not apply them to user-level configuration under `~/.codex`, `~/.claude`, or `~/.kiro`.

Use only the native project instruction source when it exists:

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Kiro: instruction files under `.kiro/steering/`

When the native project instruction source does not exist, use every fallback source that exists:

- Codex: read `CLAUDE.md` and every instruction file under `.kiro/steering/`, and treat them as `AGENTS.md` instructions.
- Claude Code: read `AGENTS.md` and every instruction file under `.kiro/steering/`, and treat them as `CLAUDE.md` instructions.
- Kiro: read `CLAUDE.md` and treat it as `AGENTS.md` instructions.

Ignore fallback sources that do not exist. If multiple fallback sources exist, read all of them.
```

- [ ] **Step 3: `~/.agents/rules` 用テンプレートを作成する**

`dot_agents/rules/project-instruction-fallbacks.md.tmpl` を次の内容にする。

```gotemplate
---
inclusion: always
---

{{ template "rules/project-instruction-fallbacks.md" . }}
```

- [ ] **Step 4: Codex の生成結果を確認する**

Run:

```bash
chezmoi --no-pager execute-template < dot_codex/AGENTS.md.tmpl | grep -Fqx '# Project Instruction Fallbacks'
```

Expected: exit 0。

- [ ] **Step 5: 共通ルールの条件を確認する**

Run:

```bash
grep -Fq 'only to instruction sources in the project root' .chezmoitemplates/rules/project-instruction-fallbacks.md
grep -Fq 'Use only the native project instruction source when it exists' .chezmoitemplates/rules/project-instruction-fallbacks.md
grep -Fq 'If multiple fallback sources exist, read all of them' .chezmoitemplates/rules/project-instruction-fallbacks.md
```

Expected: exit 0。

- [ ] **Step 6: `~/.agents/rules` 用の生成結果を確認する**

Run:

```bash
chezmoi --no-pager execute-template < dot_agents/rules/project-instruction-fallbacks.md.tmpl | grep -Fqx '# Project Instruction Fallbacks'
```

Expected: exit 0。

- [ ] **Step 7: 差分を検証する**

Run:

```bash
git -P diff --check -- .chezmoitemplates/rules/project-instruction-fallbacks.md dot_agents/rules/project-instruction-fallbacks.md.tmpl
git -P diff -- .chezmoitemplates/rules/project-instruction-fallbacks.md dot_agents/rules/project-instruction-fallbacks.md.tmpl | cat
```

Expected: `diff --check` が exit 0。差分は共通ルール本文と展開テンプレートの追加だけである。

- [ ] **Step 8: 共通ルールをコミットする**

```bash
git -P add -- .chezmoitemplates/rules/project-instruction-fallbacks.md dot_agents/rules/project-instruction-fallbacks.md.tmpl
git -P commit -m "feat: add project instruction fallback rules"
```

### Task 2: Claude Code と Kiro へ共通ルールを配布する

**Files:**
- Create: `dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl`
- Create: `dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl`

**Interfaces:**
- Consumes: Task 1 が生成する `~/.agents/rules/project-instruction-fallbacks.md`
- Produces: Claude Code と Kiro が読み込む共通ルールへのシンボリックリンク

- [ ] **Step 1: symlink テンプレートが存在しないことを確認する**

Run:

```bash
test -f dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl
test -f dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl
```

Expected: 最初の `test` が exit 1。

- [ ] **Step 2: Claude Code 用 symlink テンプレートを作成する**

`dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl` を次の内容にする。

```gotemplate
{{ .chezmoi.homeDir }}/.agents/rules/project-instruction-fallbacks.md
```

- [ ] **Step 3: Kiro 用 symlink テンプレートを作成する**

`dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl` を次の内容にする。

```gotemplate
{{ .chezmoi.homeDir }}/.agents/rules/project-instruction-fallbacks.md
```

- [ ] **Step 4: 両方のリンク先を検証する**

Run:

```bash
expected_rule_target="$(chezmoi --no-pager execute-template '{{ .chezmoi.homeDir }}/.agents/rules/project-instruction-fallbacks.md')"
claude_rule_target="$(chezmoi --no-pager execute-template < dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl)"
kiro_rule_target="$(chezmoi --no-pager execute-template < dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl)"
test "$claude_rule_target" = "$expected_rule_target"
test "$kiro_rule_target" = "$expected_rule_target"
```

Expected: exit 0。

- [ ] **Step 5: 差分を検証する**

Run:

```bash
git -P diff --check -- dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl
git -P diff -- dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl | cat
```

Expected: `diff --check` が exit 0。2つのテンプレートは同じ共有ルールを指す。

- [ ] **Step 6: symlink テンプレートをコミットする**

```bash
git -P add -- dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl
git -P commit -m "feat: share project instruction fallbacks with agents"
```

### Task 3: 最終生成結果を確認する

**Files:**
- Verify: `.chezmoitemplates/rules/project-instruction-fallbacks.md`
- Verify: `dot_agents/rules/project-instruction-fallbacks.md.tmpl`
- Verify: `dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl`
- Verify: `dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl`

**Interfaces:**
- Consumes: Task 1 の共通ルールと Task 2 の symlink テンプレート
- Produces: 3エージェントが参照できるプロジェクト指示フォールバックルール

- [ ] **Step 1: 4つの生成・参照経路をまとめて検証する**

Run:

```bash
chezmoi --no-pager execute-template < dot_codex/AGENTS.md.tmpl | grep -Fqx '# Project Instruction Fallbacks'
chezmoi --no-pager execute-template < dot_agents/rules/project-instruction-fallbacks.md.tmpl | grep -Fqx '# Project Instruction Fallbacks'
chezmoi --no-pager execute-template < dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl | grep -Fqx "$(chezmoi --no-pager execute-template '{{ .chezmoi.homeDir }}/.agents/rules/project-instruction-fallbacks.md')"
chezmoi --no-pager execute-template < dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl | grep -Fqx "$(chezmoi --no-pager execute-template '{{ .chezmoi.homeDir }}/.agents/rules/project-instruction-fallbacks.md')"
```

Expected: exit 0。

- [ ] **Step 2: 作業ツリーとコミットを確認する**

Run:

```bash
git -P status --short
git -P log -3 --oneline | cat
```

Expected: `status --short` は空。直近2コミットは `feat: share project instruction fallbacks with agents` と `feat: add project instruction fallback rules` である。
