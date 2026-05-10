# Dotfiles

Personal dotfiles management system using chezmoi. Centrally manage shell configurations, editor settings, Git configurations, and more across multiple machines (macOS and Linux).

## Features

- **Cross-platform support**: Compatible with both macOS and Linux
- **Template-based**: Manage machine-specific configurations with conditional branching
- **Secure secrets management**: Safely manage API keys and credentials through 1Password integration

## Setup

### Installation on a New Machine

#### macOS (Homebrew)

```bash
# Install chezmoi
brew install chezmoi

# Initialize and apply dotfiles
chezmoi init --apply <your-github-username>
```

#### macOS (without Homebrew) or Linux

```bash
# Install chezmoi and initialize/apply dotfiles
sh -c "$(curl -fsLS get.chezmoi.io)" -- init --apply <your-github-username>
```

Or, install chezmoi only:

```bash
sh -c "$(curl -fsLS get.chezmoi.io)"
```

Install to a specific directory (e.g., `/usr/local/bin`):

```bash
sh -c "$(curl -fsLS get.chezmoi.io)" -- -b /usr/local/bin
```

### If You Already Have chezmoi

```bash
chezmoi init <your-github-username>
chezmoi apply
```

## Usage

### Daily Operations

```bash
# Add a file
chezmoi add ~/.zshrc

# Edit a file
chezmoi edit ~/.zshrc

# Check changes
chezmoi diff | cat

# Apply changes
chezmoi apply

# Dry run
chezmoi apply --dry-run --verbose | cat
```

### Sync with Remote

```bash
# Fetch and apply latest changes
chezmoi update
```

## Structure

### Directory Structure

```
.
├── .chezmoitemplates/            # Shared templates (can be included from other templates)
│   └── rules/                    # Shared AI agent rule templates
├── dot_agents/                   # Shared AI agent configurations (rules, skills)
│   ├── .chezmoiexternal.yaml     # External commands and skill sources not compatible with npx skills
│   └── skills/                   # Custom skills for AI agents
├── dot_claude/                   # Claude Code settings and configurations
├── dot_codex/                    # Codex agent settings and configurations
├── dot_config/                   # XDG Base Directory compliant configurations
├── dot_kiro/                     # Kiro CLI settings and configurations
├── dot_vim/                      # Vim configurations
├── dot_*                         # Other dotfiles (zshrc, gitconfig, etc.)
├── private_*                     # Other private files
├── run_install-skills.sh         # Script to install AI agent skills globally
└── *.tmpl                        # Template files (processed by chezmoi)
```

## Requirements

- [chezmoi](https://www.chezmoi.io/)
- [1Password CLI](https://developer.1password.com/docs/cli/) (for secrets management)
