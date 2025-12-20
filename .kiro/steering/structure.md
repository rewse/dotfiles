# プロジェクト構造

## ディレクトリ構成

```
.
├── README.md                           # プロジェクトドキュメントとセットアップ手順
├── LICENSE                             # プロジェクトライセンスファイル
├── .gitignore                          # Git無視パターン
├── .chezmoiignore                      # chezmoi操作中に無視するファイル
├── .chezmoitemplates/                  # 共有テンプレート
├── dot_zshrc.tmpl                      # OS固有ロジック付きZshシェル設定
├── dot_gitconfig.tmpl                  # テンプレート付きGit設定
├── dot_vimrc.tmpl                      # Vimエディタ設定
├── dot_npmrc                           # NPM設定
├── private_dot_ssh/                    # SSHキーと設定（0600権限）
├── private_Library/                    # macOS固有のアプリケーションサポートファイル
├── dot_config/                         # XDG Base Directory準拠の設定
└── dot_kiro/                           # Kiro CLIとAIアシスタント設定

```

### プラットフォーム固有ファイル
- ファイルはOS固有の動作にchezmoiの条件テンプレートを使用
- 共通パターン: macOS用の `{{ if eq .chezmoi.os "darwin" }}`
- 異なるマシン用のホスト名固有設定

## ファイル命名パターン

### chezmoi属性
- `dot_`: `.filename` になる（隠しファイル）
- `private_`: 0600権限を取得（セキュアファイル）
- `executable_`: 実行権限を取得
- `.tmpl`: chezmoiによって処理されるテンプレートファイル

### テンプレート変数
- `.chezmoi.os`: オペレーティングシステム（darwin/linux）
- `.chezmoi.hostname`: マシン固有設定用のマシンホスト名
- `onepasswordRead`: シークレットを安全に取得する関数

## 主要なアーキテクチャ決定

1. **クロスプラットフォームサポート**: すべての設定がmacOSとLinuxの両方に対応
2. **セキュリティファースト**: 1Password統合による機密データ管理
3. **モジュラーテンプレート**: `.chezmoitemplates/` の共有コンポーネント
4. **XDG準拠**: モダンな設定ファイル構成
5. **AI統合**: Kiro AIアシスタントワークフローの組み込みサポート
