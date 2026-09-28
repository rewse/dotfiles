# Kiro CLI v3 移行の設計

## 目的

chezmoi が配布する Kiro CLI の設定を v3 エンジン専用に書き換える。v2 との互換は維持しない。移行後も、現在の default エージェントで許可しているコマンドとパス、enforce-uv と japanese-guard の hook、otty のタブバッジを v3 で同じように動かす。

参照資料は https://kiro.dev/docs/cli/v3/ 配下の migration-guide、permissions、hooks-migration、agent-config と、https://kiro.dev/docs/permissions 、https://kiro.dev/docs/hooks である。

## 前提と未確定事項

インストール済みの `kiro-cli 2.24.1` は `--help` に `--v3` を表示しないため、最初に v3 対応版へ更新する。ドキュメントは次の点で記述が食い違うので、書き換えの前に実機の v3 で確認し、結果に合わせて以降の作業を調整する。

1. `chat.agentEngine` に v3 を指定するときの値。設定リファレンスの表に載っていない。
2. CLI が `~/.kiro/hooks/*.json` を読むかどうか。また `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PostToolUse`、`Stop` が CLI で発火するかどうか。共通の hooks ページは `SessionStart` を IDE 専用と書いている。
3. hook の stdin JSON の形。確認するのは `tool_input.command`、`assistant_response`、`session_id` のフィールド名、シェルツールの名前、`Stop` hook の再入を示すフラグの有無、`KIRO_SESSION_ID` 環境変数の有無である。
4. 確認プロンプトで「常に許可」を選んだときに、Kiro が `~/.kiro/settings/permissions.yaml` に書き込むかどうか。
5. shell の glob パターン `cat` が引数付きの `cat foo` に一致するかどうか。一致しなければ `cat` と `cat *` の2件が必要になる。

## 変更内容

### 権限: `dot_kiro/settings/private_permissions.yaml.tmpl`（新規）

`~/.kiro/settings/permissions.yaml` をユーザースコープの権限定義として生成する。全エージェントに適用される。

- `toolsSettings.execute_bash.allowedCommands` の正規表現を `capability: shell` の `match` に glob で移す。`X( .*)?` は `X` と `X *` に分ける（確認事項5で1件で足りると分かれば `X*` 系に寄せる）。`(a|b|c)` の選択肢は1件ずつに展開する。`.+` と `.*` は `*` にする。`journalctl( .*)? --no-pager( .*)?` のように途中に固定語を含むものは `journalctl* --no-pager*` とする。
- `fs_read.allowedPaths` を `capability: fs_read`、`fs_write.allowedPaths` を `capability: fs_write` の `allow` に移す。対象は `./**`、`~/Desktop/**`、`~/Downloads/**`、`/tmp/**` である。
- 現行の `allowedTools` は `@builtin/write` を含むので書き込みを全面的に許可しているが、移行後は上記4パスに限る。ユーザースコープは Builder 系エージェントにも効くため、全面許可を広げない。
- `@builtin/web_fetch`、`@builtin/web_search`、`@builtin/subagent`、`@builtin/delegate` は `web_fetch`、`web_search`、`subagent` の `allow` に移す。`@builtin/read`、`@builtin/glob`、`@builtin/grep` は `fs_read` の許可パスで扱う。`@builtin/knowledge` は対応する capability を確認して移す。
- hostname `7cf34ded5d65` のときだけ `capability: mcp` で `builder-mcp` のツールを許可する。
- `autoAllowReadonly` は廃止されたので移さない。読み取り専用の git コマンドとシステム情報コマンドは Kiro の既定で許可される。

確認事項4で Kiro がこのファイルに書き込むと分かった場合は、テンプレートをやめて `~/.config/otty/config.toml` と同じ扱いにする。実機のファイルを正とし、変更は `chezmoi add` で取り込む。テンプレート条件（hostname、homeDir）が必要な部分は、その時点で扱いを決める。

### エージェント: `dot_kiro/agents/default.json.tmpl`

- `toolsSettings`、`allowedTools`、`hooks`、`useLegacyMcpJson` を削除する。
- `includeMcpJson: true` を追加する。
- `name`、`description`、`prompt`、`mcpServers`、`tools`、`toolAliases`、`resources` は残す。形式は JSON のままにする。

### hooks: `dot_kiro/hooks/*.json.tmpl`（新規）

