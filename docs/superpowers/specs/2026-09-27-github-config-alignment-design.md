# GitHub 設定の統一 設計

## 背景と目的

`~/git` に置いた `rewse/*` の各リポジトリの `.github` には、理由のない差がある。Dependabot は ansible-playbooks にしかなく、gitleaks-action は v2 と v3 が混在し、Action の指定は SHA 固定、メジャータグ、`@main` がばらばらで、`actions/checkout` は最新の v7 に追いついていない。

目的は、`.github` の構成を共通の方針にそろえ、その方針を `~/git/AGENTS.md` に書いて以後の変更でも保つことである。成功の条件は次のとおり。

- 対象の全リポジトリが方針どおりの構成になる
- 残る差には理由があり、その理由が `~/git/AGENTS.md` か各リポジトリの AGENTS.md から読める
- 変更後、push で走るワークフローと、手動で起動したワークフローがすべて成功する

## 範囲

対象は GitHub の `rewse/*` の 9 リポジトリとする。

| ローカルのディレクトリ | GitHub のリポジトリ | 公開 |
|---|---|---|
| ansible-playbooks | rewse/ansible-playbooks | public |
| chezmoi | rewse/dotfiles | public |
| enecoq-data-fetcher | rewse/enecoq-data-fetcher | public |
| mac-power-monitor-mqtt | rewse/mac-power-monitor-mqtt | public |
| rewse-blog | rewse/rewse-blog | public |
| stock-price-fetcher | rewse/stock-price-fetcher | private |
| textlint-config-rewse | rewse/textlint-config-rewse | public |
| textlint-rule-ja-space-around-phrase | rewse/textlint-rule-ja-space-around-phrase | public |
| zenn-content | rewse/zenn-content | public |

次は対象外とする。

- GitLab のリポジトリ（MeetNote、dotfiles-internal、context-ontology-accelerator-workshop）。`.github` を使わない
- context-ontology-accelerator。`.github` は upstream の `aws/context-ontology-accelerator` のもの
- lint とテストの CI を各リポジトリに足すこと。何を検証するかをリポジトリごとに決める話なので、別の spec で扱う
- GitHub 側のリポジトリ設定。Dependabot の security updates は確認した範囲で有効になっており、今回はファイルだけを変える
- issue と PR のテンプレート、CODEOWNERS。個人のリポジトリには要らない

## リポジトリごとの構成

| リポジトリ | Dependabot のエコシステム | gitleaks | trufflehog | dependency-scan | そのほか |
|---|---|---|---|---|---|
| ansible-playbooks | github-actions, pre-commit | あり | あり | なし | ansible-lint |
| chezmoi | github-actions | あり | あり（lob を除外） | なし | |
| enecoq-data-fetcher | github-actions, uv | あり | あり（lob を除外） | Safe Chain と OSV | release, cliff |
| mac-power-monitor-mqtt | github-actions | あり | あり | なし | |
| rewse-blog | github-actions, docker | あり | あり | なし | |
| stock-price-fetcher | github-actions, uv | あり | あり（lob を除外） | Safe Chain と OSV（`upload-sarif: false`） | |
| textlint-config-rewse | github-actions, npm | あり | あり | Safe Chain と OSV | release, cliff |
| textlint-rule-ja-space-around-phrase | github-actions, npm | あり | あり | Safe Chain と OSV | release, cliff |
| zenn-content | github-actions, npm | あり | あり | Safe Chain と OSV | |

残る差の理由は次のとおり。

- エコシステム: 各リポジトリが使うパッケージの仕組みに合わせる。rewse-blog の Python はスクリプト内の依存の書き方（PEP 723）で、Dependabot が読めないため対象にしない。blowfish のサブモジュールは `update_blowfish.sh` で更新するため、gitsubmodule も対象にしない
- dependency-scan: ロックファイルがあるリポジトリにだけ置く。ansible-playbooks、chezmoi、mac-power-monitor-mqtt、rewse-blog にはロックファイルがなく、OSV が調べるものがない
- trufflehog の lob の除外: lob の誤検知が出たリポジトリにだけ残す
- `upload-sarif: false`: private のリポジトリで Code Scanning を使うには GitHub Code Security が要る。アップロードを飛ばしても、スキャンは走り、脆弱性があれば `fail-on-vuln` の既定値でジョブが失敗する

