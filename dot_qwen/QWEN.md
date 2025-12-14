# 要求レベルについて
この文書における次の各キーワード「しなければならない (MUST)」、「してはならない (MUST NOT)」、「要求されている (REQUIRED)」、「することになる (SHALL)」、「することはない (SHALL NOT)」、「する必要がある (SHOULD)」、「しないほうがよい (SHOULD NOT)」、「推奨される (RECOMMENDED)」、「してもよい (MAY)」、「選択できる (OPTIONAL)」は、RFC 2119 で述べられているように解釈されるべきものです。

# 言語使用標準

## 基本方針
このプロジェクトでは、以下の言語使用ポリシーに従なければなりません (MUST)。

- **コード内のコメント**: 英語
- **チャットでのコミュニケーション**: 日本語
- **仕様書（Spec）**: 日本語
- **ドキュメント**: 日本語
- **コミットメッセージ**: 英語
- **変数名・関数名**: 英語

## 詳細ガイドライン

### コード内コメント（英語）
コード内のコメントは、国際的な開発環境との互換性を保つため、すべて英語で記述しなければなりません (MUST)。

### チャットコミュニケーション（日本語）
チャットやコミュニケーションは日本語で行わなければなりません (MUST)。技術的な質問、回答、説明などはすべて日本語で提供しなければなりません (MUST)。

#### フォーマットについて
チャットでの回答には表形式（Markdownテーブル）を使用してはなりません (MUST NOT)。情報を整理して伝える場合は、箇条書きや段落形式を使用する必要があります (SHOULD)。

### 仕様書（日本語）
プロジェクトの仕様書、要件定義、設計ドキュメントなどは日本語で作成しなければなりません (MUST)。

### ドキュメント（日本語）
READMEファイル、使用方法の説明、トラブルシューティングガイドなどのドキュメントは日本語で作成しなければなりません (MUST)。

### コミットメッセージ（英語）
Gitのコミットメッセージは、一般的な慣習に従って英語で記述しなければなりません (MUST)。

### 変数名・関数名（英語）
コード内の変数名、関数名、ロール名などは、標準的な開発慣習に従って英語で命名しなければなりません (MUST)。

# 要求レベルを示すキーワード標準

## 概要
このプロジェクトのドキュメントや仕様書において、要求レベルを示すキーワードは RFC 2119 に準拠して使用してください。

## キーワードの定義

### 1. しなければならない (MUST)
- **同義語**: 要求されている (REQUIRED) 、することになる (SHALL)
- **意味**: その規定が当該仕様の絶対的な要請事項であることを意味する
- **使用例**: 「パスワードは8文字以上でなければならない (MUST)」

### 2. してはならない (MUST NOT) 
- **同義語**: することはない (SHALL NOT)
- **意味**: その規定が当該仕様の絶対的な禁止事項であることを意味する
- **使用例**: 「平文でパスワードを保存してはならない (MUST NOT)」

### 3. する必要がある (SHOULD)
- **同義語**: 推奨される (RECOMMENDED)
- **意味**: 特定の状況下では無視する正当な理由が存在するかもしれないが、異なる選択をする前に、当該項目の示唆するところを十分に理解し、慎重に重要性を判断しなければならない
- **使用例**: 「エラーログは構造化された形式で出力する必要がある (SHOULD)」

### 4. しないほうがよい (SHOULD NOT)
- **同義語**: 推奨されない (NOT RECOMMENDED)
- **意味**: 特定の状況下では正当な理由が存在するかもしれないが、この動作を実装する前に、当該項目の示唆するところを十分に理解し、慎重に重要性を判断しなければならない
- **使用例**: 「本番環境でデバッグモードを有効にしないほうがよい (SHOULD NOT)」

### 5. してもよい (MAY)
- **同義語**: 選択できる (OPTIONAL)
- **意味**: ある要素がまさに選択的であることを意味する
- **使用例**: 「ユーザーは二段階認証を有効にしてもよい (MAY)」

## 使用上の注意

### 慎重な使用
これらの命令的語句は注意して使用し、使いすぎないようにしてください：
- 相互運用性確保のために不可欠である場合に使用する
- 有害である可能性がある動作を制限するために使用する
- 実装者に特定の手法を強制するために不必要に使用しない

### セキュリティへの配慮
セキュリティに関連する要求事項を記述する際は、特に注意が必要です：
- MUST や SHOULD となっている事項を実装しないことの影響を考慮する
- MUST NOT や SHOULD NOT としている事項を実装してしまうことの影響を考慮する
- 推奨事項や要請事項に従わなかった場合のセキュリティへの影響を明確に記述する

## 表記ルール

### 日本語ドキュメント
- 日本語の訳語を使用し、括弧内に英語の原語を併記する
- 例: 「しなければならない (MUST)」

### 英語ドキュメント
- 英語のキーワードは大文字で表記する
- 例: MUST, SHOULD, MAY

## 参考文献
- [RFC 2119 - Key words for use in RFCs to Indicate Requirement Levels](https://www.ietf.org/rfc/rfc2119.txt)
- [RFC 2119 日本語訳 (JPNIC) ](https://www.nic.ad.jp/ja/tech/ipa/RFC2119JA.html) 

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
- 最初の文字を大文字にしないほうがよい (SHOULD NOT)
- 末尾にピリオドを付けないほうがよい (SHOULD NOT)

## 本文 (Body)

- 短いタイトルの後ろにより長いコミットの本文を追加してもよい (MAY)
- 本文はタイトルの下の 1 行の空行から始めなければなりません (MUST)
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
