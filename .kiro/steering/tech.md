# Technology Stack

## Core Technologies

- **chezmoi**: Dotfiles management tool with templating capabilities
- **1Password CLI**: Secure secret management

## AWS Resources

The AWS resources these dotfiles depend on are deliberately not version-controlled in this repository, which holds only files chezmoi deploys to `$HOME`. They live as CloudFormation stacks in account `070392599442`. Recover a template with `aws cloudformation get-template --stack-name <stack> --region <region> | cat`, and read `describe-stacks` for its parameters and outputs.

| Stack | Region | Purpose |
|---|---|---|
| `agentcore-websearch-caller` | us-east-1 | IAM user `agentcore-websearch` and its managed policy, granting only `bedrock-agentcore:InvokeGateway` on the one Web Search gateway. Its access key lives in 1Password (`AgentCore Web Search - AWS IAM`) and is rendered into `dot_aws/private_credentials.tmpl`; `dot_aws/private_config.tmpl` defines the matching profile. |

The AgentCore Web Search gateway itself is deployed from the CloudFormation template in [aws-samples/sample-agentcore-websearch-agent-skill](https://github.com/aws-samples/sample-agentcore-websearch-agent-skill), whose `GatewayUrl` output is exported as `AGENTCORE_GATEWAY_URL` in `dot_zshenv.tmpl`.

## Configuration Files Outside chezmoi

Do not manage `~/.claude/settings.json` or `~/.codex/config.toml` with chezmoi. A corporate management tool rewrites both in place, so ownership becomes a loop: an apply reverts the tool's edits, and the tool overwrites the rendered file on its next run.

Their history is kept instead by `dot_local/bin/executable_track-config-drift`, which commits the live content into a bare repository at `~/.local/share/config-drift.git` whose work tree is `$HOME`. `private_Library/LaunchAgents/local.track-config-drift.plist.tmpl` runs it at load and hourly, and logs failures to `/tmp/track-config-drift.log`.

- Track another file: add its `$HOME`-relative path to `FILES` in the script.
- Read the history: `git -C "$HOME" --git-dir="$HOME/.local/share/config-drift.git" --work-tree="$HOME" -P log --patch`. Every command needs `-C "$HOME"`, because git resolves a pathspec against the current directory rather than the work tree.
- Restoring an old revision restores content only. git records no mode beyond the execute bit, so `chmod 600 ~/.codex/config.toml` afterwards.

### Model Settings in `~/.claude/settings.json`

The `/model` list under Bedrock comes from `modelOverrides`, `enforceAvailableModels`, `model`, and `fallbackModel`. The ASBX toolbox wrapper writes those keys, along with `awsCredentialExport`, `env.AWS_REGION`, `includeCoAuthoredBy`, and `statusLine`, into `~/.claude/settings.json` when a session starts. It records each key it has already written in `~/.claude/.amzn/state/recommendation-snapshot.json` and never writes that key again, so a key removed after the fact stays removed and `/model` shows nothing.

Recover the list by deleting `recommendation-snapshot.json` and starting a session; the wrapper re-injects every key and rewrites the snapshot. `claude post-install` does not do this — it only sets up builder-mcp and the IDE integration.

### Files Owned by Their Tool

These are managed by chezmoi, but the tool is the source of truth for the content. Take the live file with `chezmoi add` instead of correcting the source, or `chezmoi apply` fights the tool on every run.

| Path | Tool | What it does |
|---|---|---|
| `.config/otty/config.toml` | Otty | Rewrites the whole file when settings change in the GUI, including which keys are commented out. |
| `.kiro/agents/*.json` | Kiro CLI | Reformats the JSON to its own style and injects the `creds-agent` MCP server into every agent. |

### `.aws/config` Has No Comments

The codex toolbox wrapper rewrites `~/.aws/config` through an INI parser: it drops every comment and appends `[profile codex-DO-NOT-DELETE]` after the existing profiles. `dot_aws/private_config.tmpl` therefore carries no comments and keeps that profile last, so the wrapper's rewrite produces no diff. Rationale that would otherwise be a comment there belongs in this file.

## Commit Message Standards

### Type Selection Rules

- `.kiro/` directory files: You MUST use `docs:` type
- `dot_*` or `private_dot_*` files: You MUST NOT use `docs:` type (use `feat:`, `fix:`, `refactor:`, or `chore:` based on intent)

## Editor Configuration

### Zed Settings Key Order

Keep keys in `dot_config/zed/private_settings.json` ordered to match Zed's bundled `default.json`. Insert new keys at their default position; do not append to the end. Apply the same order to nested keys.

Resolve the canonical order by listing the top-level keys of `default.json` for the installed version:

```bash
ver="$(zed --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')"
curl -fsSL "https://raw.githubusercontent.com/zed-industries/zed/v${ver}/assets/settings/default.json" \
  | grep -nE '^\s{2}"[a-z_]+"\s*:'
```

## Commands (Shared Agent Commands)

Commands are slash commands shared across agents. There are two types: custom commands authored in this repo, and external commands fetched from GitHub. Each agent references the shared `~/.agents/commands` directory through a single directory-level symlink.

### Agent Symlinks

```
dot_claude/symlink_commands.tmpl   # ~/.claude/commands  → ~/.agents/commands
dot_kiro/symlink_prompts.tmpl      # ~/.kiro/prompts     → ~/.agents/commands
dot_codex/symlink_prompts.tmpl     # ~/.codex/prompts    → ~/.agents/commands
```

Because each agent symlinks the whole directory, any `.md` file placed in `~/.agents/commands` is picked up by all agents automatically; no per-command symlink is needed.

### Custom Commands (authored in `dot_agents/commands/`)

Custom commands are real files committed under `dot_agents/commands/` and deployed to `~/.agents/commands/<name>.md`. They live as siblings of the external `commands/<source>/` subdirectories, so the call name has no namespace (e.g. `dot_agents/commands/outlook-todo.md` → `/outlook-todo`).

#### Adding a New Custom Command

1. Create `dot_agents/commands/<name>.md` with frontmatter:
   ```markdown
   ---
   description: One-line summary of what the command does.
   argument-hint: "<expected argument>"   # omit if the command takes no arguments
   ---
   ```
2. Write the command body as an instruction prompt. No symlink changes are needed; the existing directory symlinks expose it to all agents.

### External Commands (fetched via `.chezmoiexternal.yaml`)

External commands are managed via `dot_agents/.chezmoiexternal.yaml` and land in `commands/<source>/` subdirectories, giving them a namespaced call name (e.g. `/<source>:<command>`).

#### File Structure

```
dot_agents/.chezmoiexternal.yaml   # Downloads commands from GitHub repos
  → ~/.agents/commands/<source>/   # Downloaded command .md files
```

#### Adding a New Command Source

Add an entry to `dot_agents/.chezmoiexternal.yaml`:

```yaml
commands/<source-name>:
  type: archive
  url: https://github.com/<owner>/<repo>/archive/refs/heads/main.tar.gz
  stripComponents: 2
  include:
    - "*/commands/<file>.md"
  exact: true
  refreshPeriod: 168h
```

Use `include` to select specific files rather than downloading all commands from a repo.

## Rules (Shared Agent Instructions)

Rules are shared across multiple agents (Claude Code, Codex, Kiro CLI). There are two types: custom rules authored in this repo, and external rules fetched from GitHub.

### Custom Rules (authored in `.chezmoitemplates/`)

Custom rules are authored in `.chezmoitemplates/rules/` and distributed to each agent via chezmoi templates.

#### File Structure

```
.chezmoitemplates/rules/          # Rule source (single source of truth)
  common-standards.md
  chat-tone.md

dot_agents/rules/                  # For Claude Code / Kiro CLI (template reference)
  common-standards.md.tmpl         # → {{ template "rules/common-standards.md" . }}

dot_claude/rules/                  # For Claude Code (symlink to generated file)
  symlink_common-standards.md.tmpl # → {{ .chezmoi.homeDir }}/.agents/rules/common-standards.md

dot_codex/AGENTS.md.tmpl           # For Codex (inline template references)

dot_kiro/steering/                 # For Kiro CLI (symlink to generated file)
  symlink_common-standards.md.tmpl # → {{ .chezmoi.homeDir }}/.agents/rules/common-standards.md
```

#### Adding a New Custom Rule

1. Create the rule body in `.chezmoitemplates/rules/<name>.md`
2. Create `dot_agents/rules/<name>.md.tmpl` with frontmatter and template reference
3. Create `dot_claude/rules/symlink_<name>.md.tmpl` pointing to the generated file
4. Add `{{ template "rules/<name>.md" . }}` to `dot_codex/AGENTS.md.tmpl`
5. Create `dot_kiro/steering/symlink_<name>.md.tmpl` pointing to the generated file

### External Rules (fetched via `.chezmoiexternal.yaml`)

External rules are fetched from GitHub repos via `dot_agents/.chezmoiexternal.yaml` and placed directly into `~/.agents/rules/`. Each agent references the downloaded file.

#### File Structure

```
dot_agents/.chezmoiexternal.yaml   # Downloads rules from GitHub repos
  → ~/.agents/rules/<name>.md      # Downloaded rule file

dot_claude/rules/                  # For Claude Code (symlink to downloaded file)
  symlink_<name>.md.tmpl           # → {{ .chezmoi.homeDir }}/.agents/rules/<name>.md

dot_codex/AGENTS.md.tmpl           # For Codex (output cat to inline the file)
  {{ output "cat" (joinPath .chezmoi.homeDir ".agents/rules/<name>.md") }}

dot_kiro/steering/                 # For Kiro CLI (symlink to downloaded file)
  symlink_<name>.md.tmpl           # → {{ .chezmoi.homeDir }}/.agents/rules/<name>.md
```

#### Adding a New External Rule

1. Add a `type: file` entry to `dot_agents/.chezmoiexternal.yaml`:
   ```yaml
   rules/<name>.md:
     type: file
     url: https://raw.githubusercontent.com/<owner>/<repo>/main/<path-to-file>.md
     refreshPeriod: 168h
   ```
2. Create `dot_claude/rules/symlink_<name>.md.tmpl` pointing to the downloaded file
3. Add `{{ output "cat" (joinPath .chezmoi.homeDir ".agents/rules/<name>.md") }}` to `dot_codex/AGENTS.md.tmpl`
4. Create `dot_kiro/steering/symlink_<name>.md.tmpl` pointing to the downloaded file

## MCP Servers

When adding or removing a server in `dot_config/mcporter/private_mcporter.json.tmpl`, also update `dot_agents/skills/mcporter/SKILL.md.tmpl` (both the `description` frontmatter and the server list in the body).

## Skills (Shared Agent Skills)

Skills are shared across agents. There are two types: custom skills authored in this repo, and external skills installed from GitHub.

### Custom Skills (authored in `dot_agents/skills/`)

Custom skills live in `dot_agents/skills/<name>/SKILL.md` and deploy to `~/.agents/skills/<name>/`.

#### Adding a New Custom Skill

1. Create `dot_agents/skills/<name>/SKILL.md` with `name` and `description` frontmatter. The `description` is the only trigger mechanism, so state what the skill does and every context that should activate it.
2. Create `dot_kiro/skills/symlink_<name>.tmpl` pointing to `{{ .chezmoi.homeDir }}/.agents/skills/<name>`
3. Create `dot_claude/skills/symlink_<name>.tmpl` pointing to the same directory

Codex needs no wiring: it scans `$HOME/.agents/skills` natively and follows symlinks. Do not add custom skills to `dot_codex/AGENTS.md.tmpl`, which would load them on every turn and defeat progressive disclosure.

Prefer a skill over a rule when the content is reference material needed only for a specific task. Rules in `~/.agents/rules` are loaded on every turn; skills load only when their description matches.

### External Skills (installed via `run_install-skills.sh`)

External skills are installed via `run_install-skills.sh` using the `skills` CLI. The script runs on `chezmoi apply` and handles install, update, and post-install patching.

#### Adding a New External Skill

Add an `install_skills` call to `run_install-skills.sh`:

```bash
install_skills <github-owner/repo> <skill-name>
```

#### Post-Install Patching

If a skill needs modification (e.g., to support multiple agents), add a patch function after the install call:

```bash
install_skills <github-owner/repo> <skill-name>

patch_<skill_name>() {
  local file="$SKILLS_DIR/<skill-name>/SKILL.md"
  [ -f "$file" ] || return 0
  grep -q "PATCHED_MARKER" "$file" && return 0
  sed -i '' '...' "$file"
}
patch_<skill_name>
```

The pattern: install → check if already patched → apply sed. Patches are idempotent and re-applied on every `skills update`.
