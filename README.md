# Dotfiles

chezmoi を使用した個人用ドットファイル管理システムです。複数マシン（macOS と Linux）間でシェル設定、エディタ設定、Git 設定などを一元管理します。

## 特徴

- **クロスプラットフォーム対応**: macOS と Linux の両方に対応
- **テンプレートベース**: マシン固有の設定を条件分岐で管理
- **セキュアな秘密情報管理**: 1Password との統合により API キーやクレデンシャルを安全に管理

## セットアップ

### 新しいマシンでのインストール

#### macOS (Homebrew)

```bash
# chezmoi をインストール
brew install chezmoi

# ドットファイルを初期化して適用
chezmoi init --apply <your-github-username>
```

#### Linux

```bash
# chezmoi をインストールしてドットファイルを初期化・適用
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply <your-github-username>
```

または、chezmoi のみをインストール:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)"
```

### 既存の chezmoi がある場合

```bash
chezmoi init <your-github-username>
chezmoi apply
```

## 使い方

### 日常的な操作

```bash
# ファイルを追加
chezmoi add ~/.zshrc

# ファイルを編集
chezmoi edit ~/.zshrc

# 変更を確認
chezmoi diff | cat

# 変更を適用
chezmoi apply

# ドライラン
chezmoi apply --dry-run --verbose | cat
```

### リモートとの同期

```bash
# 最新の変更を取得して適用
chezmoi update
```

## 構成

### ディレクトリ構造

```
.
├── .chezmoitemplates/          # 共有テンプレート（他のテンプレートから include 可能）
├── .kiro/                      # Kiro 関連設定
│   └── steering/               # AI アシスタント用ガイドライン
├── dot_config/                 # XDG Base Directory 準拠の設定
├── dot_kiro/                   # Kiro CLI 設定とステアリングルール
├── dot_vim/                    # Vim 設定
├── dot_*                       # その他のドットファイル（zshrc、gitconfig など）
├── private_dot_ssh/            # SSH 鍵と設定（プライベート属性 0600）
├── private_*                   # その他のプライベートファイル
├── *.tmpl                      # テンプレートファイル（chezmoi が処理）
└── *.example                   # 設定例ファイル
```

### テンプレート変数

`chezmoi.toml` で設定:

```toml
[data]
    email = "email@example.com"
```

## 必要な環境

- [chezmoi](https://www.chezmoi.io/)
- [1Password CLI](https://developer.1password.com/docs/cli/) (秘密情報管理用)
- macOS: Homebrew
- Linux: apt などのパッケージマネージャー
