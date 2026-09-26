# lint とテストの CI 設計

## 背景と目的

`rewse/*` の各リポジトリでは、lint とテストを CI で走らせているかがばらばらである。テストがあっても CI で走らせていないリポジトリ（enecoq-data-fetcher、stock-price-fetcher）があり、textlint の 2 つは dependency-scan の中でテストを走らせている。zizmor と actionlint は `.github` の変更時に手で回しただけで、shellcheck、ruff、basedpyright はどこでも CI にない。

目的は、各リポジトリの lint とテストを CI で強制し、手元の検査と CI の検査を同じにすることである。lint のツールは、手元で使う Zed のものにそろえる。成功の条件は次のとおり。

- 全リポジトリで `uvx pre-commit run --all-files` が通り、同じ検査が `lint.yml` で走る
- テストがあるリポジトリでは `test.yml` がテストを走らせ、dependency-scan は依存の検査だけを行う
- 今ある指摘はすべて直っているか、直せない理由がその行に書いてある
- push 後の `lint.yml` と `test.yml` がすべて成功する

これは 2026-09-27 の GitHub 設定の統一（`2026-09-27-github-config-alignment-design.md`）で対象外にした部分である。

## 範囲

対象は `rewse/actions` を加えた 10 リポジトリとする。ansible-playbooks、chezmoi（rewse/dotfiles）、enecoq-data-fetcher、mac-power-monitor-mqtt、rewse-blog、stock-price-fetcher、textlint-config-rewse、textlint-rule-ja-space-around-phrase、zenn-content、actions である。

次は対象外とする。

- rewse-blog と ansible-playbooks の Markdown の textlint。どちらにも textlint の設定がなく、文章の方針を決める話になる
- 手元の git フック（`pre-commit install`）。入れるかは各自に任せ、方針にはコミットの前に `uvx pre-commit run --all-files` を回すことだけを書く
- mypy や ty のような、Zed が既定で使わない型チェッカー

## Zed との対応

Zed は Python に basedpyright と ruff を同時に使い、basedpyright の型チェックのモードを `standard` にしている（basedpyright 単体の既定は `recommended`）。手元の Zed のログでも、`/opt/homebrew/bin/basedpyright-langserver` と ruff が起動している。

| 対象 | Zed が使うもの | CI で使うもの |
|---|---|---|
| Python | basedpyright（`standard`）、ruff | basedpyright（`standard`）、ruff check、ruff format |
| シェル | bash-language-server（中で shellcheck を使う） | shellcheck |
| YAML | yaml-language-server（SchemaStore のスキーマ） | check-jsonschema の `check-dependabot`、actionlint |
| Ansible | ansible の拡張（中で ansible-lint を使う） | ansible-lint |

basedpyright の `typeCheckingMode = "standard"` は設定ファイルに明示する。`pyproject.toml` があるリポジトリは `[tool.basedpyright]` に書き、ないリポジトリは `pyrightconfig.json` に書く。Zed の既定の値に頼らず、Zed と CLI が同じファイルを読むようにする。

## 構成

各リポジトリに次の 3 つを置く。

| ファイル | 中身 |
|---|---|
| `.pre-commit-config.yaml` | lint のフック。`rev:` は `<SHA>  # frozen: vX.Y.Z` |
| `.github/workflows/lint.yml` | Safe Chain の下で `uvx pre-commit run --all-files --show-diff-on-failure` を実行する |
| `.github/workflows/test.yml` | テストがあるリポジトリだけ。テストを走らせる |

`lint.yml` と `test.yml` は、`main` への push、`main` への pull request、`workflow_dispatch` で走る。定期実行はしない。dependabot.yml には `pre-commit` のエコシステムを、ほかと同じ形（weekly、`cooldown.default-days: 4`、グループ）で足す。ansible-playbooks にはすでにある。

### フックの割り当て

| フック | 対象 |
|---|---|
| actionlint（actionlint-py のミラー）、zizmor、check-jsonschema の `check-dependabot` | 10 リポジトリすべて |
| shellcheck（shellcheck-py） | actions、ansible-playbooks、chezmoi、enecoq-data-fetcher、mac-power-monitor-mqtt、rewse-blog |
| ruff check、ruff format、basedpyright | ansible-playbooks、chezmoi、enecoq-data-fetcher、rewse-blog、stock-price-fetcher |
| ansible-lint | ansible-playbooks |
| textlint（`repo: local`、`language: system`、`npm run lint`） | zenn-content |

chezmoi の `*.tmpl` は、テンプレートの構文を shellcheck と ruff が読めないため対象から外す。ruff は既定のルールのまま使い、`select` などの設定は足さない。

zizmor は、CI では `GH_TOKEN` を渡して online で動かす。固定した SHA が本当にそのリポジトリのコミットかを確かめる audit（impostor-commit など）が走るからである。手元でトークンがない場合に offline で動くかは、plan で確かめる。

### lint.yml

ジョブは 1 つで、次の順に進む。

1. `actions/checkout`
2. `astral-sh/setup-uv`
3. `rewse/actions/setup-safe-chain`
4. 依存を持つリポジトリだけ、Safe Chain 経由で依存を入れる。enecoq-data-fetcher と stock-price-fetcher は `uv sync`（basedpyright が `.venv` を読む）、zenn-content は `actions/setup-node` と `npm ci`（textlint のフックが `node_modules` を使う）
5. `uvx pre-commit run --all-files --show-diff-on-failure`

