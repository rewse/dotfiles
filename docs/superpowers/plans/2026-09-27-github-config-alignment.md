# GitHub 設定の統一 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `rewse/*` の 9 リポジトリの `.github` を共通の方針にそろえ、方針を `~/git/AGENTS.md` に書いて chezmoi で管理する。

**Architecture:** リポジトリごとに 1 タスク、1 コミットとする。各タスクは、変更前に共通チェックが失敗し、変更後に通ることで確かめる。push は最後のタスクでまとめて行う。

**Tech Stack:** GitHub Actions、Dependabot、chezmoi、actionlint（`uvx --from actionlint-py actionlint`）、zizmor（`uvx zizmor`）、check-jsonschema（`uvx check-jsonschema`）

**Spec:** `docs/superpowers/specs/2026-09-27-github-config-alignment-design.md`

## Global Constraints

- `uses:` はすべて `<owner>/<repo>[/<path>]@<40 桁の SHA>  # vX.Y.Z` の形にする（SHA の後ろは空白 2 つ）。値は下の表のものを使う
- dependabot.yml の各項目: `directory: /`、`schedule.interval: weekly`、`cooldown.default-days: 4`、`groups.<ecosystem>.patterns: ["*"]`
- トップレベルの `permissions` は `contents: read` だけ。ほかの権限はジョブに付ける
- `actions/checkout` にはすべて `persist-credentials: false` を付ける
- すべてのジョブに `name` を付ける
- Node.js は `'24'`。Python は `python-version-file: .python-version`
- cron の値は今のものを変えない
- `security-scan.yml` は `dependency-scan.yml`（`name: Dependency Scan`）に改名する。`release.yml` は改名しない
- `.github/cliff.toml` はリポジトリの直下の `cliff.toml` に移し、git-cliff-action の `config:` を消す
- コミットメッセージは Conventional Commits の `ci:` か `docs:`。1 リポジトリにつき 1 コミット
- 作業の前に各リポジトリで `git pull --ff-only` を行う
- push は Task 11 でユーザーの確認を取ってから行う

固定する Action（公開から 4 日以上たった最新のリリース。2026-09-27 に解決した値）:

| Action | 版 | SHA |
|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| actions/setup-node | v7.0.0 | `820762786026740c76f36085b0efc47a31fe5020` |
| actions/setup-python | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| astral-sh/setup-uv | v10.2.0 | `c18668ad3cf93ea998bef934396af7bb5c839dc7` |
| gitleaks/gitleaks-action | v3.0.0 | `e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e` |
| google/osv-scanner-action（`.github/workflows/osv-scanner-reusable.yml`） | v2.6.0 | `a345acffa64b0eaede81a3d9aae6141214d9c8fc` |
| orhun/git-cliff-action | v4.9.1 | `a9a95522b26fe6403f7bb24031f21fb573d0f5ff` |
| pypa/gh-action-pypi-publish | v1.14.2 | `dc37677b2e1c63e2034f94d8a5b11f265b73ba33` |
| trufflesecurity/trufflehog | v3.97.6 | `64d939a56362f519781c53ea09b27f8d1dc0140a` |

## 共通チェック

各タスクでは、リポジトリの直下で次を実行する。どれも出力がなく、終了コードが 0 なら合格とする。

```bash
# C1: 構文と式
uvx --from actionlint-py actionlint
# C2: セキュリティ上の指摘（unpinned-uses, artipacked, excessive-permissions, template-injection, cache-poisoning, dependabot-cooldown など）
uvx zizmor --offline --min-severity low .github
# C3: SHA 固定でない uses: が残っていない
rg -n 'uses:' .github/workflows | rg -v '@[0-9a-f]{40}  # v[0-9]'
# C4: dependabot.yml のスキーマ
uvx check-jsonschema --builtin-schema vendor.dependabot .github/dependabot.yml
```

zizmor で出そうな指摘と、その直し方は次のとおり。

- `template-injection`: `run:` の中の `${{ ... }}`（`steps.changelog.outputs.content`、`github.ref_name`）を `env:` に移し、`"$VAR"` で参照する
- `cache-poisoning`: release.yml の `astral-sh/setup-uv` に `enable-cache: false` を付ける
- `excessive-permissions`: release.yml の `contents: write` と `id-token: write` をジョブに移す

C2 の指摘で理由があって残すものは、該当する行に `# zizmor: ignore[<audit>]` と理由のコメントを付ける。

## 共通のファイル

**gitleaks.yml**（全リポジトリで同じ。cron も全リポジトリで今の値と同じ）:

