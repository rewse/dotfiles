# outlook-todo スラッシュコマンド 設計

## 目的

TickTick の Quick Add（ワンライナー）文法で書いた1行から、Microsoft To-Do（Outlook ToDo）のタスクを作成するスラッシュコマンドを追加する。TickTick の記法に慣れた操作感のまま、Outlook 側へタスクを登録できるようにする。

## 配布構成

コマンド本体は単一ソースとして `dot_agents/commands/outlook-todo.md` に置く（chezmoi 管理の実ファイル）。`chezmoi apply` で `~/.agents/commands/outlook-todo.md` に展開される。

外部コマンドは `commands/<source>/` のサブディレクトリに `exact: true` で展開されるが、本ファイルはその兄弟として直下に置くため干渉しない。サブディレクトリに入れないので、呼び出しは namespace なしの `/outlook-todo` になる。

各エージェントへの配布:

- Claude Code: 既存の `dot_claude/symlink_commands.tmpl`（`~/.claude/commands` → `~/.agents/commands`）経由で参照される。追加作業なし。
- Kiro CLI: 既存の `dot_kiro/symlink_commands.tmpl` 経由で参照される。追加作業なし。
- Codex: Codex はカスタムプロンプトを `~/.codex/prompts/` から読むため、新規に `dot_codex/symlink_prompts.tmpl`（→ `~/.agents/commands`）を追加する。

## コマンド形式

既存コマンドに倣い、frontmatter 付き Markdown とする。

- `description`: コマンドの一行説明
- `argument-hint`: `"<task in TickTick quick-add syntax>"`
- 本文: パースルールと作成手順を記述した指示書（方針 A）。エージェント（LLM）自身が `$ARGUMENTS` を解釈し、mcporter で `aws-outlook-mcp.todo_tasks` を呼ぶ。

## TickTick Quick Add 文法のパース仕様

入力例: `Review Q3 report ^Work #finance !high tomorrow 5pm @gowri`

| 記号 | TickTick の意味 | Microsoft To-Do への変換 |
|------|----------------|--------------------------|
| `^list` | リスト指定 | `todo_lists` で名前一致を探し `listId` を解決。無ければ既定リスト（Tasks）へ入れて警告 |
| `!priority` | 優先度 | `importance` にマップ（後述） |
| 日付・時刻 | 期日・リマインダー | 自然言語を ISO に解釈し `dueDateTime` へ。時刻ありなら `reminderDateTime` も同値・`isReminderOn=true` |
| `#tag` | タグ | To-Do に相当機能がないため `body`（説明）へ追記 |
| `@user` | 担当者割当 | 個人リストは割当不可のため `body` へ追記 |
| 残りのテキスト | タスク名 | 記号トークンを除去した本文を `title` に |

### 優先度マッピング

| TickTick | Microsoft To-Do `importance` |
|----------|------------------------------|
| `!high` | `high` |
| `!medium` | `normal` |
| `!low` | `low` |
| `!none` / 指定なし | `normal` |

### 日付・時刻の扱い

- 自然言語（`tomorrow 5pm`、`明日17時`、`*2026-06-20` など）を ISO 形式に解釈する。
- 時刻はローカルタイムゾーンとして解釈し、ISO 文字列にオフセット（JST なら `+09:00`）を必ず付与する。オフセットが無いとサーバーは UTC とみなし時刻がずれる。
- 時刻を含む場合: `reminderDateTime` をオフセット付きの ISO 値で設定し `isReminderOn=true`。`dueDateTime` も同値で設定するが、To-Do は `dueDateTime` の日付部分のみ保持し時刻成分は捨てる仕様のため、時刻は `reminderDateTime` 側で表現される。TickTick が時刻指定でリマインダーを付ける挙動に合わせる。
- 日付のみの場合: 全日扱いとしリマインダーは設定しない（mcporter スキルの方針に合わせ、不要なリマインダーを避ける）。

### タイトルの言語

mcporter スキルの方針に従い、タイトルは英語・命令形に整える（例: "Review Q3 report"）。日本語入力でも英語命令形へ変換する。

## 作成フロー（解析して即作成）

1. `$ARGUMENTS` を上記仕様でパースする。
2. `^list` があれば `mcporter call aws-outlook-mcp.todo_lists operation=list` で `listId` を解決する。一致が無ければ既定のタスクリスト（Tasks）へ入れ、その旨を警告する。
3. `mcporter call aws-outlook-mcp.todo_tasks operation=create listId=... title=... body=... importance=... dueDateTime=... reminderDateTime=... isReminderOn=...` を実行する。
4. 作成結果（タイトル / リスト / 期日 / 優先度、`body` に退避した tag・user）を1行で報告する。

## エラー処理

- mcporter または `aws-outlook-mcp` が利用不可の場合: その旨を報告し、実行を中止する。
- `^list` が解決できない場合: 既定リストへ入れて警告する（中止しない）。
- 日付の解釈が曖昧な場合: 最も近い有効な日時として解釈する（TickTick の挙動に合わせる）。

## 対象外（YAGNI）

- タスクの更新・完了・削除（作成のみに絞る）。
- チェックリスト（サブタスク）の作成。
- 繰り返しタスク（TickTick の `repeat` 文法）の変換。
