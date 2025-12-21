# AGENTS.md

## 言語使用ガイド

原則として、広く一般に公開される文章には英語、ユーザーのみにしか影響しないものには日本語を使用することが推奨されます:

- チャットでのコミュニケーション: 日本語
- 仕様書（Spec）: 日本語
- コード内のコメント: 英語
- コミットメッセージ: 英語
- 変数名・関数名: 英語

`README.md`の言語は未定義です。作成する前に、ユーザーに何の言語で書くべきか聞かなければなりません。

### チャットについて

#### チャットの口調について

チャットの口調は`./chat-tone-guide.md`に従わなければなりません。

#### チャットのフォーマットについて

チャットでの回答には表形式を使用してはなりません。情報を整理して伝える場合は、箇条書きや段落形式を使用する必要があります。

## コミットメッセージ規約

コミットメッセージは [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) に従わなければなりません。

## 仕様書 (Spec) について

- 仕様書 (Spec) は [RFC 2119](https://datatracker.ietf.org/doc/html/rfc2119) に従わなければなりません。
- アーキテクチャはMermaidで書かなくてはなりません。

## コーディング規約

### コーディングスタイル

コーディングスタイルは [Google Style Guides](https://google.github.io/styleguide/) に従わなければなりません。

### コメント

コメントはコードに記述できない背景や理由を説明する内容でなければなりません。または、直感的には分かりづらいコードを自然言語で説明する内容でなければなりません。コードを読めば誰でも分かる内容については、コメントを書かないほうが良いです。

## CLIコマンドガイド

Pagerが起動してしまう可能性があるコマンドは、`cat`にパイプしてPagerが起動しないようしなければなりません。

### 推奨される例

- `git diff` → `git diff | cat`
- `git log` → `git log | cat`
- `git show` → `git show | cat`

## Pythonプロジェクト規約

### ビルドシステム

`src`レイアウトを使用するプロジェクトで `uv run <command>` でコンソールスクリプトを実行する場合、以下の設定を`pyrpoject.toml`に追加しなければなりません。

```toml
[project.scripts]
my-command = "my_package.cli:main"

[build-system]
build-backend = "uv_build"

[tool.uv.build-backend]
module-root = "src"
```

#### トラブルシューティング

- WEHN `ModuleNotFoundError`が発生する THEN `.venv`を削除して `uv sync --no-editable` で再作成する

### テスト

テストには `uv run` を使用しなければなりません。

実行例: `PYTHONPATH=src uv run pytest tests/test_foo.py`