```yaml
name: Gitleaks

on:
  push:
  pull_request:
  schedule:
    - cron: "37 19 * * 3"  # Every Thursday at 04:37 JST (19:37 UTC Wed)

permissions:
  contents: read

jobs:
  scan:
    name: Secret Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          fetch-depth: 0
          persist-credentials: false

      - uses: gitleaks/gitleaks-action@e0c47f4f8be36e29cdc102c57e68cb5cbf0e8d1e  # v3.0.0
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**trufflehog.yml**: 今のファイルの `uses:` を上の表の値に替え、checkout に `persist-credentials: false` を足す。`extra_args` はリポジトリごとに次のようにする。

- lob を除外する（chezmoi、enecoq、stock）: `--exclude-detectors=lob --results=verified,unknown`
- それ以外: `--results=verified,unknown`

**dependency-scan.yml**: 今の `security-scan.yml` を `git mv` で改名し、次の形にする。`<SETUP>` と `<INSTALL>` 以降のステップは、リポジトリごとの今の内容を残す。

```yaml
name: Dependency Scan

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  schedule:
    - cron: "<今の値>"  # <今のコメント>
  workflow_dispatch:

permissions:
  contents: read

jobs:
  safe-chain:
    name: Aikido Safe Chain Scan
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false
      # <SETUP>: npm のリポジトリは setup-node（node-version: '24'）と `npm install -g npm@latest`
      #          uv のリポジトリは setup-python（python-version-file: .python-version）と setup-uv
      # <INSTALL>: Safe Chain の導入と、今の install、build、test のステップ

  osv-scan:
    name: OSV-Scanner
    permissions:
      actions: read
      contents: read
      security-events: write
    uses: google/osv-scanner-action/.github/workflows/osv-scanner-reusable.yml@a345acffa64b0eaede81a3d9aae6141214d9c8fc  # v2.6.0
