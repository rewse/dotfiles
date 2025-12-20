# 技術スタック

## コア技術

- **chezmoi**: テンプレート機能付きのdotfiles管理ツール
- **1Password CLI**: セキュアなシークレット管理
- **Shell**: クロスプラットフォーム対応のZsh
- **Git**: dotfilesのバージョン管理

## テンプレートシステム

- chezmoiの変数を使ったGoテンプレート構文を使用
- OS基準の条件分岐 (`{{ if eq .chezmoi.os "darwin" }}`)
- ホスト名固有の設定 (`{{ if eq .chezmoi.hostname "..." }}`)
- 1Password統合 (`{{ onepasswordRead "op://..." }}`)

## 主要な依存関係

- **Kiro CLI**: AI アシスタント統合
- **direnv**: 環境変数管理 (macOS)
- **bat/batcat**: 拡張ファイル表示
- **zsh-vi-mode**: シェル用Viキーバインド
- **op**: 1Password CLIツール

## よく使うコマンド

### 初期セットアップ
```bash
# chezmoiをインストールしてdotfilesを適用
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply <username>

# またはmacOSでHomebrewを使用
brew install chezmoi
chezmoi init --apply <username>
```

### 日常的な操作
```bash
# 新しいファイルを管理対象に追加
chezmoi add ~/.filename

# 管理されているファイルを編集
chezmoi edit ~/.filename

# 何が変更されるかを確認
chezmoi diff | cat

# 変更を適用
chezmoi apply

# 変更をプレビューするドライラン
chezmoi apply --dry-run --verbose | cat

# リモートリポジトリと同期
chezmoi update
```

### 開発ワークフロー
```bash
# テンプレートを直接編集
chezmoi edit --apply ~/.zshrc

# 変更後にテンプレートを再実行
chezmoi apply

# テンプレート構文をチェック
chezmoi execute-template < template-file
```

## ファイル命名規則

- `dot_*`: ホームディレクトリで `.filename` になるファイル
- `private_*`: 制限された権限 (0600) を持つファイル
- `*.tmpl`: chezmoiによって処理されるテンプレートファイル
- `executable_*`: 実行可能にすべきファイル
