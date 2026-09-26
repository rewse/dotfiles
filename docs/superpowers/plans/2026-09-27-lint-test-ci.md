# lint とテストの CI 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `rewse/*` の 10 リポジトリで、Zed と同じ lint を pre-commit にまとめて `lint.yml` で強制し、テストを `test.yml` で走らせる。

**Architecture:** 各リポジトリに `.pre-commit-config.yaml` を置き、手元と CI で同じ `pre-commit run --all-files` を実行する。CI では Safe Chain の shim の下で `uvx` を動かし、フックの環境の取得も Safe Chain に通す。リポジトリごとに 1 タスクとし、既存の指摘を直してからワークフローを足す。

**Tech Stack:** pre-commit 4.6.2、pre-commit-uv 4.3.0、actionlint、zizmor、check-jsonschema、shellcheck、ruff、basedpyright、ansible-lint、textlint、GitHub Actions

**Spec:** `docs/superpowers/specs/2026-09-27-lint-test-ci-design.md`

## Global Constraints

- pre-commit の実行は、手元でも CI でも `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files --show-diff-on-failure` とする（以下「PC」）。素の pre-commit は、runner の上で uv の管理する Python を見つけられずに失敗する
- `rev:` は `<40 桁の SHA>  # frozen: <tag>` の形にする。値は下の表のものを使う
- `uses:` は今のリポジトリと同じ SHA を使う（下の表）
- basedpyright は `typeCheckingMode = "standard"` を設定ファイルに明示する。`pyproject.toml` があるリポジトリは `[tool.basedpyright]`、ないリポジトリは `pyrightconfig.json`
- ruff は既定のルールのまま使う。`select`、`ignore` などの設定は足さない。自動修正は `ruff check --fix` の安全なものだけとし、`--unsafe-fixes` は使わない
- 指摘を抑えるのは、正しい設計がルールに反する場合と、原因がリポジトリの外にある場合だけ。その行に `# noqa: <code>  <理由>`、`# pyright: ignore[<rule>]  <理由>`、`# shellcheck disable=<code>  # <理由>` の形で理由を書く
- コミットは各リポジトリで `style:`（ruff format）、`fix:` か `refactor:`（指摘の修正と basedpyright の設定）、`ci:` の順。該当する変更がないものは作らない。各リポジトリの AGENTS.md のコミットの決まりを優先する（enecoq はモジュールのスコープと本文、zenn は記事ごとの `article:<slug>` と `chore:`、chezmoi は `dot_*` に `docs:` を使わない）
- 作業の前に `git pull --ff-only` を行う。push は Task 12 でユーザーの確認を取ってから行う

固定する値（公開から 96 時間以上たった最新のもの。2026-09-26T19:22Z に解決した）:

| フックのリポジトリ | tag | SHA | フックの id |
|---|---|---|---|
| Mateusz-Grzelinski/actionlint-py | v1.7.12.25 | `805f85e558841bf4d852335e036b33d2b26be1cc` | `actionlint` |
| zizmorcore/zizmor-pre-commit | v1.30.1 | `fa412071e4f5d44d44f9e365f4676f9df92456a2` | `zizmor` |
| python-jsonschema/check-jsonschema | 0.38.0 | `12e63946db2c5cfcc9030fac21c3883ba88c6ed8` | `check-dependabot` |
| shellcheck-py/shellcheck-py | v0.11.0.1 | `745eface02aef23e168a8afb6b5737818efbea95` | `shellcheck` |
| astral-sh/ruff-pre-commit | v0.16.8 | `2eeb5678de71a00c0902cbda7105d328432f72cb` | `ruff-check`、`ruff-format` |
| DetachHead/basedpyright-pre-commit-mirror | 1.40.1 | `706e6acebe9e88c2c28d1527d3085a14b11794c4` | `basedpyright` |
| ansible/ansible-lint | v26.9.0 | `e7f397ad6dfa20d274afa17cd7bbedd84ed136f5` | `ansible-lint` |

