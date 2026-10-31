# agent-desktop 導入 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Mac に `agent-desktop` を npm で入れ、バイナリに埋め込まれたスキルを `~/.agents/skills/agent-desktop/SKILL.md` に書き出して Claude Code、Codex、Kiro から使えるようにする。

**Architecture:** 本体は ansible-playbooks の darwin ロールの `darwin_npm_packages` に足し、既存の `npm.yml` がインストールと更新を担う。スキルは chezmoi の `run_install-skills.sh` が apply のたびに `agent-desktop skills get desktop` の `data.content` を書き出し、Claude Code と Kiro へは symlink テンプレートで配る。

**Tech Stack:** Ansible、npm、chezmoi、bash、jq

**Spec:** `docs/superpowers/specs/2026-10-31-agent-desktop-design.md`（chezmoi リポジトリ）

## Global Constraints

- 対象は Mac のみ。Ubuntu のロールには何も足さない
- スキルは `npx skills add` で入れない
- 書き出すのは `desktop` の本体ガイドだけ。`--full`、`platform`、reference は書き出さない
- Kiro の `private_permissions.yaml.tmpl` に `agent-desktop *` を足さない。Claude Code と Codex の権限設定も変えない
- アクセシビリティ権限は ansible で自動化せず、利用者が `agent-desktop permissions --guide` で手で付ける
- 各リポジトリで作業前に `git pull` し、コミット前に `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files` を通す（新規ファイルは先に stage する）
- push は利用者の確認を取ってから行う

## Review Focus

- `agent-desktop skills get desktop` が失敗する、または `data.content` が空や null のとき、既存の SKILL.md を残したまま `record_failure` する（Task 2 Step 4 で確かめる）
- `agent-desktop` がない状態で apply したとき、ほかのスキルの更新は続き、スクリプトは最後に失敗数を報告して終わる（Task 2 Step 4 で確かめる）
- 書き出した SKILL.md の先頭に `name: agent-desktop` を含む frontmatter がある。なければスキルとして認識されない（Task 2 Step 1 で確かめ、なければ書き出し時に補う）
- 2回目の `ansible-playbook --tags darwin_npm` が `changed=0` になる（Task 1 Step 4 で確かめる）
- Claude Code と Kiro の symlink が `~/.agents/skills/agent-desktop` を指していて、リンク切れになっていない（Task 2 Step 5 で確かめる）

---

### Task 1: ansible-playbooks で agent-desktop を入れる

**Files:**
- Modify: `~/git/ansible-playbooks/roles/darwin/vars/main.yml`（`darwin_npm_packages`）

**Interfaces:**
- Produces: PATH 上の `agent-desktop` コマンド（`/opt/homebrew/bin/agent-desktop`、パッケージは `/opt/homebrew/lib/node_modules/agent-desktop`）

- [ ] **Step 1: `git pull` して main にいることを確かめる**

Run: `git -C ~/git/ansible-playbooks pull && git -C ~/git/ansible-playbooks -P status -sb | head -1`
Expected: `## main...origin/main`

- [ ] **Step 2: `darwin_npm_packages` の先頭に `agent-desktop` を足す**

アルファベット順なので `ctx7` の前に置く。npm が vendor の案内するインストール方法なので、方法についてのコメントは要らない。

- [ ] **Step 3: check mode で差分を確かめる**

Run: `cd ~/git/ansible-playbooks && ansible-playbook darwin-business.yml --tags darwin_npm --check`
Expected: 終了コード 0、`npm | Install global packages` の `agent-desktop` が changed

- [ ] **Step 4: 適用し、2回目が changed=0 になることを確かめる**

Run: `ansible-playbook darwin-business.yml --tags darwin_npm` を2回
Expected: 1回目は終了コード 0、2回目は PLAY RECAP が `changed=0`。続けて `agent-desktop version` がバージョンを表示する

- [ ] **Step 5: lint とテストを通す**

Run: `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files --show-diff-on-failure && uv run --with pytest --with ansible-core pytest tests`
Expected: どちらも成功

- [ ] **Step 6: コミットする**

```bash
git add roles/darwin/vars/main.yml
git commit -m "feat(darwin): install agent-desktop for desktop computer use"
```

- [ ] **Step 7: 利用者にアクセシビリティ権限の付与を頼む**

`! agent-desktop permissions --guide` を実行してもらい、ターミナルアプリに権限を付けてもらう。付与後に `agent-desktop status` で permissions が granted になっていることを確かめる。

### Task 2: chezmoi でスキルを書き出して配る

