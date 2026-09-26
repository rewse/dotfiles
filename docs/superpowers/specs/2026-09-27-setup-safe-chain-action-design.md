# Safe Chain の導入 Action 設計

## 背景と目的

依存のスキャンと npm のリリースの 7 つのワークフローは、`raw.githubusercontent.com/AikidoSec/safe-chain/main/install-scripts/install-safe-chain.sh` を `curl | sh` で実行している。main ブランチの中身は予告なく変わり、バイナリは最新版を取り、main 版のスクリプトは checksum の確認を飛ばす。リリースのワークフローでは、この処理が npm と PyPI に公開する権限（`id-token: write`）を持つジョブの中で走る。

目的は、Safe Chain を公開から 96 時間以上たった immutable なリリースから、checksum を確かめて入れることである。版は手で上げない。成功の条件は次のとおり。

- 7 つのワークフローに `curl | sh` が残らない
- 新しい Safe Chain のリリースは、公開から 96 時間たつと手を入れずに使われる
- 呼び出し側の Action の更新は Dependabot が行う

## 共通の Action

public のリポジトリ `rewse/actions`（MIT、README は英語）に、composite action `setup-safe-chain` を置く。private の stock-price-fetcher からも呼べるように public にする。

| ファイル | 役割 |
|---|---|
| `setup-safe-chain/action.yml` | 入力 `cooldown-hours`（既定 `96`）、出力 `version` |
| `setup-safe-chain/resolve-version.sh` | draft と prerelease を除き、immutable で、公開から `cooldown-hours` 以上たった最新のリリースのタグを出力する。なければ失敗する |
| `setup-safe-chain/install.sh` | そのリリースに添付された `install-safe-chain.sh` を `gh release download` で取り、`SAFE_CHAIN_VERSION=<タグ>` を付けて `--ci` で実行する |
| `.github/workflows/test.yml` | ubuntu で Action を実行し、`safe-chain -v` の版が出力の `version` と一致することを確かめる |
| `.github/dependabot.yml`、`gitleaks.yml`、`trufflehog.yml` | `~/git/AGENTS.md` の方針どおり |

リリースのインストーラーは、`SAFE_CHAIN_VERSION` の版のバイナリを、スクリプトに埋め込まれた SHA256 で確かめる。リリースは immutable なので、公開後にタグや添付ファイルが差し替わることはない。`SAFE_CHAIN_VERSION` を指定すると glibc 版（`linux-x64`）が入るが、ubuntu のランナーでは問題ない。`--include-python` は Safe Chain 側で非推奨かつ無視されるため、入力にしない。

`v1.0.0` のタグとリリースを作る。Dependabot は呼び出し側の `# v1.0.0` をタグから更新する。

## 呼び出し側

依存のスキャン（enecoq、stock、textlint の 2 つ、zenn）と npm のリリース（textlint の 2 つ）の `Setup Aikido Safe Chain` のステップを、次に置き換える。

```yaml
      - name: Setup Aikido Safe Chain
        uses: rewse/actions/setup-safe-chain@<SHA>  # v1.0.0
```

rewse/actions を使う全リポジトリの dependabot.yml の github-actions の項目に、`cooldown.exclude: ["rewse/*"]` を足す。自分のリポジトリには cooldown をかけない。

`~/git/AGENTS.md` に次を足す: "Install Aikido Safe Chain with `rewse/actions/setup-safe-chain`, which takes the newest immutable release at least 96 hours old and verifies its checksum; do not pipe an installer from a branch into `sh`." あわせて、Dependabot の項目に `rewse/*` を cooldown から除く旨を足す。

## 検証

- `resolve-version.sh` を手元で実行し、96 時間以上前に公開された最新の immutable なリリースのタグが出る。`COOLDOWN_HOURS=100000` では失敗する
- rewse/actions の test.yml が成功する
- 呼び出し側の依存のスキャンが push で成功する。リリースのワークフローは次のリリースまで走らないため、actionlint と zizmor で代える