## 共通の方針

### Dependabot

`.github/dependabot.yml` に、エコシステムごとに次の形の項目を置く。

```yaml
version: 2

updates:
  - package-ecosystem: <ecosystem>
    directory: /
    schedule:
      interval: weekly
    cooldown:
      default-days: 4
    groups:
      <ecosystem>:
        patterns: ["*"]
```

`cooldown` の 4 日は、npm と PyPI の最小公開経過時間 96 時間とそろえる。`groups` はエコシステムごとの更新を 1 つの PR にまとめ、9 リポジトリ分の PR の数を抑える。ansible-playbooks の既存のコメント（実行時の cooldown とそろえる旨）は残す。

### Action の指定

`uses:` はすべて `@<コミット SHA>  # vX.Y.Z` の形で固定する。reusable workflow（osv-scanner）と trufflehog も同じ扱いにし、`@main` やメジャータグは使わない。タグは後から別のコミットに付け替えられるので、タグで指定すると、付け替えられた直後から待ちなしで実行されてしまう。SHA で固定すれば、最新版への追従は Dependabot が cooldown の後に行う。

SHA は、公開から 4 日以上たったリリースのうち最新のものから選ぶ。

### ワークフローの書き方

- トップレベルの `permissions` は `contents: read` だけにする。それ以上の権限は必要なジョブにだけ付ける。dependency-scan の `actions: read` と `security-events: write` は osv-scan のジョブに移す
- `actions/checkout` には `persist-credentials: false` を付ける。git の認証情報を使うワークフローはなく、`gh` は `GITHUB_TOKEN` の環境変数で動く
- すべてのジョブに `name` を付ける
- Node.js は 24 とする。依存の `engines` が 24 を許さない場合だけ例外にする。zenn-content は zenn-cli の `engines` を実装時に確かめ、許せば 24 にする
- Python は `'3.14'` と直に書かず、`python-version-file: .python-version` で読む
- 定期実行の cron の分は、今のリポジトリごとの値を残し、同時に走らないようにする
- 書式をそろえる。`uses:` は引用符で囲まず、行末の空白は消す

### ファイルの名前と置き場所

| ファイル | 扱い |
|---|---|
| `security-scan.yml` | `dependency-scan.yml`（`name: Dependency Scan`）に改名する。gitleaks と trufflehog も security scan であり、中身の Safe Chain と OSV はどちらも依存を調べる |
| `release.yml` | 名前を変えない。PyPI と npm の Trusted Publishing はこのファイル名に紐づく |
| `gitleaks.yml`、`trufflehog.yml`、`ansible-lint.yml` | ツールの名前で中身が分かるため変えない |
| `.github/cliff.toml` | リポジトリの直下の `cliff.toml` に移す。git-cliff と git-cliff-action が既定で読む場所であり、release.yml の `config:` が要らなくなり、手元の `git-cliff` もフラグなしで動く |
| enecoq の `.github/RELEASE.md` | 消す。`__init__.py` を直に書き換える古い手順で、AGENTS.md の `scripts/bump_version.sh` と食い違う。Trusted Publisher が `release.yml` と Environment の `release` に紐づくことだけを、enecoq の AGENTS.md のリリースの段落に英語で移す |

拡張子は `.yml` のままにする。全リポジトリがすでに `.yml` で、GitHub のドキュメントと ansible-playbooks の規約も `.yml` である。

改名しても、README のバッジやブランチ保護の必須チェックは壊れない。どのリポジトリにもバッジはなく、ブランチ保護もルールセットもない。過去の実行履歴は旧い名前の下に残る。

cliff.toml を移しても、配布物は変わらない。textlint の 2 つは npm の `files` に書いたものだけを公開し、enecoq の sdist は hatchling が作っていて、移す前から cliff.toml を含んでいる。

### リポジトリ固有の修正

- chezmoi: trufflehog の `--exclude-paths=.trufflehog-exclude-paths.txt` と、コメントしかない `.trufflehog-exclude-paths.txt` を消す
- stock-price-fetcher: dependency-scan に osv-scan のジョブを `upload-sarif: false` 付きで足す
- enecoq-data-fetcher: release.yml の setup-python と setup-uv を dependency-scan と同じ最新版にする
- gitleaks-action を v2 から v3 に上げる（enecoq、mac-power-monitor-mqtt、rewse-blog、stock-price-fetcher、textlint の 2 つ）

