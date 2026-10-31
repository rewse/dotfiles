# agent-desktop の導入

## 目的

Bedrock 経由の Claude Code では組み込みの Computer Use が使えない。代わりに vercel-labs/agent-desktop を入れ、エージェントが macOS のデスクトップアプリをアクセシビリティツリー経由で操作できるようにする。

## ゴールと非ゴール

- ゴール: Mac に `agent-desktop` が入り、Claude Code、Codex、Kiro から `agent-desktop` スキルが見える
- ゴール: スキル本文が、最後に `chezmoi apply` した時点のバイナリのバージョンと一致する。Mac の ansible は `chezmoi apply` を実行しないため、npm で更新された後は次の apply まで古い本文のままでよい
- 非ゴール: Ubuntu への導入（GUI のないサーバーのため）
- 非ゴール: macOS のアクセシビリティ権限の自動付与（GUI で一度だけ手で付ける）
- アンチゴール: スキルを `npx skills add` で入れること（バイナリとずれる）

## 方式

検討した案は次の3つで、A を選んだ。

| 案 | 内容 | トレードオフ |
|---|---|---|
| A（採用） | `run_install-skills.sh` に officecli と同じ形のブロックを足し、`agent-desktop skills get desktop` の出力を書き出す | 既存の前例どおり。失敗は `record_failure` に記録されて他のスキル更新を止めない。ansible より先に apply するとその回は失敗として数えられる |
| B | chezmoi テンプレートの `output` で SKILL.md を管理ファイルにする | `chezmoi diff` で見える。バイナリがないとテンプレートの段階で apply 全体が止まる |
| C | ansible の npm タスクの後に書き出しタスクを足す | 順序の問題がない。スキル管理が chezmoi と ansible に割れる |

## 決めたこと

- ansible-playbooks: `roles/darwin/vars/main.yml` の `darwin_npm_packages` に `agent-desktop` を加える。インストールと更新は既存の `npm.yml`（cooldown 付き）に任せる
- chezmoi: `run_install-skills.sh` の OfficeCLI ブロックの近くに agent-desktop のブロックを置く。`command -v agent-desktop` があれば `agent-desktop skills get desktop | jq -r '.data.content'` を `~/.agents/skills/agent-desktop/SKILL.md` に書き出し、なければ `record_failure` する。apply のたびに書き直す
- chezmoi: `dot_claude/skills/symlink_agent-desktop.tmpl` と `private_dot_kiro/skills/symlink_agent-desktop.tmpl` を officecli と同じ形で足す。Codex は `~/.agents/skills` を直接読む
- 書き出すのは本体ガイド（`desktop`）だけ。macOS 固有の内容と reference は、SKILL.md の案内に従ってその場で `skills get platform` と `skills get desktop <reference>` から読む
- 権限: Kiro の `private_permissions.yaml.tmpl` に `agent-desktop *` の自動許可は足さない（デスクトップ全体を操作できるため、操作のたびに承認を求める）。Claude Code と Codex の権限設定は変えない

## 実装者の判断（自分の判断として記載）

- コマンドが失敗したり `data.content` が空だったりしたときに既存の SKILL.md を壊さないよう、一時ファイルに書いてから中身を確かめて置き換える
- `agent-desktop permissions --guide` でアクセシビリティ権限を付ける手順は、ansible のタスクにせず手作業とする
- Ubuntu では `agent-desktop` がないので、ブロックは失敗として数えられ、symlink はリンク切れになる。OfficeCLI のブロックと symlink も同じ振る舞いなので、それに合わせる
- `.data.content` という JSON のパスと、出力に SKILL.md の frontmatter が含まれるかどうかは、バイナリを入れてから確かめる。frontmatter がなければ書き出すときに補う
