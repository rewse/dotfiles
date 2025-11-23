# 技術スタック

## 要求レベルについて
この文書における次の各キーワード「しなければならない (MUST)」、「してはならない (MUST NOT)」、「要求されている (REQUIRED)」、「することになる (SHALL)」、「することはない (SHALL NOT)」、「する必要がある (SHOULD)」、「しないほうがよい (SHOULD NOT)」、「推奨される (RECOMMENDED)」、「してもよい (MAY)」、「選択できる (OPTIONAL)」は、RFC 2119 で述べられているように解釈されるべきものです。

## コア技術

### ドットファイル管理
- **chezmoi**: ドットファイル管理ツール（テンプレート機能を活用）
- **1Password CLI (op)**: 秘密情報の安全な管理

## プラットフォーム

- **macOS**: Homebrew を使用したパッケージ管理
- **Linux**: apt などのネイティブパッケージマネージャー

## 共通コマンド

### chezmoi 操作

```bash
# ファイルを追加
chezmoi add <file>

# ファイルを編集
chezmoi edit <file>

# 変更を確認
chezmoi diff | cat

# 変更を適用
chezmoi apply

# ドライラン（実際には適用しない）
chezmoi apply --dry-run --verbose | cat

# ソースディレクトリに移動
chezmoi cd

# 外部ファイルを強制更新
chezmoi apply --refresh-externals

# テンプレートデータを表示
chezmoi data

# テンプレートをテスト
chezmoi execute-template

# 状態をクリア（スクリプト再実行用）
chezmoi state delete-bucket --bucket=entryState  # run_onchange_
chezmoi state delete-bucket --bucket=scriptState # run_once_
```

## 設定ファイルの場所

- **chezmoi 設定**: `~/.config/chezmoi/chezmoi.toml`

## テンプレート変数

chezmoi テンプレート内で使用可能な変数:

- `.chezmoi.os`: オペレーティングシステム（`darwin` または `linux`）
- `.chezmoi.hostname`: ホスト名
- `.email`: ユーザーのメールアドレス（`chezmoi.toml` で設定）

## 秘密情報の管理

### 1Password CLI の使用

1Password CLI を使用して秘密情報を取得します:

```
{{ onepasswordRead "op://Private/ServiceName/credential" }}
```

### Service Account の設定

CI/CD 環境や自動化スクリプトで 1Password を使用する場合、Service Account を使用できます。

#### Service Account の作成

1. [1Password の Web アプリ](https://my.1password.com/developer-tools/active/service-accounts)にログイン
2. Settings > Developer > Service Accounts に移動
3. "Create Service Account" をクリック
4. Service Account に名前を付ける（例: "chezmoi-automation"）
5. 必要な Vault へのアクセス権限を付与（注: Private vault は Service Account に使用できません）
6. トークンをコピーして安全に保存（このトークンは一度しか表示されません）

**重要**: Service Account は Private vault にアクセスできません (MUST NOT)。Service Account で使用する秘密情報は、共有 Vault に保存する必要があります (MUST)。

#### chezmoi での設定

`chezmoi.toml` に以下の設定を追加することで、`OP_SERVICE_ACCOUNT_TOKEN` 環境変数を使用した認証が有効になります:

```toml
[onepassword]
    mode = "service-account"
```

この設定により、対話的なログインなしで 1Password の秘密情報にアクセスできます。Service Account トークンは環境変数 `OP_SERVICE_ACCOUNT_TOKEN` に設定する必要があります (MUST)。

#### 使用例

```bash
# 環境変数にトークンを設定
export OP_SERVICE_ACCOUNT_TOKEN="ops_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# chezmoi を実行
chezmoi apply
```
