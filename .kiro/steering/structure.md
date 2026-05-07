# Project Structure

## Directory Layout

```
.
├── .chezmoitemplates/            # Shared templates (can be included from other templates)
│   └── rules/                    # Shared AI agent rule templates
├── dot_agents/                   # Shared AI agent configurations (rules, skills)
│   ├── .chezmoiexternal.yaml     # External skill sources not compatible with npx skills
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
