# 依存パッケージアップデートプロンプト

以下のプロジェクトの依存パッケージをアップデートしてください：

## 1. enecoq-data-fetcher (Python/uv)
- パス: `/Users/tats/Documents/git/enecoq-data-fetcher`
- パッケージマネージャ: uv
- 手順:
  1. `uv lock --upgrade --dry-run` を実行して更新するパッケージを表示
  2. `uv lock --upgrade` を実行して依存関係を更新
  3. 更新内容を確認
  4. `./tests/run_tests.sh` を実行してテスト
  5. 変更をコミット

## 2. stock-price-fetcher (Python/uv)
- パス: `/Users/tats/Documents/git/stock-price-fetcher`
- パッケージマネージャ: uv
- 手順:
  1. `uv lock --upgrade --dry-run` を実行して更新するパッケージを表示
  2. `uv lock --upgrade` を実行して依存関係を更新
  3. 更新内容を確認
  4. `PYTHONPATH=src uv run pytest tests/ -v` を実行してテスト
  5. 変更をコミット

## 3. textlint-config-rewse (Node.js/npm)
- パス: `/Users/tats/Documents/git/textlint-config-rewse`
- パッケージマネージャ: npm
- 手順:
  1. `npm outdated` を実行して更新するパッケージを表示
  2. `npm update` を実行して依存関係を更新
  3. `npm outdated` を再度実行して更新内容を確認
  4. `npm test` を実行してテスト
  5. 変更をコミット

## 4. textlint-rule-ja-space-around-phrase (Node.js/npm)
- パス: `/Users/tats/Documents/git/textlint-rule-ja-space-around-phrase`
- パッケージマネージャ: npm
- 手順:
  1. `npm outdated` を実行して更新するパッケージを表示
  2. `npm update` を実行して依存関係を更新
  3. `npm outdated` を再度実行して更新内容を確認
  4. `npm test` を実行してテスト
  5. 変更をコミット

## 5. zenn-content (Node.js/npm)
- パス: `/Users/tats/Documents/git/zenn-content`
- パッケージマネージャ: npm
- 手順:
  1. `npm outdated` を実行して更新するパッケージを表示
  2. `npm update` を実行して依存関係を更新
  3. `npm outdated` を再度実行して更新内容を確認
  4. 変更をコミット

## 6. git push
- 手順:
  1. 全てのプロジェクトで `git push` を実行して変更をプッシュ
  2. 1分待つ
  3. 全てのプロジェクトで `gh run list` を実行して GitHub Actions が成功していることを確認

## 注意事項
- 破壊的変更がある場合は適切に対応しなければなりません (MUST)
- コミットメッセージは Conventional Commits に従がわなけれなりません (MUST)（例: `chore: update dependencies`）
- テストでエラーが発生した場合は、エラーの内容を説明し、エラーを無視して良いか尋ねなければなりません(MUST)