| Action | 版 | SHA |
|---|---|---|
| actions/checkout | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| actions/setup-node | v7.0.0 | `820762786026740c76f36085b0efc47a31fe5020` |
| actions/setup-python | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| astral-sh/setup-uv | v10.2.0 | `c18668ad3cf93ea998bef934396af7bb5c839dc7` |
| rewse/actions/setup-safe-chain | v1.0.0 | `499465b2ad235c5fa2c412f922ad3bf0aff73163` |

## 共通のファイル

**`.pre-commit-config.yaml`**: 次の 3 つのフックを全リポジトリの先頭に置き、表の「追加のフック」をその後ろに足す。

```yaml
repos:
  - repo: https://github.com/Mateusz-Grzelinski/actionlint-py
    rev: 805f85e558841bf4d852335e036b33d2b26be1cc  # frozen: v1.7.12.25
    hooks:
      - id: actionlint
  - repo: https://github.com/python-jsonschema/check-jsonschema
    rev: 12e63946db2c5cfcc9030fac21c3883ba88c6ed8  # frozen: 0.38.0
    hooks:
      - id: check-dependabot
  - repo: https://github.com/zizmorcore/zizmor-pre-commit
    rev: fa412071e4f5d44d44f9e365f4676f9df92456a2  # frozen: v1.30.1
    hooks:
      - id: zizmor
```

shellcheck のフックには `exclude_types: [zsh]` を付ける。shellcheck は zsh を読めない。

**`lint.yml`**:

```yaml
name: Lint

on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  pre-commit:
    name: pre-commit
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1  # v7.0.1
        with:
          persist-credentials: false

      - name: Install uv
        uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7  # v10.2.0

      - name: Setup Aikido Safe Chain
        uses: rewse/actions/setup-safe-chain@499465b2ad235c5fa2c412f922ad3bf0aff73163  # v1.0.0

      # <DEPS>: 依存を持つリポジトリだけ、ここで依存を入れる

      # uvx runs through the Safe Chain shim, so hook environments are
      # installed through Safe Chain too. pre-commit-uv builds them with uv,
      # which finds the uv-managed Python that plain virtualenv cannot.
      - name: Run pre-commit
        env:
          # zizmor runs its online audits, such as impostor-commit, with a token.
          GH_TOKEN: ${{ github.token }}
        run: uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files --show-diff-on-failure
```

`<DEPS>` は次のとおり。

- enecoq-data-fetcher、stock-price-fetcher: `Install dependencies` で `uv sync --extra test --safe-chain-skip-minimum-package-age`
- zenn-content: `Setup Node.js`（setup-node、`node-version: '24'`）と、`Install dependencies` で `npm ci --safe-chain-skip-minimum-package-age`

**`test.yml`**: `name: Test`。`on` と `permissions` は lint.yml と同じ。ジョブは `test`（`name: Test`）で、checkout、言語のセットアップ、setup-safe-chain、依存の導入、テストの順に並べる。ステップはリポジトリのタスクに書く。

**dependabot.yml に足す項目**（ansible-playbooks にはすでにある）:

```yaml
  - package-ecosystem: pre-commit
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 4  # zizmor: ignore[dependabot-cooldown] matches the 96-hour minimum package age
    groups:
      pre-commit:
        patterns: ["*"]
```

## 共通の手順

各リポジトリのタスクは次の手順で進める。タスクに書いた違いだけを加える。

- [ ] **A. `git pull --ff-only` して、`.pre-commit-config.yaml`（と basedpyright の設定）を置く。この段階ではコミットしない**
- [ ] **B. PC を実行し、失敗することを確かめる**。Expected: タスクに書いたフックが失敗する。何も失敗しないリポジトリは B を「成功」として記録する
- [ ] **C. `ruff format` の差分だけを `style:` でコミットする**（Python のあるリポジトリだけ）
- [ ] **D. 残りの指摘を直し、PC が通ることを確かめる**。Expected: すべてのフックが `Passed` か `Skipped`
- [ ] **E. テストがあるリポジトリは、テストが通ることを確かめる**
- [ ] **F. 修正と basedpyright の設定をコミットする**（`fix:` か `refactor:`）
- [ ] **G. `.pre-commit-config.yaml`、lint.yml、test.yml、dependabot.yml を足し、次を確かめてから `ci:` でコミットする**

