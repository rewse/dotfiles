# Safe Chain の導入 Action 実装計画

**Goal:** `rewse/actions/setup-safe-chain` を作り、7 つのワークフローの `curl | sh` を置き換える。

**Spec:** `docs/superpowers/specs/2026-09-27-setup-safe-chain-action-design.md`

## Global Constraints

- `~/git/AGENTS.md` の GitHub Configuration の方針に従う（SHA 固定、`persist-credentials: false`、トップレベルの `permissions: contents: read` など）
- 共通チェック C1〜C4（actionlint、zizmor、SHA 固定、dependabot のスキーマ）が各リポジトリで通る
- 外部への書き込み（GitHub のリポジトリ作成、push）はユーザーの確認を取ってから行う。public のリポジトリへの push は fox 経由

### Task 1: rewse/actions をローカルに作る

- [ ] `~/git/actions` を `git init -b main` で作り、spec の表のファイルと `LICENSE`（MIT）、英語の `README.md` を置く
- [ ] `COOLDOWN_HOURS=96 setup-safe-chain/resolve-version.sh` が、96 時間以上前に公開された最新の immutable なタグを出すことを確かめる。`COOLDOWN_HOURS=100000` で失敗し、`COOLDOWN_HOURS=abc` でも失敗することを確かめる
- [ ] `shellcheck` と C1〜C4 が通る
- [ ] Commit: `feat: add setup-safe-chain action`

### Task 2: 公開して v1.0.0 を出す（確認のあとで行う）

- [ ] `gh repo create rewse/actions --public` で作り、fox 経由で push する
- [ ] test.yml が成功する
- [ ] `v1.0.0` のタグとリリースを作り、そのコミットの SHA を控える

### Task 3: 呼び出し側を置き換える

- [ ] 5 つの依存のスキャンと 2 つの npm のリリースで、`Setup Aikido Safe Chain` のステップを `rewse/actions/setup-safe-chain@<SHA>  # v1.0.0` に置き換える
- [ ] 7 リポジトリの dependabot.yml の github-actions の項目に `exclude: ["rewse/*"]` を足す
- [ ] `rg -n 'install-safe-chain' */.github` の出力がなく、C1〜C4 が通る
- [ ] `~/git/AGENTS.md`（chezmoi の `git/AGENTS.md`）に spec の文を足す
- [ ] 1 リポジトリ 1 コミット: `ci: install Safe Chain from an aged immutable release`

### Task 4: push と確認（確認のあとで行う）

- [ ] fox 経由で push し、ローカルを origin に合わせる
- [ ] 依存のスキャンが push で成功する。`Setup Aikido Safe Chain` のログに、選ばれた版が出る

## Review Focus

- GitHub の API の回数制限や一時的な障害で、リリースの一覧が取れない: resolve がエラーで止まり、古い値や空の値で先に進まない
- 公開から 96 時間たったリリースが 1 つもない: 失敗し、理由が分かるメッセージを出す
- `immutable` が false のリリースが最新: 飛ばして、その前の immutable なものを使う
