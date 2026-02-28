# Project Structure

## Directory Layout

```
.
├── .chezmoitemplates/            # Shared templates (can be included from other templates)
├── .kiro/                        # Kiro-related configurations
│   └── steering/                 # Guidelines for AI assistant
├── dot_config/                   # XDG Base Directory compliant configurations
│   └── chezmoi/                  # chezmoi configuration and examples
│       └── chezmoi.yaml          # Configuration file
├── dot_kiro/                     # Kiro CLI settings and steering rules
├── dot_vim/                      # Vim configurations
├── dot_*                         # Other dotfiles (zshrc, gitconfig, etc.)
├── private_dot_ssh/              # SSH keys and config (private attribute 0600)
├── private_*                     # Other private files
└── *.tmpl                        # Template files (processed by chezmoi)
```

### Platform-Specific Files

- Files use chezmoi conditional templates for OS-specific behavior
- Common pattern: `{{ if eq .chezmoi.os "darwin" }}` for macOS
- Hostname-specific configurations for different machines

## File Naming Patterns

### chezmoi Attributes

- `dot_`: Becomes `.filename` (hidden files)
- `private_`: Gets 0600 permissions (secure files)
- `executable_`: Gets execute permissions
- `.tmpl`: Template files processed by chezmoi

### Template Variables

- `.chezmoi.os`: Operating system (darwin/linux)
- `.chezmoi.hostname`: Machine hostname for machine-specific configuration
- `onepasswordRead`: Function to securely retrieve secrets