**Files:**
- Modify: `~/git/chezmoi/run_install-skills.sh`（OfficeCLI ブロックの直前に agent-desktop ブロックを置く）
- Create: `~/git/chezmoi/dot_claude/skills/symlink_agent-desktop.tmpl`
- Create: `~/git/chezmoi/private_dot_kiro/skills/symlink_agent-desktop.tmpl`

**Interfaces:**
- Consumes: Task 1 の `agent-desktop` コマンド
- Produces: `~/.agents/skills/agent-desktop/SKILL.md`、`~/.claude/skills/agent-desktop` と `~/.kiro/skills/agent-desktop`（どちらも `~/.agents/skills/agent-desktop` への symlink）

- [ ] **Step 1: 実際の出力の形を確かめる**

Run: `agent-desktop skills get desktop | jq -r '.data.content' | head -5`
Expected: 1行目が `---`、続いて `name: agent-desktop`。違う形（パスが別、frontmatter がない）なら、Step 3 の jq 式を合わせ、frontmatter がなければ upstream の `skills/agent-desktop/SKILL.md` の `name` と `description` を前に足す処理を加える

- [ ] **Step 2: `git pull` する**

Run: `git -C ~/git/chezmoi pull`
Expected: 成功

- [ ] **Step 3: `run_install-skills.sh` に agent-desktop ブロックを足す**

コメントでは、スキルがバイナリに埋め込まれていることと、apply のたびに書き出すとインストール済みバージョンと揃うことを述べる。一時ファイルを経由するので、失敗しても既存の SKILL.md は壊れない。

```bash
if command -v agent-desktop >/dev/null 2>&1; then
  agent_desktop_skill="$(mktemp /tmp/agent-desktop-skill.XXXXXX)"
  if agent-desktop skills get desktop < /dev/null |
    jq -er '.data.content | select(type == "string" and length > 0)' > "$agent_desktop_skill"; then
    chmod 0644 "$agent_desktop_skill" &&
      mkdir -p "$SKILLS_DIR/agent-desktop" &&
      command mv "$agent_desktop_skill" "$SKILLS_DIR/agent-desktop/SKILL.md" ||
      record_failure "write agent-desktop skill"
  else
    record_failure "update agent-desktop skill"
  fi
  command rm -f "$agent_desktop_skill"
else
  record_failure "find agent-desktop"
fi
```

`mktemp` の一時ファイルは mode 0600 なので、置き換える前に 0644 にする。

- [ ] **Step 4: 失敗時の振る舞いを確かめる**

ブロックだけを抜き出した一時スクリプトを `mktemp -d /tmp/agent-desktop-test.XXXXXX` の中に作り、`SKILLS_DIR` をその中に向け、`record_failure` を echo に差し替えて次の3つを実行する。

- `agent-desktop` を `{"ok":false}` を返す偽物に差し替えると `Failed to update agent-desktop skill` が出て、あらかじめ置いた SKILL.md が変わらない
- PATH から `agent-desktop` を外すと `Failed to find agent-desktop` が出る
- 本物の `agent-desktop` では SKILL.md ができ、mode が 0644 になる

- [ ] **Step 5: symlink テンプレートを足して apply する**

2つのテンプレートの中身は `{{ .chezmoi.homeDir }}/.agents/skills/agent-desktop` の1行だけにする（`symlink_officecli.tmpl` と同じ形）。

Run: `chezmoi apply && readlink ~/.claude/skills/agent-desktop ~/.kiro/skills/agent-desktop && head -3 ~/.claude/skills/agent-desktop/SKILL.md`
Expected: apply の終了コード 0、2つの readlink が `~/.agents/skills/agent-desktop` を指し、SKILL.md の frontmatter が見える

- [ ] **Step 6: lint とテストを通す**

Run: `cd ~/git/chezmoi && git add run_install-skills.sh dot_claude/skills/symlink_agent-desktop.tmpl private_dot_kiro/skills/symlink_agent-desktop.tmpl && uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files && uv run python -m unittest discover -s tests`
Expected: shellcheck を含めてすべて成功

- [ ] **Step 7: コミットする**

```bash
git add run_install-skills.sh dot_claude/skills/symlink_agent-desktop.tmpl private_dot_kiro/skills/symlink_agent-desktop.tmpl
git commit -m "feat(skills): write the agent-desktop skill from its binary"
```

- [ ] **Step 8: 新しい Claude Code セッションで動作を確かめる**

`agent-desktop` スキルが一覧に出て、`agent-desktop snapshot --app Finder -i --compact` が ref 付きの JSON を返すことを確かめる。
