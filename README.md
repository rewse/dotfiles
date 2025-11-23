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
├── .kiro/                        # Kiro-related configurations
│   └── steering/                 # Guidelines for AI assistant
├── dot_config/                   # XDG Base Directory compliant configurations
│   └── chezmoi/                  # chezmoi configuration and examples
│       └── chezmoi.toml.example  # Example configuration file
├── dot_kiro/                     # Kiro CLI settings and steering rules
├── dot_vim/                      # Vim configurations
├── dot_*                         # Other dotfiles (zshrc, gitconfig, etc.)
├── private_dot_ssh/              # SSH keys and config (private attribute 0600)
├── private_*                     # Other private files
└── *.tmpl                        # Template files (processed by chezmoi)
```

### Template Variables

Configure in `$HOME/.config/chezmoi/chezmoi.toml`:

```toml
[data]
    email = "email@example.com"
```

## Requirements

- [chezmoi](https://www.chezmoi.io/)
- [1Password CLI](https://developer.1password.com/docs/cli/) (for secrets management)
