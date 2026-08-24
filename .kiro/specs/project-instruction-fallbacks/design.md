# プロジェクト指示ファイルのフォールバック設計

## 目的

プロジェクトルートに各エージェントのネイティブ指示がない場合、ほかのエージェント向け指示をプロジェクト指示として読む。ユーザールートの設定は chezmoi で共通化済みのため、このルールの対象外とする。

## 配置

互換ルールの本文を `.chezmoitemplates/rules/project-instruction-fallbacks.md` に置く。`dot_agents/rules/project-instruction-fallbacks.md.tmpl` が本文を `~/.agents/rules/` へ展開し、Claude Code と Kiro は既存ルールと同じ方式のシンボリックリンクで参照する。Codex の `AGENTS.md.tmpl` は公開ルールを glob するため、新しい本文を自動で取り込む。

## フォールバック規則

| エージェント | ネイティブ指示 | ネイティブ不在時に読む指示 |
|---|---|---|
| Claude Code | プロジェクトルートの `CLAUDE.md` | プロジェクトルートの `AGENTS.md` と `.kiro/steering/` 配下の指示 |
| Codex | プロジェクトルートの `AGENTS.md` | プロジェクトルートの `CLAUDE.md` と `.kiro/steering/` 配下の指示 |
| Kiro | プロジェクトルートの `AGENTS.md` と `.kiro/steering/` 配下の指示 | プロジェクトルートの `CLAUDE.md` |

ネイティブ指示が存在する場合、代替指示は読まない。ネイティブ指示が存在せず、代替指示が複数存在する場合はすべて読む。存在しない代替指示は無視する。

Kiro は `AGENTS.md` と `.kiro/steering/` 配下の指示をネイティブとして扱う。片方でも存在すれば、存在するネイティブ指示をすべて読み、`CLAUDE.md` は読まない。どちらも存在しない場合だけ `CLAUDE.md` を読む。

`.kiro/steering/` を代替として読む場合は、配下の指示ファイルをすべてプロジェクト指示として扱う。この規則はプロジェクトルートだけに適用し、ユーザールートの `~/.codex`、`~/.claude`、`~/.kiro` には適用しない。

## 変更対象

- Create: `.chezmoitemplates/rules/project-instruction-fallbacks.md`
- Create: `dot_agents/rules/project-instruction-fallbacks.md.tmpl`
- Create: `dot_claude/rules/symlink_project-instruction-fallbacks.md.tmpl`
- Create: `dot_kiro/steering/symlink_project-instruction-fallbacks.md.tmpl`

既存の共通規約、`dot_codex/AGENTS.md.tmpl`、既存シンボリックリンクは変更しない。

## エラー処理

ネイティブ指示も代替指示も存在しない場合は何も追加で読まず、通常どおり処理を続ける。代替指示を読めない場合は、推測で内容を補わず読み取り失敗を報告する。

## 検証

- Codex 用 `AGENTS.md` の生成結果に互換ルールが含まれることを確認する。
- `~/.agents/rules/` 用テンプレートが互換ルール本文を展開することを確認する。
- Claude Code と Kiro のシンボリックリンクが `~/.agents/rules/project-instruction-fallbacks.md` を指すことを確認する。
- Kiro のネイティブ指示に `AGENTS.md` と `.kiro/steering/` の両方が含まれ、どちらかが存在する場合は `CLAUDE.md` を読まないことを確認する。
- 互換ルールにプロジェクトルート限定、ネイティブ優先、複数代替の全読み込みが明記されていることを確認する。
