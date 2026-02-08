# Technology Stack

## Core Technologies

- **chezmoi**: Dotfiles management tool with templating capabilities
- **1Password CLI**: Secure secret management

## Common Commands

### Daily Operations

```bash
# Add a new file to management
chezmoi add ~/.filename

# Edit a managed file
chezmoi edit ~/.filename

# Check what will be changed
chezmoi diff | cat

# Apply changes
chezmoi apply

# Dry run to preview changes
chezmoi apply --dry-run --verbose | cat

# Sync with remote repository
chezmoi update
```

### Development Workflow

```bash
# Edit template directly
chezmoi edit --apply ~/.zshrc

# Re-execute template after changes
chezmoi apply

# Check template syntax
chezmoi execute-template < template-file
```

## File Naming Conventions

- `dot_*`: Files that become `.filename` in home directory
- `private_*`: Files with restricted permissions (0600)
- `*.tmpl`: Template files processed by chezmoi
- `executable_*`: Files that should be executable

## Commit Message

- When you write a conventional commit message, You SHOULD use `docs:` as a type for files in `.kiro` directories.
- When you write a conventional commit message, You SHOULD NOT use `docs:` as a type for files in `dot_*` or `private_dot_*` directories.
