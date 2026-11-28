# 複数コミットの作業をブランチで進めるルール Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 2 コミット以上の作業をブランチと squash PR で取り込むルールを common-standards に足す。

**Architecture:** Pull Request Standards の節に 1 段落足すだけ。作業は worktree `.worktrees/feat-multi-commit-branches`（ブランチ `feat/multi-commit-branches`）で行い、PR を squash merge する。

**Tech Stack:** Markdown のルールファイル、chezmoi、`gh`

**Spec:** `docs/superpowers/archive/specs/2026-11-28-multi-commit-branches-design.md`

## Global Constraints

- ルールは英語、指示を先に書き、段落を折り返さない。
- 既存の「リポジトリの `AGENTS.md` に別のルールがあればそれに従う」がこのルールにもかかる位置に書く。
- push、PR 作成、マージの前にユーザーの確認を取る。

## Review Focus

- 1 コミットのつもりで始めた作業が 2 コミット目を要したとき、push 前にブランチへ移すと文面から読めること。
- spec と plan を書く作業が、spec を書く前からブランチで進めるものと読めること。
- 文面が GitHub 以外のホストでも矛盾しないこと（「pull request」を一般語として使う）。
- 既存の「Merge pull requests by squash」の段落と重複せず、1 つの節として通して読めること。
- ansible-playbooks の「修正は main に直接 push してよい」という運用と矛盾しないこと（1 コミットの修正は従来どおり直接 push）。

---

### Task 1: Pull Request Standards にルールを足す

**Files:**
- Modify: `.chezmoitemplates/rules/common-standards.md`（`## Pull Request Standards` の段落の前）

- [ ] **Step 1: 段落を追加する**

節の先頭に、spec の「決めたこと」2 項目を 1 段落で書く: 2 コミット以上になる作業はブランチか worktree で進め PR で取り込む。デフォルトブランチへ直接 push するのは 1 コミットの変更だけ。spec と plan のある作業は spec を書く前にブランチを切る。途中で 2 コミット目が要るとわかったら push 前にブランチへ移す。既存の squash の段落はその後に残す。

- [ ] **Step 2: 配布結果を確かめる**

Run: worktree で `chezmoi --no-pager --source . execute-template < .chezmoitemplates/rules/common-standards.md | rg -n -A4 '## Pull Request Standards'`
Expected: 新しい段落と squash の段落が続けて出る。

- [ ] **Step 3: Commit**

```bash
git add .chezmoitemplates/rules/common-standards.md docs/superpowers/specs/2026-11-28-multi-commit-branches-design.md docs/superpowers/plans/2026-11-28-multi-commit-branches.md
git commit -m "feat(rules): take multi-commit work through a branch and a squash merge"
```

### Task 2: archive、検証、PR

- [ ] **Step 1: spec と plan を archive へ移して commit**

```bash
git mv docs/superpowers/specs/2026-11-28-multi-commit-branches-design.md docs/superpowers/archive/specs/
git mv docs/superpowers/plans/2026-11-28-multi-commit-branches.md docs/superpowers/archive/plans/
git commit -m "docs: archive the multi-commit branch spec and plan"
```

- [ ] **Step 2: 検証**

Run: `uvx pre-commit run --all-files && uv run python -m unittest discover -s tests`
Expected: すべて Passed / OK。

- [ ] **Step 3: push、PR、マージ（ユーザーの確認後）**

`git push -u origin feat/multi-commit-branches`、`gh pr create --fill-first`、CI 通過後に `gh pr merge --squash`。マージ後に main の clone で `git pull` と `chezmoi apply`、worktree とローカルブランチを削除する。