```

osv-scan の `permissions` は、reusable workflow の側が要求する権限と同じにする。呼び出し側がこれより少ないと、`upload-sarif: false` でもワークフローが起動しない。

---

### Task 0: ansible-playbooks の未コミットの変更を扱う

**Files:** なし

- [ ] **Step 1: 状態を確かめる**

Run: `git -C ~/git/ansible-playbooks -P status --short && git -C ~/git/ansible-playbooks -P diff`
Expected: `roles/darwin/tasks/main.yml` の 1 行の変更だけ

- [ ] **Step 2: STOP してユーザーに扱い（コミット、stash、そのまま残して後で pull）を聞く**

答えに従ったあとで `git pull --ff-only` が成功し、`git -P log -1 --oneline` が `ce5b262c` 以降になること。

### Task 1: `~/git/AGENTS.md` の方針と chezmoi での管理

**Files:**
- Modify: `~/git/AGENTS.md`（末尾に節を足す）
- Create: `chezmoi/git/AGENTS.md`（`chezmoi add` で作る）
- Modify: `chezmoi/.chezmoiignore`（darwin 以外のブロック）

- [ ] **Step 1: 管理されていないことを確かめる**

Run: `chezmoi --no-pager source-path ~/git/AGENTS.md`
Expected: `not managed`

- [ ] **Step 2: `~/git/AGENTS.md` の末尾に、spec の「追記する節」のコードブロックを一字一句そのまま足す**

- [ ] **Step 3: `chezmoi add ~/git/AGENTS.md` を実行し、`.chezmoiignore` の `{{- else }}` から次の `{{- end }}` までのブロックに、アルファベット順で `git` の行を足す**

- [ ] **Step 4: 確かめる**

Run: `chezmoi --no-pager source-path ~/git/AGENTS.md && chezmoi --no-pager diff ~/git/AGENTS.md && awk '/else/,/end/' ~/git/chezmoi/.chezmoiignore | rg -x 'git'`
Expected: `…/chezmoi/git/AGENTS.md` が出て、diff は空で、`git` が 1 行出る

- [ ] **Step 5: Commit**

```bash
git -C ~/git/chezmoi add git/AGENTS.md .chezmoiignore
git -C ~/git/chezmoi commit -m "docs: manage ~/git/AGENTS.md with GitHub configuration policy"
```

`.chezmoitemplates/rules/common-standards.md` のユーザーの未コミットの変更は含めない。

### Task 2: chezmoi（rewse/dotfiles）

**Files:**
- Create: `chezmoi/.github/dependabot.yml`（github-actions）
- Modify: `chezmoi/.github/workflows/gitleaks.yml`、`chezmoi/.github/workflows/trufflehog.yml`
- Delete: `chezmoi/.trufflehog-exclude-paths.txt`

- [ ] **Step 1: 共通チェックが失敗することを確かめる**

Run: C3 と C4
Expected: C3 は `@v6` と `@main` の行を出し、C4 はファイルがなくて失敗する

- [ ] **Step 2: dependabot.yml を作り、gitleaks.yml を共通のファイルに替え、trufflehog.yml を lob 除外の形にする（`--exclude-paths=…` を消す）。`git rm .trufflehog-exclude-paths.txt` を実行する**

- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**

- [ ] **Step 4: Commit**

```bash
git -C ~/git/chezmoi add -A .github .trufflehog-exclude-paths.txt
git -C ~/git/chezmoi commit -m "ci: pin actions to SHAs and add Dependabot"
```

### Task 3: ansible-playbooks

**Files:**
- Modify: `.github/dependabot.yml`（両方の項目に `groups` を足す。今のコメントは残す）
- Modify: `.github/workflows/ansible-lint.yml`（checkout に `persist-credentials: false`）
- Modify: `.github/workflows/gitleaks.yml`、`.github/workflows/trufflehog.yml`

- [ ] **Step 1: C3 が `@v6` と `@main` の行を出すことを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: Commit** — `ci: group Dependabot updates and pin all actions to SHAs`

### Task 4: mac-power-monitor-mqtt

**Files:** Create `.github/dependabot.yml`（github-actions）。Modify `gitleaks.yml`、`trufflehog.yml`

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: Commit** — `ci: pin actions to SHAs and add Dependabot`

### Task 5: rewse-blog

**Files:** Create `.github/dependabot.yml`（github-actions、docker）。Modify `gitleaks.yml`、`trufflehog.yml`

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: Commit** — `ci: pin actions to SHAs and add Dependabot`

### Task 6: enecoq-data-fetcher

**Files:**
- Create: `.github/dependabot.yml`（github-actions、uv）
- Modify: `gitleaks.yml`、`trufflehog.yml`（lob を除外）
- Rename: `.github/workflows/security-scan.yml` → `.github/workflows/dependency-scan.yml`
- Modify: `.github/workflows/release.yml`
- Rename: `.github/cliff.toml` → `cliff.toml`
- Delete: `.github/RELEASE.md`
- Modify: `AGENTS.md`（25 行目のパスと、19 行目のリリースの段落）

release.yml の変更:
- トップレベルを `contents: read` にし、ジョブに `contents: write` と `id-token: write  # Required for Trusted Publishers` を付ける
- setup-python を `python-version-file: .python-version` にし、setup-uv に `enable-cache: false` を付ける
- git-cliff-action の `config:` を消す
- `gh release create` と `gh release upload` で使う `${{ github.ref_name }}` と `${{ steps.changelog.outputs.content }}` を、`env:` の `TAG_NAME` と `RELEASE_NOTES` に移す

AGENTS.md のリリースの段落の末尾に、次の文を足す: "PyPI Trusted Publishing is bound to `.github/workflows/release.yml` and the `release` environment, so do not rename either."

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: リリースノートが既定の設定で作れることを確かめる**

Run: `uvx git-cliff --latest --strip header`
Expected: 最新のタグの節が出て、末尾に `**Full Changelog**: https://github.com/rewse/enecoq-data-fetcher/compare/` がある

- [ ] **Step 5: 古い名前が残っていないことを確かめる**

Run: `rg -n 'security-scan|\.github/cliff|RELEASE\.md' --hidden -g '!.git'`
Expected: 出力なし

- [ ] **Step 6: Commit** — `ci: pin actions, add Dependabot, and rename the dependency scan`

### Task 7: stock-price-fetcher

**Files:**
- Create: `.github/dependabot.yml`（github-actions、uv）
- Modify: `gitleaks.yml`、`trufflehog.yml`（lob を除外）
- Rename: `security-scan.yml` → `dependency-scan.yml`。osv-scan のジョブを足し、`with: upload-sarif: false` を付ける

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: osv-scan の設定を確かめる**

Run: `rg -n -A8 'osv-scan:' .github/workflows/dependency-scan.yml`
Expected: `security-events: write` と `upload-sarif: false` がある

- [ ] **Step 5: Commit** — `ci: pin actions, add Dependabot, and scan dependencies with OSV`

### Task 8: textlint-config-rewse