```bash
uvx --from actionlint-py actionlint
uvx zizmor --offline --min-severity low .github
uvx check-jsonschema --builtin-schema vendor.dependabot .github/dependabot.yml
```

Expected: どれも出力がなく、終了コードが 0

---

### Task 1: `~/git/AGENTS.md`

**Files:** Modify `~/git/AGENTS.md`（chezmoi の `git/AGENTS.md` と同じ内容にする）

- [ ] **Step 1: GitHub Configuration の節で、`dependency-scan.yml` の項目の次に、次の 3 項目をこの順で足す**

```markdown
- Give every repository a `.pre-commit-config.yaml` with the hooks for the languages it contains: actionlint, check-jsonschema, and zizmor everywhere, plus basedpyright and ruff for Python, shellcheck for shell scripts, and ansible-lint for Ansible, which match what Zed runs. Pin each `rev:` to a full commit SHA followed by `# frozen: vX.Y.Z`, set basedpyright's `typeCheckingMode = "standard"` in `pyproject.toml` or `pyrightconfig.json`, and run `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files` before committing.
- Run the same command in `lint.yml` after `rewse/actions/setup-safe-chain`, so the hook environments are installed through Safe Chain, and run tests in `test.yml` rather than in `dependency-scan.yml`.
- Fix lint and type findings instead of suppressing them. Suppress one only where the rule conflicts with a deliberate design or the cause lies outside the repository, and state the reason on the same line.
```

- [ ] **Step 2: `chezmoi --no-pager re-add ~/git/AGENTS.md` の後、`chezmoi --no-pager diff ~/git/AGENTS.md` が空であることを確かめる**
- [ ] **Step 3: Commit** — `git -C ~/git/chezmoi add git/AGENTS.md`、`docs: add lint and test CI policy to ~/git/AGENTS.md`

### Task 2: actions

追加のフック: shellcheck。テスト: 今の `test.yml` のまま。

- [ ] 共通の手順 A〜G（C、E、F は該当なし。B で失敗しなければそのまま G へ進む）
- [ ] **Commit** — `ci: lint with pre-commit and add Dependabot for hooks`

### Task 3: mac-power-monitor-mqtt

追加のフック: shellcheck。テスト: なし（`make test` は実機の MQTT に送るため CI では走らせない）。

- [ ] 共通の手順 A〜G。D で SC1091 は `# shellcheck source=config.example` を `source` の直前の行に書いて直す
- [ ] **Commit** — `fix: resolve shellcheck findings`、`ci: lint with pre-commit and add Dependabot for hooks`

### Task 4: textlint-config-rewse

追加のフック: なし。

**Files:** Create `test.yml`。Modify `dependency-scan.yml`（Test のステップを消す）、`dependabot.yml`

test.yml のステップ: setup-node（`'24'`）、setup-safe-chain、`npm ci --safe-chain-skip-minimum-package-age`、`npm test`。

- [ ] 共通の手順 A〜G
- [ ] **dependency-scan.yml の safe-chain のジョブが、checkout、setup-node、setup-safe-chain、`npm ci` の 4 つだけになったことを確かめる**
- [ ] **Commit** — `ci: lint with pre-commit and move tests to test.yml`

### Task 5: textlint-rule-ja-space-around-phrase

Task 4 と同じ。test.yml は `npm ci` の後に `npm run build` と `npm test` を走らせ、dependency-scan.yml から Build と Test のステップを消す。`AGENTS.md` の 42 行目は依存の検査の説明なので変えない。

- [ ] 共通の手順 A〜G
- [ ] **Commit** — `ci: lint with pre-commit and move tests to test.yml`

### Task 6: stock-price-fetcher