`uvx` は Safe Chain の shim を通るので、フックの環境を作るときの pip や npm の取得も Safe Chain の検査を受ける。手元で確かめたところ、ruff を無指定でフックの依存にすると、公開から 96 時間たっていない 0.16.9 が外され、0.16.8 が入った。

### test.yml

| リポジトリ | テスト |
|---|---|
| actions | 今の `test.yml` のまま |
| enecoq-data-fetcher | `uv sync` の後に `bash tests/run_tests.sh` |
| stock-price-fetcher | `uv sync` の後に `uv run pytest` |
| textlint-config-rewse | `npm ci` の後に `npm test` |
| textlint-rule-ja-space-around-phrase | `npm ci` の後に `npm run build` と `npm test` |

依存は Safe Chain 経由で入れる。textlint の 2 つは、dependency-scan の中の build と test を `test.yml` に移す。dependency-scan は依存の導入と OSV-Scanner だけにする。

## 既存の指摘の直し方

2026-09-27 に手元で数えた件数は次のとおり。

| 検査 | 件数 |
|---|---|
| ruff check | enecoq-data-fetcher が約 115 件、ほかの 4 リポジトリが 3〜13 件 |
| basedpyright（`standard`） | エラーが chezmoi 12 件、enecoq-data-fetcher 22 件、rewse-blog 26 件（うち警告 3）、stock-price-fetcher 5 件、ansible-playbooks 警告 1 件 |
| shellcheck | ansible-playbooks 67 件（大半が SC2086）、chezmoi、enecoq-data-fetcher、mac-power-monitor-mqtt、rewse-blog が各 1 件 |
| textlint（zenn-content） | 公開済みの 4 記事で 30 件 |
| zizmor、actionlint | 0 件 |

指摘は抑えずに直す。抑えるのは、正しい設計がルールに反する場合（CLI の最上位で例外をまとめて受ける BLE001 など）と、外部ライブラリの型の誤りのようにこちらで直せない場合だけとし、その行に `# noqa: <code>` や `# pyright: ignore[<rule>]` と理由を書く。ruff の自動修正は `--fix` の安全なものだけを使い、`--unsafe-fixes` は使わない。

振る舞いが変わりうるのは、ansible-playbooks の Zabbix 向けスクリプトにクォートを足す修正である。テストがないため、変更点を 1 つずつ見直し、shellcheck が通ることで確かめる。サーバーに届くのは次に playbook を流したときである。

zenn-content の記事は、意味を変えずに直す。zenn は GitHub から同期して公開しているため、push した時点で公開中の記事の文面が変わる。

## コミット

リポジトリごとに次の順でコミットする。修正を先に入れ、ワークフローが初めて走るときから成功するようにする。該当する変更がないコミットは作らない。

1. `style:` ruff format による整形だけ
2. `fix:` か `refactor:` lint と型の指摘の修正と、basedpyright の設定
3. `ci:` `.pre-commit-config.yaml`、`lint.yml`、`test.yml`、dependabot.yml、dependency-scan からのテストの移動

各リポジトリの AGENTS.md にコミットの決まりがあれば、それを優先する。

- enecoq-data-fetcher: 本文に何をなぜ変えたかを書き、モジュール名（`authenticator`、`cli` など）をスコープにする。モジュールをまたぐ修正は、モジュールごとにコミットを分ける
- chezmoi: `dot_*` と `private_dot_*` のファイルに `docs:` を使わない
- zenn-content: 記事の修正は記事ごとにコミットし、スコープを `article:<slug>` にする。型は変更の性質で選ぶ。誤りの修正は `fix`、意味を変えない読みやすさのための書き換えは `refactor`、表記の統一は `style` とする。本文には理由を書き、文言の変更は日本語の語をそのまま引用する。この AGENTS.md の型に `ci` はないため、CI の設定は「configuration updates」に当たる `chore:` にする

## `~/git/AGENTS.md`

GitHub Configuration の節に、次の方針を英語で足す。

- 各リポジトリに `.pre-commit-config.yaml` を置き、そのリポジトリの言語に合うフックを並べる。`rev:` は `<SHA>  # frozen: vX.Y.Z` で固定する
- `lint.yml` で、Safe Chain の下で `uvx pre-commit run --all-files` を実行する
- lint は Zed が使うものにそろえる。Python は basedpyright（`typeCheckingMode = "standard"` を設定ファイルに明示）と ruff、シェルは shellcheck、YAML は check-jsonschema と actionlint、Ansible は ansible-lint
- 指摘は抑えずに直す。抑えるときは、その行に理由を書く
- テストは `test.yml` で走らせ、dependency-scan には入れない
- コミットの前に `uvx pre-commit run --all-files` を回す

各リポジトリの AGENTS.md に、dependency-scan でテストするといった古い記述があれば、同じコミットで直す。

## 検証

- 手元: 各リポジトリで、変更の前に `uvx pre-commit run --all-files` が失敗し、変更の後に通る。テストがあるリポジトリでは、修正の後もテストが通る
- push 後: `lint.yml` と `test.yml` が成功し、textlint の 2 つの dependency-scan も成功する
- Dependabot: `pre-commit` のエコシステムで設定のエラーが出ない
- push は外部への書き込みなので、全リポジトリ分をまとめてユーザーの確認を取ってから行う。zenn-content は push すると公開中の記事が変わることを、その確認の中で伝える
