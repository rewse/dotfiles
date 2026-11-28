# PR の squash merge 統一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** PR のマージ方式を原則 squash に統一し、ルール 3 か所と GitHub のリポジトリ設定に反映する。

**Architecture:** 原則は common-standards、rewse リポジトリの設定既定値は `git/AGENTS.md`、teslamate の例外は teslamate の AGENTS.md に書く。既定値は `gh api -X PATCH` で 17 リポジトリと teslamate に入れる。

**Tech Stack:** Markdown のルールファイル、chezmoi、`gh api`

**Spec:** `docs/superpowers/archive/specs/2026-11-28-pr-squash-merge-design.md`

## Global Constraints

- ルールファイルは英語、Rule Authoring Standards に従い指示を先に書き、段落は折り返さない。
- 17 リポジトリの設定: `allow_merge_commit=false`、`allow_rebase_merge=false`、`allow_squash_merge=true`、`squash_merge_commit_title=PR_TITLE`、`squash_merge_commit_message=BLANK`。
- teslamate の設定: `allow_merge_commit=true`、`allow_rebase_merge=false`、`allow_squash_merge=true`、`squash_merge_commit_title=PR_TITLE`、`squash_merge_commit_message=BLANK`。
- teslamate は public なので、その AGENTS.md は `~/git/AGENTS.md` や common-standards に触れない。
- GitHub の設定変更と push は、実行直前にユーザーの確認を取る。
- dotfiles のコミット種別: `git/AGENTS.md` と `docs/` は `docs:`、`.chezmoitemplates/rules/` は `feat:`。

## Review Focus

- squash が無効なリポジトリはない前提で PATCH するが、`allow_squash_merge=true` を同じ呼び出しで入れるので、3 つとも無効になる状態は起きない（GitHub は全無効を 422 で拒否する）。Task 3 の確認で 18 リポジトリすべての値を読む。
- archive されたリポジトリや fork に誤って PATCH しない。Task 3 は対象を spec の一覧で固定し、`gh repo list` の結果から作らない。
- teslamate の upgrade PR に squash を押す誤り。Task 4 の文面が「upstream リリースを取り込む PR」を判定できる形になっていることをレビューで確かめる。
- 新規リポジトリで設定が漏れる。Task 2 の文面に「作成時に入れる」を含める。
- common-standards の例外文言が GitHub 以外（GitLab のリポジトリ）でも矛盾しない。Task 1 の文面はホストを限定しない。

---

### Task 1: common-standards に Pull Request Standards を足す

**Files:**
- Modify: `.chezmoitemplates/rules/common-standards.md`（`## Commit Message Standards` の節の直後）

- [ ] **Step 1: 節を追加する**

`## Pull Request Standards` を `## Project Instruction File Standards` の前に入れ、次の 2 点を書く: PR は squash merge で取り込み、リポジトリの `AGENTS.md` に別のルールがあればそれに従う。PR タイトルが squash commit の件名になるので、PR タイトルも Conventional Commits に従う。

- [ ] **Step 2: 配布結果を確かめる**

Run: `chezmoi --no-pager apply --no-tty ~/.agents/rules/common-standards.md && rg -n 'Pull Request Standards' ~/.agents/rules/common-standards.md`
Expected: 見出しが 1 行ヒットする。

- [ ] **Step 3: Commit**

```bash
git add .chezmoitemplates/rules/common-standards.md
git commit -m "feat(rules): merge pull requests by squash unless the repository says otherwise"
```

### Task 2: `git/AGENTS.md` にマージ設定の既定値を足す

**Files:**
- Modify: `git/AGENTS.md`（`# GitHub Configuration` の箇条書き、Dependabot alerts の項目の直後）

- [ ] **Step 1: 項目を追加する**

「squash merge だけを許可し、squash commit の件名を PR タイトル、本文を空にする。リポジトリ作成時にも設定する」と書き、Global Constraints の 5 つの値と、設定する `gh api -X PATCH repos/rewse/<repo>` の例を入れる。本文を空にする理由（コミット一覧や Dependabot の本文で履歴が埋まる）を 1 文添える。

