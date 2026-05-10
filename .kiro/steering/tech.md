# Technology Stack

## Core Technologies

- **chezmoi**: Dotfiles management tool with templating capabilities
- **1Password CLI**: Secure secret management

## Commit Message Standards

### Type Selection Rules

- `.kiro/` directory files: You MUST use `docs:` type
- `dot_*` or `private_dot_*` files: You MUST NOT use `docs:` type (use `feat:`, `fix:`, `refactor:`, or `chore:` based on intent)

## Commands (Shared Agent Commands)

Commands are slash commands shared across agents. External commands are managed via `dot_agents/.chezmoiexternal.yaml` and symlinked into each agent's directory.

### File Structure

```
dot_agents/.chezmoiexternal.yaml   # Downloads commands from GitHub repos
  → ~/.agents/commands/<source>/   # Downloaded command .md files

dot_claude/symlink_commands.tmpl   # → ~/.agents/commands
dot_kiro/symlink_commands.tmpl     # → ~/.agents/commands
```

### Adding a New Command Source

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
  cmux-subagent.md

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

## Skills (Shared Agent Skills)

External skills are installed via `run_install-skills.sh` using the `skills` CLI. The script runs on `chezmoi apply` and handles install, update, and post-install patching.

### Adding a New Skill

Add an `install_skills` call to `run_install-skills.sh`:

```bash
install_skills <github-owner/repo> <skill-name>
```

### Post-Install Patching

If a skill needs modification (e.g., to support multiple agents), add a patch function after the install call:

```bash
install_skills hummer98/using-cmux using-cmux

patch_using_cmux() {
  local file="$SKILLS_DIR/using-cmux/SKILL.md"
  [ -f "$file" ] || return 0
  grep -q "PATCHED_MARKER" "$file" && return 0
  sed -i '' '...' "$file"
}
patch_using_cmux
```

The pattern: install → check if already patched → apply sed. Patches are idempotent and re-applied on every `skills update`.
