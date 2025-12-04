# 依存パッケージアップデートプロンプト

以下の3つのプロジェクトの依存パッケージをアップデートしてください：

## 1. enecoq-data-fetcher (Python/uv)
- パス: `/Users/tats/Documents/git/enecoq-data-fetcher`
- パッケージマネージャ: uv
- 手順:
  1. `uv lock --upgrade --dery-run` を実行して更新するパッケージを表示
  2. `uv lock --upgrade` を実行して依存関係を更新
  3. 更新内容を確認
  4. `./tests/run_tests.sh` を実行してテスト
  5. 変更をコミット

## 2. textlint-config-rewse (Node.js/npm)
- パス: `/Users/tats/Documents/git/textlint-config-rewse`
- パッケージマネージャ: npm
- 手順:
  1. `npm list` を実行して現在のパッケージを表示
  2. `npm update` を実行して依存関係を更新
  3. `npm list` を実行して現在のパッケージを表示し、更新内容を確認
  4. `npm test` を実行してテスト
  5. 変更をコミット

## 3. textlint-rule-ja-space-around-phrase (Node.js/npm)
- パス: `/Users/tats/Documents/git/textlint-rule-ja-space-around-phrase`
- パッケージマネージャ: npm
- 手順:
  1. `npm list` を実行して現在のパッケージを表示
  2. `npm update` を実行して依存関係を更新
  3. `npm list` を実行して現在のパッケージを表示し、更新内容を確認
  4. `npm test` を実行してテスト
  5. 変更をコミット

## 4. zenn-content (Node.js/npm)
- パス: `/Users/tats/Obsidian/zenn-content`
- パッケージマネージャ: npm
- 手順:
  1. `npm list` を実行して現在のパッケージを表示
  2. `npm update` を実行して依存関係を更新
  3. `npm list` を実行して現在のパッケージを表示し、更新内容を確認
  5. 変更をコミット

## 注意事項
- 破壊的変更がある場合は適切に対応してください
- コミットメッセージは Conventional Commits に従ってください（例: `chore: update dependencies`）