エージェントに埋め込んでいた hooks を、v3 の単独ファイル形式（`"version": "v1"`）に移す。

- `agent-guards.json.tmpl`: 全 OS 向け。`PreToolUse`（matcher はシェルツール名）で `~/.agents/hooks/enforce-uv.sh` を、`Stop` で `~/.agents/hooks/japanese-guard-kiro.py` を実行する。
- `otty-state.json.tmpl`: darwin 向け。`SessionStart` と `Stop` で `otty-state.sh idle` を、`UserPromptSubmit`、`PreToolUse`、`PostToolUse` で `otty-state.sh processing` を実行する。
- `Stop` 内の順序は japanese-guard が先、otty-state が後とする。現行と同じである。
- `.chezmoiignore` は Linux で `.kiro/hooks` 全体を除外しているので、除外対象を `.kiro/hooks/otty-state.sh` と `.kiro/hooks/otty-state.json` に絞る。

確認事項2で CLI がグローバルの hook ファイルを読まない場合、または必要なトリガーが CLI で発火しない場合は、その hook だけエージェント埋め込みの `hooks` に戻す。

### hook スクリプト

- `dot_agents/hooks/executable_enforce-uv.sh`: v3 の `PreToolUse` 入力でコマンド文字列の位置が `.tool_input.command` と違う場合は、そのフィールドも読む。Claude Code と Codex からの入力は引き続き扱う。exit 2 によるブロックは v3 でも有効である。
- `dot_agents/hooks/executable_japanese-guard-kiro.py`: `session_id` と `assistant_response` のフィールド名を v3 に合わせる。v3 が再入フラグを渡す場合は、marker ファイルをやめてそのフラグで判定する。docstring もそれに合わせて直す。
- `dot_kiro/hooks/executable_otty-state.sh`: `KIRO_SESSION_ID` が v3 で渡されない場合は、stdin の `session_id` からキャッシュキーを作る。

### CLI 設定: `dot_kiro/settings/private_cli.json.tmpl`

- 確認事項1の値で `chat.agentEngine` を追加する。これで `kiro-cli chat` が v3 で起動するので、zsh のエイリアス（`k`、`ka`、`kr`、`kar`）は変えない。
- v3 で意味がなくなったキーを `kiro-cli settings list` と設定リファレンスで確かめて削除する。候補は `chat.enableCheckpoint`（v3 では IDE 専用）である。

### ドキュメント

- `AGENTS.md` の Managed files 節に、`permissions.yaml` の管理方法と、Kiro の hooks をエージェントではなく `dot_kiro/hooks/*.json.tmpl` に置くことを追記する。
- `README.md` の `dot_kiro/` の説明を、権限と hooks のファイル構成に合わせて更新する。

### 変更しないもの

skills と steering の symlink（`dotfiles-internal` 側を含む）、`~/.kiro/settings/mcp.json`、`dot_zshrc.tmpl` と `dot_zprofile.tmpl` の Kiro ブロック、`dot_kiro/argv.json` は変更しない。

## 手作業で行う一回限りの作業

- v3 のセッションは v2 と互換がないので、切り替え前に `cp -r ~/.kiro/sessions ~/.kiro/sessions-v2-backup` で退避する。
- Linux ホストの OS が AL2 でないことと、v3 対応版の `kiro-cli` が入っていることを確認する。v3 は AL2 に対応していない。

## 検証

- `kiro-cli diagnostic` が hook スキーマと `permissions.yaml` のエラーを報告しないこと
- `chezmoi diff` の差分が上記の変更だけであること
- v3 のセッションで次を確認すること
  - `rg`、`git -P diff`、`jq` が確認なしで実行される
  - 許可リストにないコマンドは確認を求められる
  - `pip install foo` が enforce-uv にブロックされる
  - 英語で回答させると japanese-guard が一度だけ書き直しを求める
  - macOS で otty のタブバッジが実行中と完了に切り替わる
  - 業務用 Mac で `builder-mcp` の `ReadInternalWebsites` が確認なしで使える
- `tests/` に `japanese-guard-kiro.py` のテストを追加し、確認事項3で得た v3 の `Stop` 入力で、英語の回答をブロックすることと、再入時に通すことを検証すること

## 対象外

default エージェントの Markdown 形式への変換、steering の inclusion front matter の導入、ワークスペーススコープの権限設定、v2 セッションの移行は行わない。
