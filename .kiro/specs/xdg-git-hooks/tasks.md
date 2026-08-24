# Git hook の XDG 移行実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** グローバル Git hook を `~/.config/git/hooks` へ移し、ホスト `7cf34ded5d65` 以外だけユーザー Git config で有効にする。

**Architecture:** chezmoi の hook ソースを `dot_config/git/hooks/` へ移し、`dot_config/git/config.tmpl` の `hooksPath` をホスト条件で出力する。新 hook の内容と実行権限を確認した後、旧 `~/.git-hooks` を今回の作業で直接削除する。

**Tech Stack:** chezmoi、Git config、Go template、Bash

## Global Constraints

- hook の配置先は `~/.config/git/hooks/pre-commit` とする。
- ホスト `7cf34ded5d65` では `core.hooksPath` を出力しない。
- それ以外のホストでは `core.hooksPath` を `~/.config/git/hooks` の絶対パスにする。
- pre-commit hook の内容と実行権限を変更しない。
- 新旧 hook の一致を確認するまで旧 hook を削除しない。
- レビュー承認前にコミットしない。

---

### Task 1: hook ソースを XDG 配下へ移す

**Files:**
- Delete: `dot_git-hooks/executable_pre-commit`
- Create: `dot_config/git/hooks/executable_pre-commit`

**Interfaces:**
- Consumes: 既存のグローバル pre-commit hook
- Produces: chezmoi が `~/.config/git/hooks/pre-commit` へ配置する実行可能 hook

- [ ] **Step 1: XDG 配下の hook ソースが存在しないことを確認する**

Run:

```bash
test -f dot_config/git/hooks/executable_pre-commit
```

Expected: exit 1。

- [ ] **Step 2: hook ソースを移動する**

`dot_git-hooks/executable_pre-commit` を内容を変えずに `dot_config/git/hooks/executable_pre-commit` へ移す。

- [ ] **Step 3: Git が rename として認識することを確認する**

Run:

```bash
git -P diff --summary | cat
git -P diff --no-renames -- dot_git-hooks/executable_pre-commit dot_config/git/hooks/executable_pre-commit | cat
```

Expected: summary は100% renameを示し、削除側と追加側の内容が同一である。

- [ ] **Step 4: chezmoi の新しい管理先を確認する**

Run:

```bash
chezmoi --no-pager managed | grep -Fqx '.config/git/hooks/pre-commit'
```

Expected: exit 0。

### Task 2: `hooksPath` をホスト条件付きにする

**Files:**
- Modify: `dot_config/git/config.tmpl:14-19`

**Interfaces:**
- Consumes: `.chezmoi.hostname` と `.chezmoi.homeDir`
- Produces: 対象ホストでは `hooksPath` なし、対象外ホストでは XDG hook パスを持つ Git config

- [ ] **Step 1: 現在の `hooksPath` が無条件かつ旧パスであることを確認する**

Run:

```bash
grep -Fqx '    hooksPath = {{ .chezmoi.homeDir }}/.git-hooks' dot_config/git/config.tmpl
```

Expected: exit 0。

- [ ] **Step 2: `[core]` の `hooksPath` を条件化する**

`dot_config/git/config.tmpl` の `[core]` を次の内容にする。

```gotemplate
[core]
    editor = vim
    pager = bat
{{ if ne .chezmoi.hostname "7cf34ded5d65" -}}
    hooksPath = {{ .chezmoi.homeDir }}/.config/git/hooks
{{ end -}}
[color]
```

- [ ] **Step 3: 現在の対象ホストでは `hooksPath` が出力されないことを確認する**

Run:

```bash
sed -n '/^\[core\]/,/^\[color\]/p' dot_config/git/config.tmpl | chezmoi --no-pager execute-template | grep -F 'hooksPath'
```

Expected: exit 1。

- [ ] **Step 4: 対象外ホストの条件が XDG パスを出力することを確認する**

Run:

```bash
chezmoi --no-pager execute-template '{{ if ne "other-host" "7cf34ded5d65" }}hooksPath = {{ .chezmoi.homeDir }}/.config/git/hooks{{ end }}' | grep -Fqx 'hooksPath = /Users/shibtats/.config/git/hooks'
```

Expected: exit 0。

- [ ] **Step 5: テンプレート差分を検証する**

Run:

```bash
git -P diff --check -- dot_config/git/config.tmpl
git -P diff -- dot_config/git/config.tmpl | cat
```

Expected: `hooksPath` のホスト条件と XDG パスへの変更だけである。

### Task 3: 新 hook を反映して旧パスを削除する

**Files:**
- Apply: `~/.config/git/hooks/pre-commit`
- Delete: `~/.git-hooks/pre-commit`
- Delete if empty: `~/.git-hooks`

**Interfaces:**
- Consumes: Task 1 の XDG hook
- Produces: XDG 配下の実行可能 hook と、旧パスを持たないホームディレクトリ

- [ ] **Step 1: 新 hook だけを chezmoi で反映する**

Run:

```bash
chezmoi --no-pager apply /Users/shibtats/.config/git/hooks/pre-commit
```

Expected: exit 0。

- [ ] **Step 2: 新旧 hook の内容と実行権限を確認する**

Run:

```bash
test -x /Users/shibtats/.config/git/hooks/pre-commit
cmp /Users/shibtats/.git-hooks/pre-commit /Users/shibtats/.config/git/hooks/pre-commit
```

Expected: exit 0。

- [ ] **Step 3: 旧 hook を直接削除する**

Run:

```bash
rm /Users/shibtats/.git-hooks/pre-commit
rmdir /Users/shibtats/.git-hooks
```

Expected: exit 0。旧ディレクトリに想定外ファイルがあれば `rmdir` は失敗し、その内容を報告する。

- [ ] **Step 4: 新旧パスの最終状態を確認する**

Run:

```bash
test -x /Users/shibtats/.config/git/hooks/pre-commit
test ! -e /Users/shibtats/.git-hooks/pre-commit
test ! -d /Users/shibtats/.git-hooks
```

Expected: exit 0。

### Task 4: 全差分をレビューする

**Files:**
- Verify: `.kiro/specs/xdg-git-hooks/design.md`
- Verify: `.kiro/specs/xdg-git-hooks/tasks.md`
- Verify: `dot_config/git/config.tmpl`
- Verify: `dot_config/git/hooks/executable_pre-commit`
- Verify deleted: `dot_git-hooks/executable_pre-commit`

**Interfaces:**
- Consumes: Task 1からTask 3の変更
- Produces: コミット可能なレビュー済み差分

- [ ] **Step 1: 全差分を検証する**

Run:

```bash
git -P diff --check
git -P status --short
git -P diff --stat | cat
git -P diff -- dot_config/git/config.tmpl dot_git-hooks/executable_pre-commit dot_config/git/hooks/executable_pre-commit | cat
```

Expected: 設計書、計画書、Git config、hook の移動だけが差分に含まれる。

- [ ] **Step 2: ユーザーレビューを受ける**

差分と検証結果を提示し、承認を待つ。承認前にコミットしない。

- [ ] **Step 3: レビュー承認後にコミットする**

```bash
git -P add -- .kiro/specs/xdg-git-hooks/design.md .kiro/specs/xdg-git-hooks/tasks.md dot_config/git/config.tmpl dot_config/git/hooks/executable_pre-commit dot_git-hooks/executable_pre-commit
git -P commit -m "fix(git): move global hooks to XDG config"
```