追加のフック: ruff-check、ruff-format、basedpyright。basedpyright の設定は `pyproject.toml` の `[tool.basedpyright]` に `typeCheckingMode = "standard"`、`venvPath = "."`、`venv = ".venv"`。

test.yml のステップ: setup-python（`python-version-file: .python-version`）、setup-uv、setup-safe-chain、`uv sync --extra test --safe-chain-skip-minimum-package-age`、`uv run pytest`。

- [ ] 共通の手順 A〜G。B の Expected: ruff-check（3 件）と basedpyright（5 件）が失敗する
- [ ] E: `uv run --extra test pytest` が 123 件成功する
- [ ] **Commit** — `style: format with ruff`、`fix: resolve ruff and basedpyright findings`、`ci: lint with pre-commit and run tests in CI`

### Task 7: zenn-content

追加のフック:

```yaml
  - repo: local
    hooks:
      - id: textlint
        name: textlint
        entry: npm run lint
        language: system
        files: ^articles/.*\.md$
        pass_filenames: false
```

- [ ] 共通の手順 A、B。B の Expected: textlint が失敗し、4 記事で 30 件のエラーが出る
- [ ] **D: 記事を 1 本ずつ直し、記事ごとにコミットする**。意味を変えずに直し、`npm run lint` が通ることを確かめる。コミットは `fix(article:<slug>)`、`refactor(article:<slug>)`、`style(article:<slug>)` から変更の性質で選ぶ。本文に理由を書き、文言の変更は日本語の語をそのまま引用する
- [ ] G の Commit — `chore: lint with pre-commit in CI`（zenn の AGENTS.md の型の一覧に `ci` はない）

### Task 8: rewse-blog

追加のフック: shellcheck、ruff-check、ruff-format、basedpyright。basedpyright の設定は `pyrightconfig.json` に `{"typeCheckingMode": "standard"}`。basedpyright のフックの `additional_dependencies` に、スクリプトの PEP 723 の宣言と同じ `pyvips==3.2.0` を足す。

- [ ] 共通の手順 A〜G。B の Expected: shellcheck（SC2115 が 1 件）、ruff-check、basedpyright が失敗する
- [ ] E: `uv run --with pytest --with pyvips==3.2.0 pytest tests` が成功する（今の実行方法が AGENTS.md や README にあればそちらに従う）
- [ ] **Commit** — `style: format with ruff`、`fix: resolve shellcheck, ruff, and basedpyright findings`、`ci: lint with pre-commit and add Dependabot for hooks`

### Task 9: chezmoi

追加のフック: shellcheck、ruff-check、ruff-format、basedpyright。すべてのフックに `exclude: \.tmpl$` を付ける。basedpyright の設定は `pyrightconfig.json` に `{"typeCheckingMode": "standard"}`。basedpyright のフックの `additional_dependencies` に、`reddit.py` の PEP 723 の宣言と同じ `beautifulsoup4` を足す。

**Files:** 上に加えて、Modify `.chezmoiignore`（先頭のブロックに `pyrightconfig.json` をアルファベット順で足す）

- [ ] 共通の手順 A〜G。B の Expected: shellcheck（SC2001 が 1 件）、ruff-check、basedpyright が失敗する
- [ ] **pyrightconfig.json が配布されないことを確かめる**。Run: `chezmoi --no-pager managed | rg -c pyrightconfig`。Expected: `0`
- [ ] E: `uv run --with pytest pytest tests` が成功する
- [ ] **Commit** — `style: format with ruff`、`fix: resolve shellcheck, ruff, and basedpyright findings`、`ci: lint with pre-commit and add Dependabot for hooks`。`dot_*` のファイルの修正に `docs:` を使わない

### Task 10: enecoq-data-fetcher

追加のフック: shellcheck、ruff-check、ruff-format、basedpyright。basedpyright の設定は Task 6 と同じ。

test.yml のステップ: setup-python（`python-version-file: .python-version`）、setup-uv、setup-safe-chain、`uv sync --extra test --safe-chain-skip-minimum-package-age`、`./tests/run_tests.sh`。