**Files:**
- Create: `.github/dependabot.yml`（github-actions、npm）
- Modify: `gitleaks.yml`、`trufflehog.yml`
- Rename: `security-scan.yml` → `dependency-scan.yml`（Node 24）
- Modify: `release.yml`（Task 6 と同じ変更のうち、permissions、`config:`、`env:` への移動。setup-node の `node-version: '24'` と `SAFE_CHAIN_MINIMUM_PACKAGE_AGE_HOURS: 96` は残す）
- Rename: `.github/cliff.toml` → `cliff.toml`

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: `uvx git-cliff --latest --strip header` の出力の末尾に `https://github.com/rewse/textlint-config-rewse/compare/` があることを確かめる**
- [ ] **Step 5: `rg -n 'security-scan|\.github/cliff' --hidden -g '!.git'` の出力がないことを確かめる**
- [ ] **Step 6: Commit** — `ci: pin actions, add Dependabot, and rename the dependency scan`

### Task 9: textlint-rule-ja-space-around-phrase

Task 8 と同じ変更をする。加えて、`AGENTS.md` の 42 行目の `security-scan.yml` を `dependency-scan.yml` に直す。

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 変更する**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: `uvx git-cliff --latest --strip header` の出力の末尾に `https://github.com/rewse/textlint-rule-ja-space-around-phrase/compare/` があることを確かめる**
- [ ] **Step 5: `rg -n 'security-scan|\.github/cliff' --hidden -g '!.git'` の出力がないことを確かめる**
- [ ] **Step 6: Commit** — `ci: pin actions, add Dependabot, and rename the dependency scan`

### Task 10: zenn-content

**Files:** Create `.github/dependabot.yml`（github-actions、npm）。Modify `gitleaks.yml`、`trufflehog.yml`。Rename `security-scan.yml` → `dependency-scan.yml`（Node 24。zenn-cli の `engines` は `>=22.12.0` なので 24 でよい）

- [ ] **Step 1: C3 と C4 が失敗することを確かめる**
- [ ] **Step 2: 上の Files のとおりに直す**
- [ ] **Step 3: C1〜C4 がすべて通ることを確かめる**
- [ ] **Step 4: Commit** — `ci: pin actions, add Dependabot, and rename the dependency scan`

### Task 11: push とリモートでの検証

**Files:** なし

- [ ] **Step 1: 9 リポジトリの未 push のコミットを一覧にし、STOP して push の確認をユーザーに取る**

Run: `for d in ansible-playbooks chezmoi enecoq-data-fetcher mac-power-monitor-mqtt rewse-blog stock-price-fetcher textlint-config-rewse textlint-rule-ja-space-around-phrase zenn-content; do echo "== $d"; git -C ~/git/$d -P log --oneline @{u}..; done`

- [ ] **Step 2: 確認が取れたら各リポジトリで `git push` する**

- [ ] **Step 3: push で走ったワークフローが成功したことを確かめる**

Run: `gh run list -R rewse/<repo> -L 5`（リポジトリごと）
Expected: 最新のコミットの Gitleaks、Dependency Scan、Ansible Lint が `completed success`

- [ ] **Step 4: TruffleHog と Dependency Scan を手動で起動し、成功を確かめる**

Run: `gh workflow run trufflehog.yml -R rewse/<repo>`、`gh workflow run dependency-scan.yml -R rewse/<repo>`、そのあと `gh run watch -R rewse/<repo> <run-id>`
Expected: すべて `success`

- [ ] **Step 5: Dependabot の設定が受け付けられたことを確かめる**

Run: `gh api repos/rewse/<repo>/commits/main/check-runs --jq '.check_runs[] | select(.app.slug=="dependabot") | .name + " " + .conclusion'`
Expected: 失敗の check run がない。数日のうちに最初の更新の PR が届く

## Review Focus

- enecoq の `.python-version` は `3.13` で、CI はこれまで `3.14` で動いていた。`python-version-file` にすると CI も 3.13 になる。宣言した版で通るのが正しいので、Task 11 の Step 4 で enecoq の Dependency Scan が成功することを確かめる
- stock-price-fetcher は private なので、osv-scan の呼び出し側に `security-events: write` がないとワークフローが起動しない。Task 7 の Step 4 と Task 11 の Step 4 で確かめる
- release.yml は次のリリースまで走らない。`env:` への移動と cliff.toml の既定のパスは、C1、C2 と、Task 6、8、9 の `git-cliff` のステップで代わりに確かめる
- `persist-credentials: false` にすると、git の認証情報を使うステップは失敗する。今のワークフローには該当するものがないはずなので、Task 11 の Step 3 と Step 4 の成功で確かめる
- trufflehog は `@main` から v3.97.6 の固定に変わる。検出の結果が変わっていないことを、Task 11 の Step 4 の TruffleHog の成功で確かめる