- [ ] **Step 2: `~/git/AGENTS.md` へ配る**

Run: `chezmoi --no-pager execute-template < run_after_sync-git-agents-md.sh.tmpl | sh && diff git/AGENTS.md ~/git/AGENTS.md`
Expected: diff の出力なし。

- [ ] **Step 3: Commit**

```bash
git add git/AGENTS.md
git commit -m "docs: allow only squash merges in rewse repositories"
```

### Task 3: GitHub のリポジトリ設定を変える

**Files:** なし（GitHub への書き込み）

- [ ] **Step 1: ユーザーの確認を取る**

対象 18 リポジトリと値を示し、実行の承認を得る。

- [ ] **Step 2: 17 リポジトリに既定値を入れる**

spec の一覧に対し `gh api -X PATCH repos/rewse/$r -F allow_merge_commit=false -F allow_rebase_merge=false -F allow_squash_merge=true -f squash_merge_commit_title=PR_TITLE -f squash_merge_commit_message=BLANK --silent` を実行する。

- [ ] **Step 3: teslamate に例外の値を入れる**

同じコマンドで `allow_merge_commit=true` にする。

- [ ] **Step 4: 値を確かめる**

Run: 18 リポジトリについて `gh api repos/rewse/$r --jq '[.name,.allow_merge_commit,.allow_rebase_merge,.allow_squash_merge,.squash_merge_commit_title,.squash_merge_commit_message]|@tsv'`
Expected: 17 行が `false false true PR_TITLE BLANK`、teslamate が `true false true PR_TITLE BLANK`。

### Task 4: teslamate の AGENTS.md に例外を書く

**Files:**
- Modify: `~/git/teslamate/AGENTS.md`（`## Dependencies` の後に `## Pull Requests` を追加）

- [ ] **Step 1: ブランチを切って節を追加する**

`git -C ~/git/teslamate switch -c docs/pull-request-merge-method` の後、upstream リリースを取り込む upgrade PR（`teslamate-fork-upgrade` skill が作る PR）は merge commit で、それ以外は squash で取り込むと書く。squash や rebase は upgrade の `-s ours` マージを消し、skill が fork の差分を見分けられなくなる、と理由を 1 文添える。

- [ ] **Step 2: リポジトリの検証を通す**

Run: `npx -y prettier --check AGENTS.md`（teslamate の Markdown は prettier 整形。表があるので整形差分に注意）
Expected: 差分なし。prettier が使われていなければ省略し、その旨を報告する。

- [ ] **Step 3: Commit、push、PR**

push と PR 作成の前にユーザーの確認を取る。

```bash
git -C ~/git/teslamate add AGENTS.md
git -C ~/git/teslamate commit -m "docs: merge upgrade pull requests with a merge commit and others by squash"
git -C ~/git/teslamate push -u origin docs/pull-request-merge-method
gh pr create -R rewse/teslamate --fill
```

マージは squash で行う（この PR は upgrade PR ではない）。

### Task 5: spec と plan を archive して dotfiles を push する

**Files:**
- Move: `docs/superpowers/specs/2026-11-28-pr-squash-merge-design.md` → `docs/superpowers/archive/specs/`
- Move: `docs/superpowers/plans/2026-11-28-pr-squash-merge.md` → `docs/superpowers/archive/plans/`

- [ ] **Step 1: 移動して commit**

```bash
git add docs/superpowers/specs/2026-11-28-pr-squash-merge-design.md docs/superpowers/plans/2026-11-28-pr-squash-merge.md
git mv docs/superpowers/specs/2026-11-28-pr-squash-merge-design.md docs/superpowers/archive/specs/
git mv docs/superpowers/plans/2026-11-28-pr-squash-merge.md docs/superpowers/archive/plans/
git commit -m "docs: archive the squash merge spec and plan"
```

- [ ] **Step 2: 検証して push**

Run: `uvx pre-commit run --all-files && uv run python -m unittest discover -s tests`
Expected: すべて Passed / OK。push の前にユーザーの確認を取る。
