---
inclusion: always
---

# コミットメッセージ標準

## 概要

このプロジェクトでは [Conventional Commits 1.0.0](https://www.conventionalcommits.org/ja/v1.0.0/) に準拠したコミットメッセージを使用しなければなりません (MUST)。

## コミットメッセージの形式

```
<型>[任意 スコープ]: <タイトル>

[任意 本文]

[任意 フッター]
```

## 型 (Type)

コミットは以下の型から始まらなければなりません (MUST):

- `feat`: 新しい機能を追加するとき (SemVer の MINOR に相当)
- `fix`: バグ修正を行うとき (SemVer の PATCH に相当)
- `docs`: ドキュメントのみの変更
- `style`: コードの意味に影響しない変更（空白、フォーマット、セミコロンの欠落など）
- `refactor`: バグ修正でも機能追加でもないコード変更
- `perf`: パフォーマンスを向上させるコード変更
- `test`: テストの追加・修正
- `build`: ビルドシステムや外部依存関係に影響する変更
- `ci`: CI 設定ファイルやスクリプトの変更
- `chore`: その他の変更（ソースやテストファイルを変更しない）
- `revert`: 以前のコミットを取り消す

## スコープ (Scope)

型の後ろにスコープを記述してもよい (MAY)。スコープはコードベースのセクションを記述する括弧で囲まれた名詞にしなければなりません (MUST)。

例: `feat(zsh):`, `fix(vim):`, `docs(readme):`

## タイトル (Description)

- 型/スコープの後ろのコロンとスペースの直後にタイトルが続かなければなりません (MUST)
- タイトルはコード変更の短い要約にする必要があります (SHOULD)
- 命令形、現在形を使用する必要があります (SHOULD)（例: "change" であり "changed" や "changes" ではない）
- 最初の文字を小文字にしたほうがよい (SHOULD)
- 末尾にピリオドを付けないほうがよい (SHOULD NOT)

## 本文 (Body)

- 短いタイトルの後ろにより長いコミットの本文を追加してもよい (MAY)
- 本文はタイトルの下の1行の空行から始めなければなりません (MUST)
- コミットの本文は自由な形式であり、改行で区切られた複数の段落で構成することができます (MAY)

## フッター (Footer)

- ひとつ以上のフッターを、本文の下の 1 行の空行に続けて書くことができます (MAY)
- フッターのトークンは空白の代わりに `-` を使わなければなりません (MUST)（例: `Acked-by`, `Reviewed-by`）
- 例外として `BREAKING CHANGE` はトークンとして使用することができます (MAY)

## 破壊的変更 (Breaking Changes)

破壊的変更は以下のいずれかの方法で明示しなければなりません (MUST):

1. フッターに `BREAKING CHANGE:` を記述する
2. 型/スコープの直後、コロンの直前に `!` を付ける

例:
```
feat!: send an email to the customer when a product is shipped
```

```
feat(api)!: send an email to the customer when a product is shipped
```

```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

## コミットメッセージの例

### シンプルなコミット
```
docs: correct spelling of CHANGELOG
```

### スコープ付きコミット
```
feat(zsh): add alias for chezmoi commands
```

### 本文付きコミット
```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.
```

### 破壊的変更を含むコミット
```
chore!: drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.
```

### revert コミット
```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```

## 参考文献

- [Conventional Commits 1.0.0](https://www.conventionalcommits.org/ja/v1.0.0/)
- [Angular Commit Message Guidelines](https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#-commit-message-guidelines)
