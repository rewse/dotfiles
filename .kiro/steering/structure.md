# プロジェクト構造

## 要求レベルについて
この文書における次の各キーワード「しなければならない (MUST)」、「してはならない (MUST NOT)」、「要求されている (REQUIRED)」、「することになる (SHALL)」、「することはない (SHALL NOT)」、「する必要がある (SHOULD)」、「しないほうがよい (SHOULD NOT)」、「推奨される (RECOMMENDED)」、「してもよい (MAY)」、「選択できる (OPTIONAL)」は、RFC 2119 で述べられているように解釈されるべきものです。

## ディレクトリ構造

```
.
├── .chezmoitemplates/            # 共有テンプレート（他のテンプレートから include 可能）
├── .kiro/                        # Kiro 関連設定
│   └── steering/                 # AI アシスタント用ガイドライン
├── dot_config/                   # XDG Base Directory 準拠の設定
│   └── chezmoi/                  # chezmoi 設定と設定例
│       └── chezmoi.toml.example  # 設定例ファイル
├── dot_kiro/                     # Kiro CLI 設定とステアリングルール
├── dot_vim/                      # Vim 設定
├── dot_*                         # その他のドットファイル（zshrc、gitconfig など）
├── private_dot_ssh/              # SSH 鍵と設定（プライベート属性 0600）
├── private_*                     # その他のプライベートファイル
└── *.tmpl                        # テンプレートファイル（chezmoi が処理）
```

## ファイル命名規則

chezmoi の命名規則に従います:

- `dot_`: `.` で始まるファイル（例: `dot_zshrc` → `~/.zshrc`）
- `private_`: パーミッション 0600 のファイル
- `.tmpl`: テンプレートとして処理されるファイル
- `executable_`: 実行可能ファイル

## テンプレートの使用

### 共有テンプレート
`.chezmoitemplates/` ディレクトリ内のファイルは他のテンプレートから include できます:

```
{{- include ".chezmoitemplates/vim-keymappings" -}}
{{- template "mcp-servers.json.tmpl" . -}}
```

### プラットフォーム固有の設定
テンプレート内で OS を判定して条件分岐します:

```
{{- if eq .chezmoi.os "darwin" }}
# macOS 用の設定
{{- else if eq .chezmoi.os "linux" }}
# Linux 用の設定
{{- end }}
```

## 設定の適用順序

### Zsh の読み込み順序
1. `.zprofile`: ログインシェル起動時（環境変数、PATH）
2. `.zshrc`: 対話シェル起動時（エイリアス、プロンプト）

## ベストプラクティス

- テンプレート変数は `chezmoi.toml` の `[data]` セクションで定義する必要がある (SHOULD)
- 秘密情報は 1Password CLI を使用して管理しなければならない (MUST)
- プラットフォーム固有の設定は条件分岐で管理する必要がある (SHOULD)
- 共通のテンプレート部品は `.chezmoitemplates/` に配置する必要がある (SHOULD)
- SSH 鍵などの機密ファイルには `private_` プレフィックスを使用しなければならない (MUST)
