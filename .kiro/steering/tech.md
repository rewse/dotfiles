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

1Password CLI を使用して秘密情報を取得します:

```
{{ onepasswordRead "op://Private/ServiceName/credential" }}
```