## `~/git/AGENTS.md` と chezmoi

### chezmoi での管理

`chezmoi add` で `~/git/AGENTS.md` を source の `git/AGENTS.md` に取り込む。`~/git/CLAUDE.md` は `@AGENTS.md` を読み込むだけのファイルで、Claude Code は `AGENTS.md` を直接読むため不要になっている。取り込まずに削除する。同じく読み込むだけか空の、未追跡の `chezmoi/CLAUDE.md`、`textlint-config-rewse/CLAUDE.md`、`textlint-rule-ja-space-around-phrase/CLAUDE.md` も削除する。`~/git` は Mac にしかないため、`.chezmoiignore` の darwin 以外のブロックに `git` を足す。rewse/dotfiles は public なので、`~/git/AGENTS.md` に書く内容も公開される。

### 追記する節

rule ファイルなので英語で書く。

```markdown
# GitHub Configuration

Keep `.github` consistent across the `rewse/*` repositories cloned here. A repository may differ only for a reason stated in this section or in its own AGENTS.md. Repositories hosted on GitLab and forks of upstream projects are out of scope.

- Give every repository a `.github/dependabot.yml` that covers `github-actions` and each package ecosystem it uses (`docker`, `npm`, `pre-commit`, `uv`). Each entry runs weekly, groups all updates of the ecosystem into one pull request, and sets `cooldown.default-days: 4` to match the 96-hour minimum package age.
- Pin every `uses:`, including reusable workflows, to a full commit SHA followed by `# vX.Y.Z`. Do not reference tags or branches, because a tag can be moved to malicious code; Dependabot keeps the pins current.
- Set top-level `permissions` to `contents: read` and grant anything more on the job that needs it.
- Set `persist-credentials: false` on `actions/checkout`, give every job a `name`, use Node.js 24 unless a dependency's `engines` rules it out, and read the Python version from `.python-version`.
- Run `gitleaks.yml` on push, pull request, and a weekly schedule, and `trufflehog.yml` as a weekly sweep, in every repository. Add `--exclude-detectors=<detector>` only in a repository where that detector reported a false positive.
- Add `dependency-scan.yml` to every repository with a lockfile: install dependencies through Aikido Safe Chain and call the OSV-Scanner reusable workflow. Pass `upload-sarif: false` in a private repository, since Code Scanning there requires GitHub Code Security.
- Give each repository's scheduled workflows their own cron minutes so they do not run at the same time.
- Name a workflow file after the tool it runs or the job it does (`gitleaks.yml`, `dependency-scan.yml`, `release.yml`), use the `.yml` extension, and never rename `release.yml`, because PyPI and npm Trusted Publishing are bound to that file name.
- Keep tool configuration at the path the tool reads by default (for example, `cliff.toml` at the repository root) so it works locally without extra flags.
```

## 展開の順番

1. chezmoi: この spec をコミットし、`~/git/AGENTS.md` の取り込み、`~/git/CLAUDE.md` の削除、自身の `.github` の変更を行う
2. 残りの 8 リポジトリ: 1 リポジトリにつき 1 コミット（`ci:`）とする。ansible-playbooks は未コミットの変更で `git pull` が止まっているため、作業の前に扱いをユーザーに確かめる
3. 手元の検証: 全ワークフローに `actionlint` と `zizmor` をかける
4. push: 外部への書き込みなので、全リポジトリ分をまとめてユーザーの確認を取ってから行う

各リポジトリの AGENTS.md で `security-scan.yml` や `.github/cliff.toml` を参照している箇所は、同じコミットで新しい名前に直す。

## 検証

- 手元: `actionlint` と `zizmor` がエラーなしで通る。`rg '@(v[0-9]|main)' .github` で SHA 固定でない `uses:` が残っていない
- push 後: `gh run list` で、push で走った gitleaks、ansible-lint、dependency-scan が成功している
- 手動の起動: trufflehog と dependency-scan を `workflow_dispatch` で一度ずつ走らせ、成功を確かめる
- Dependabot: 設定エラーのチェックが出ていないことと、最初の更新の PR が届くことを確かめる
- release.yml: 次のリリースまで走らないため、`actionlint` と `zizmor` の結果と、`config:` を消した git-cliff-action の既定値の確認で代える
