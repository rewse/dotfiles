# Project Structure

## Directory Layout

```
.
├── README.md                           # Project documentation and setup instructions
├── LICENSE                             # Project license file
├── .gitignore                          # Git ignore patterns
├── .chezmoiignore                      # Files to ignore during chezmoi operations
├── .chezmoitemplates/                  # Shared templates
├── dot_zshrc.tmpl                      # Zsh shell configuration with OS-specific logic
├── dot_gitconfig.tmpl                  # Git configuration with templating
├── dot_vimrc.tmpl                      # Vim editor configuration
├── dot_npmrc                           # NPM configuration
├── private_dot_ssh/                    # SSH keys and configuration (0600 permissions)
├── private_Library/                    # macOS-specific application support files
├── dot_config/                         # XDG Base Directory compliant configurations
└── dot_kiro/                           # Kiro CLI and AI assistant configuration

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
