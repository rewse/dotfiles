# 要求レベルについて
この文書における次の各キーワード「しなければならない (MUST)」、「してはならない (MUST NOT)」、「要求されている (REQUIRED)」、「することになる (SHALL)」、「することはない (SHALL NOT)」、「する必要がある (SHOULD)」、「しないほうがよい (SHOULD NOT)」、「推奨される (RECOMMENDED)」、「してもよい (MAY)」、「選択できる (OPTIONAL)」は、RFC 2119 で述べられているように解釈されるべきものです。

# 言語使用ガイドライン

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

# 要求レベルを示すキーワードのガイドライン

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

Conventional Commits の仕様はコミットメッセージのための軽量の規約です。 明示的なコミット履歴を作成するための簡単なルールを提供します。この規則に従うことで自動化ツールの導入を簡単にします。 コミットメッセージで機能追加・修正・破壊的変更などを説明することで、この規約は [SemVer](http://semver.org/lang/ja/) と協調動作します。

コミットメッセージは次のような形にする必要があります:

原文：
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

訳：
```
<型>[任意 スコープ]: <タイトル>

[任意 本文]

[任意 フッター]
```

あなたのライブラリの利用者に意図を伝えるために、コミットは以下の構造化された要素を持ちます：

1. **fix:** *型* `fix` を持つコミットはコードベースのバグにパッチを当てます (これは Semantic Versioning における [PATCH](http://semver.org/#summary) に相当します)。
1. **feat:** *型* `feat` を持つコミットはコードベースに新しい機能を追加します (これは Semantic Versioning における [MINOR](http://semver.org/#summary) に相当します)。
1. **BREAKING CHANGE:** フッター に `BREAKING CHANGE:` が書かれているか型/スコープの直後に `!` が追加されているコミットは API の破壊的変更を導入します (Semantic Versioning における [MAJOR](http://semver.org/#summary) に相当します)。 `BREAKING CHANGE` は任意の *型* のコミットに含めることができます。
1. `fix:` や `feat:` 以外の *型* も許されています。たとえば [@commitlint/config-conventional](https://github.com/conventional-changelog/commitlint/tree/master/%40commitlint/config-conventional) (これは [Angular の規約](https://github.com/angular/angular/blob/22b96b9/CONTRIBUTING.md#-commit-message-guidelines) が基になっています) は `build:`, `chore:`, `ci:`,`docs:`, `style:`, `refactor:`, `perf:`, `test:`, などを推奨しています。
1. [git trailer format](https://git-scm.com/docs/git-interpret-trailers) に似た規約に従って、`BREAKING CHANGE: <タイトル>` 以外の フッター が与えられるかもしれません。

## 型の特徴
- `feat`: 新機能の追加（SemVerのMINORに相当）
- `fix`: バグ修正（SemVerのPATCHに相当）
- `build`: ビルドシステムや外部依存関係に影響する変更
- `chore`: ビルドプロセスや補助ツールの変更、依存関係の更新
- `ci`: CI設定ファイルやスクリプトの変更
- `docs`: ドキュメントの変更
- `style`: コードの意味に影響しない変更（フォーマット、セミコロンの欠落など）
- `refactor`: バグ修正でも機能追加でもないコード変更
- `perf`: パフォーマンス改善
- `test`: テストの追加や更新

追加の型たちは Conventional Commits の仕様で義務付けられているものではなく、(BREAKING CHANGE を含まない限り) Semantic Versioning に対する暗黙的な効果を持ちません。

コミットの型には追加の文脈の情報として スコープ を追加することができます。スコープは括弧で囲みます。たとえば `feat(parser): add ability to parse arrays` のようになります。

## Conventional Commits 1.0.0 仕様からの拡張
- コミットタイトル (1行目) の型は小文字から始める（MUST）

## 例

### タイトルおよび破壊的変更のフッターを持つコミットメッセージ
```
feat: allow provided config object to extend other configs

BREAKING CHANGE: `extends` key in config file is now used for extending other config files
```

### 破壊的変更を目立たせるために ! を持つコミットメッセージ
```
feat!: send an email to the customer when a product is shipped
```

### スコープおよび破壊的変更を目立たせるための ! を持つコミットメッセージ
```
feat(api)!: send an email to the customer when a product is shipped
```

### ! と BREAKING CHANGE フッターの両方を持つコミットメッセージ
```
chore!: drop support for Node 6

BREAKING CHANGE: use JavaScript features not available in Node 6.
```

### 本文を持たないコミットメッセージ
```
docs: correct spelling of CHANGELOG
```

### スコープを持つコミットメッセージ
```
feat(lang): add polish language
```

### 複数段落からなる本文と複数のフッターを持ったコミットメッセージ
```
fix: prevent racing of requests

Introduce a request id and a reference to latest request. Dismiss
incoming responses other than from latest request.

Remove timeouts which were used to mitigate the racing issue but are
obsolete now.

Reviewed-by: Z
Refs: #123
```

## 仕様
この文書におけるキーワード「しなければならない (MUST)」「してはならない (MUST NOT)」「要求されている (REQUIRED)」「することになる (SHALL)」「することはない(SHALL NOT)」「する必要がある (SHOULD)」「しないほうがよい (SHOULD NOT)」「推奨される (RECOMMENDED)」「してもよい (MAY)」「選択できる (OPTIONAL)」は [RFC 2119](https://www.ietf.org/rfc/rfc2119.txt) ([JPNIC 日本語訳](https://www.nic.ad.jp/ja/tech/ipa/RFC2119JA.html)) で述べられているように解釈されるべきものです。

1. コミットは `feat` や `fix` などの型から始まり (MUST)、その後ろにはスコープ (OPTIONAL) と `!` (OPTIONAL) が続き、その後ろにコロンとスペース (REQUIRED) が続く。
1. コミットがあなたのアプリケーションやライブラリに新しい機能を追加するとき、型 `feat` が使われなければならない (MUST)。
1. コミットがあなたのアプリケーションのためのバグ修正を行うとき、型 `fix` が使われなければならない (MUST)。
1. スコープを型の後ろに記述してもよい (MAY)。スコープは、コードベースのセクションを記述する括弧で囲まれた名詞にしなければならない (MUST)。例: `fix(parser):`。
1. 型/スコープの後ろのコロンとスペースの直後にタイトルが続かなければならない (MUST)。 タイトルはコード変更の短かい要約である。例: `fix: array parsing issue when multiple spaces were contained in string`。
1. 短いタイトルの後ろにより長いコミットの本文を追加してもよい (MAY)。これはコード変更に関する追加の情報を提供する。 本文はタイトルの下の 1 行の空行から始めなければならない (MUST)。
1. コミットの本文は自由な形式であり、改行で区切られた複数の段落で構成することができる (MAY)。
1. ひとつ以上のフッターを、本文の下の 1 行の空行に続けて書くことができる (MAY)。 それぞれのフッターは、ひとつの単語トークン、それに続く `:<space>` か `<space>#` によるセパレータ、そして文字列の値から構成されなければならない (MUST) (これは [git trailer convention](https://git-scm.com/docs/git-interpret-trailers) に触発されている)。
1. フッターのトークンは空白の代わりに - を使わなければならない (MUST)。例えば `Acked-by` とする (これは複数段落からなる本文からフッターを区別するのに役立つ)。 例外として `BREAKING CHANGE` があり、これをトークンとして使用することができる (MAY)。
1. フッターの値にはスペースと改行を含めることができる (MAY)。そして次のフッターのトークンとセパレータの組が見つかった時、以前のフッターのパースは終了しなければならない (MUST)。
1. 破壊的変更は、コミットの型/スコープの接頭辞か、フッターによって明示されなければならない (MUST)。
1. 破壊的変更がフッターとして含まれる場合は、大文字の BREAKING CHANGE の後ろにコロンとスペース、そしてタイトルを続けなければならない (MUST)。例: `BREAKING CHANGE: environment variables now take precedence over config files`。
1. 破壊的変更が型/スコープの接頭辞として含まれる場合は、`:` の直前に `!` を用いて明示されねばならない (MUST)。! が使用された場合には、 フッターから `BREAKING CHANGE:` を省略してもよい (MAY)。その場合はコミットのタイトル部分で破壊的変更の内容を説明することになる (SHALL)。
1. `feat` と `fix` 以外の型を使うことができる (MAY)。例: `docs: updated ref docs.`。
1. Conventional Commits を構成する情報の単位は、大文字の `BREAKING CHANGE` を除いて、実装は大文字と小文字を区別してはならない (MUST NOT)。
1. フッターのトークンにおいて `BREAKING-CHANGE` は `BREAKING CHANGE` と同じトークンとして解釈されなければならない (MUST)。

## よくある質問

### Conventional Commits はrevertコミットをどのように扱いますか？
我々のおすすめの方法としては、ひとつは`revert`型と revertされるコミットの SHA を参照するフッターを使うようにすることです。

```
revert: let us never again speak of the noodle incident

Refs: 676104e, a215868
```
