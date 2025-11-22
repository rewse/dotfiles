---
inclusion: always
---

# chezmoi ユーザーガイド

## 概要

chezmoi は複数マシン間でドットファイルを管理するためのツールです。テンプレート機能を使用して、マシン固有の設定を柔軟に管理できます。

## 公式ドキュメント

- [Command Overview](https://www.chezmoi.io/user-guide/command-overview/)
- [Setup](https://www.chezmoi.io/user-guide/setup/)
- [Daily Operations](https://www.chezmoi.io/user-guide/daily-operations/)
- [Manage Different Types of File](https://www.chezmoi.io/user-guide/manage-different-types-of-file/)
- [Include Files from Elsewhere](https://www.chezmoi.io/user-guide/include-files-from-elsewhere/)
- [Manage Machine-to-Machine Differences](https://www.chezmoi.io/user-guide/manage-machine-to-machine-differences/)
- [Use Scripts to Perform Actions](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/)
- [Templating](https://www.chezmoi.io/user-guide/templating/)

## ディレクトリ構造

- **ソースディレクトリ**: `~/.local/share/chezmoi` - すべてのマシンで共通のドットファイルリポジトリのクローン
- **設定ファイル**: `~/.config/chezmoi/chezmoi.toml` (JSON、YAML も使用可能) - ローカルマシン固有の設定

## 基本コマンド

### 日常的な操作

- `chezmoi add $FILE` - ホームディレクトリのファイルをソースディレクトリに追加
- `chezmoi edit $FILE` - ソースディレクトリのファイルをエディタで編集
- `chezmoi edit --apply $FILE` - 編集後に自動的に適用
- `chezmoi edit --watch $FILE` - 保存時に自動的に適用
- `chezmoi status` - 変更されるファイルの概要を表示
- `chezmoi diff` - 適用される変更の詳細を表示
- `chezmoi apply` - ソースディレクトリからドットファイルを更新
- `chezmoi cd` - ソースディレクトリでサブシェルを開く

### ページャーを使用するコマンドの注意点

`chezmoi diff` などの一部のコマンドはデフォルトでページャー（`less` など）を使用します。自動化スクリプトや CI/CD 環境で実行する場合は、ページャーが起動してプロセスがブロックされることを避けるため、`cat` にパイプする必要があります (MUST)。

```bash
# 自動化環境での使用例
chezmoi diff | cat
chezmoi apply --dry-run --verbose | cat
```

### 複数マシン間での同期

- `chezmoi init $GITHUB_USERNAME` - GitHub からドットファイルをクローン
- `chezmoi init --apply $GITHUB_USERNAME` - クローンして即座に適用
- `chezmoi update` - リモートリポジトリから最新の変更を取得して適用

### テンプレート関連

- `chezmoi data` - 利用可能なテンプレートデータを表示
- `chezmoi add --template $FILE` - ファイルをテンプレートとして追加
- `chezmoi chattr +template $FILE` - 既存ファイルをテンプレート化
- `chezmoi cat $FILE` - ファイルの最終的な内容を表示（適用はしない）
- `chezmoi execute-template` - テンプレートのテストとデバッグ

## テンプレート機能

### 基本構文

テンプレートアクションは `{{` と `}}` で囲みます。

```
{{ .chezmoi.hostname }}
```

### 条件分岐

```
{{ if eq .chezmoi.os "darwin" }}
# macOS 用の設定
{{ else if eq .chezmoi.os "linux" }}
# Linux 用の設定
{{ else }}
# その他の OS 用の設定
{{ end }}
```

### 空白の削除

`{{-` と `-}}` を使用して前後の空白を削除できます。

```
HOSTNAME={{- .chezmoi.hostname }}
```

### テンプレート変数

- `.chezmoi.os` - オペレーティングシステム
- `.chezmoi.arch` - アーキテクチャ
- `.chezmoi.hostname` - ホスト名
- `.chezmoi.username` - ユーザー名
- `.chezmoi.sourceDir` - ソースディレクトリのパス

設定ファイル (`chezmoi.toml`) の `[data]` セクションで独自の変数を定義できます。

```toml
[data]
    email = "me@home.org"
```

テンプレート内で使用:

```
[user]
    email = {{ .email | quote }}
```

### `.chezmoitemplates` の使用

共通のテンプレートを `.chezmoitemplates` ディレクトリに配置し、他のテンプレートから呼び出せます。

```
{{- template "part.tmpl" . -}}
```

## ファイル管理

### ファイル名の属性

- `dot_` - `.` で始まるファイル
- `private_` - パーミッション 0600
- `executable_` - 実行可能ファイル
- `readonly_` - 読み取り専用
- `symlink_` - シンボリックリンク
- `create_` - 存在しない場合のみ作成
- `modify_` - ファイルの一部を変更するスクリプト
- `empty_` - 空ファイル
- `.tmpl` - テンプレートとして処理

### `.chezmoiignore`

特定のマシンでファイルを無視するには `.chezmoiignore` を使用します。

```
README.md
{{- if ne .chezmoi.hostname "work-laptop" }}
.work
{{- end }}
```

### `.chezmoiremove`

ターゲットディレクトリから削除するファイルのパターンを指定します。

## 外部ファイルの取り込み

### `.chezmoiexternal.toml`

外部ソースからファイルを取り込むには `.chezmoiexternal.toml` を使用します。

```toml
[".oh-my-zsh"]
    type = "archive"
    url = "https://github.com/ohmyzsh/ohmyzsh/archive/master.tar.gz"
    exact = true
    stripComponents = 1
    refreshPeriod = "168h"

[".vim/autoload/plug.vim"]
    type = "file"
    url = "https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim"
    refreshPeriod = "168h"

[".vim/pack/plugin"]
    type = "git-repo"
    url = "https://github.com/user/plugin.git"
    refreshPeriod = "168h"
```

外部ファイルを強制的に更新:

```
chezmoi apply --refresh-externals
chezmoi -R apply
```

## スクリプト

### スクリプトの種類

- `run_` - 毎回実行
- `run_onchange_` - 内容が変更された場合のみ実行
- `run_once_` - 一度だけ実行（内容のハッシュで管理）
- `run_before_` - ドットファイル更新前に実行
- `run_after_` - ドットファイル更新後に実行

### スクリプトの作成

スクリプトは手動で作成する必要があります。

```bash
chezmoi cd
cat > run_onchange_install-packages.sh << 'EOF'
#!/bin/sh
sudo apt install ripgrep
EOF
```

テンプレートとして作成する場合は `.tmpl` 拡張子を付けます。

```
run_onchange_install-packages.sh.tmpl
```

### スクリプトの状態をクリア

```bash
# run_onchange_ スクリプトの状態をクリア
chezmoi state delete-bucket --bucket=entryState

# run_once_ スクリプトの状態をクリア
chezmoi state delete-bucket --bucket=scriptState
```

## マシン間の差異管理

### 設定ファイルでの管理

`~/.config/chezmoi/chezmoi.toml` でマシン固有の変数を定義:

```toml
[data]
    email = "me@home.org"
```

テンプレートで使用:

```
[user]
    email = {{ .email | quote }}
```

### 異なるファイルの使用

完全に異なるファイルを使用する場合は `include` または `template` 関数を使用:

```
{{- if eq .chezmoi.os "darwin" -}}
{{-   include ".bashrc_darwin" -}}
{{- else if eq .chezmoi.os "linux" -}}
{{-   include ".bashrc_linux" -}}
{{- end -}}
```

## 自動コミット・プッシュ

設定ファイルで有効化:

```toml
[git]
    autoCommit = true
    autoPush = true
```

カスタムコミットメッセージ:

```toml
[git]
    autoCommit = true
    commitMessageTemplate = "{{ promptString \"Commit message\" }}"
```

## 新しいマシンでのセットアップ

ワンライナーでインストールと適用:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply $GITHUB_USERNAME
```

一時的な環境用（実行後に chezmoi を削除）:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --one-shot $GITHUB_USERNAME
```

## トラブルシューティング

- `chezmoi doctor` - 一般的な問題をチェック
- `chezmoi apply --dry-run --verbose` - 実際に適用せずに変更を確認
- `chezmoi ignored` - 無視されているファイルを表示

## ベストプラクティス

- スクリプトは冪等性を保つ（何度実行しても同じ結果になるようにする）
- 大きなファイルやアーカイブには external を使用しない（代わりに `run_onchange_` スクリプトを使用）
- プライベートデータは `chezmoi.toml` に保存し、パーミッションを 0600 に設定
- テンプレートのテストには `chezmoi execute-template` を使用
- git submodule を使用する場合は `external_` 属性を設定