- [ ] 共通の手順 A〜G。B の Expected: shellcheck（SC2164 が 1 件）、ruff-check（約 115 件）、basedpyright（22 件）が失敗する
- [ ] D の注意: DTZ001 と DTZ005 は、今の振る舞い（ローカル時刻で数える）を変えないタイムゾーンを明示して直す。naive と aware の datetime を比べる箇所が残っていないことを、テストで確かめる
- [ ] E: `./tests/run_tests.sh` が `All test suites passed!` を出す
- [ ] **Commit**: `style: format with ruff`。修正はモジュールごとに、`fix(<module>):` か `refactor(<module>):` として本文付きで分ける。テストの修正は、テストするモジュールのスコープに含める。最後に `ci: lint with pre-commit and run tests in CI`

### Task 11: ansible-playbooks

追加のフック: 今の ansible-lint（`rev:` を表の SHA にする）、shellcheck、ruff-check、ruff-format、basedpyright。basedpyright の設定は `pyrightconfig.json` に `{"typeCheckingMode": "standard"}`。

**Files:** `.github/workflows/ansible-lint.yml` を `git mv` で `lint.yml` に改名して、共通の lint.yml の形にする。今のコメントのうち、pre-commit-uv の理由は残す。`AGENTS.md` の Lint の節のコマンドを PC にそろえる。

- [ ] 共通の手順 A〜G。B の Expected: shellcheck（67 件）、ruff-check、basedpyright（警告 1 件）が失敗する
- [ ] D の注意: SC2086 は、単語分割を意図した箇所（引数の並びを展開するところなど）を配列に書き換える。配列にできない箇所だけ、理由付きで抑える。スクリプトごとに、変更の前後で分割のされ方が同じかを読んで確かめる
- [ ] **Commit** — `style: format with ruff`、`fix: resolve shellcheck, ruff, and basedpyright findings`、`ci: run all lint hooks in lint.yml`

### Task 12: push とリモートでの検証

- [ ] **Step 1: 10 リポジトリと chezmoi の未 push のコミットを一覧にし、STOP して push の確認をユーザーに取る**。zenn-content は push すると公開中の 4 記事の文面が変わることを伝える
- [ ] **Step 2: 確認が取れたら push する**。public のリポジトリは Code Defender に止められるため、github-push-via-fox の手順で push する。stock-price-fetcher は直接 push する
- [ ] **Step 3: 各リポジトリで Lint、Test、Dependency Scan が成功したことを確かめる**。Run: `gh run list -R rewse/<repo> -L 6`。Expected: 最新のコミットの実行がすべて `completed success`
- [ ] **Step 4: Lint のログで、Safe Chain の下でフックが入ったことを確かめる**。Run: `gh run view -R rewse/<repo> <run-id> --log | rg -i 'safe-chain'`。Expected: setup-safe-chain の後の pre-commit のステップにも Safe Chain の出力がある。なければ、`uvx` が shim を通っていない理由を調べる
- [ ] **Step 5: Dependabot の設定が受け付けられたことを確かめる**。Run: `gh api repos/rewse/<repo>/commits/main/check-runs --jq '.check_runs[] | select(.app.slug=="dependabot") | .name + " " + .conclusion'`。Expected: 失敗の check run がない

## Review Focus

- ansible-playbooks の SC2086 の修正で、意図した単語分割を壊すと、Zabbix の監視スクリプトがサーバーの上で壊れる。テストがないので、Task 11 の D の注意に従って 1 つずつ読んで確かめる
- enecoq の DTZ の修正で、naive な datetime を aware にすると、比較や表示の時刻が変わる。Task 10 の D の注意とテストで確かめる
- zenn の記事の修正で文意が変わると、公開中の記事の内容が変わる。Task 7 で、記事ごとの差分を読んで確かめる
- CI の `uvx` が Safe Chain の shim を通っていないと、フックの環境が検査なしで入る。Task 12 の Step 4 で確かめる
- chezmoi の `pyrightconfig.json` が `.chezmoiignore` になければ、ホームに配布される。Task 9 で確かめる
