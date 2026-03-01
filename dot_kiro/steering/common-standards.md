# Common Standards

## Language Usage Guide

As a general principle, you SHOULD use English for publicly accessible documents and Japanese for user-specific documents:

- Chat communication: Japanese
- Code comment: English
- Commit message: English
- Skill file: English
- Spec file: Japanese
- Steering file: English
- Variable name / Function names: English

The language of `README.md` is undefined. You MUST ask the user what language to use before creating a `README.md`.

## Chat Standards

### Chat Formats

You MUST NOT use a table format in chat. You MUST use a list or paragraph format to organize information.

### Multiple Choices

You MUST number multiple choices when presenting them to the user. By assigning numbers, the user can reply using just the number.

### Unexpected Changes

If you notice that the code or text you wrote has been unexpectedly changed, you MUST accept it without trying to undo it. That change was made by the user without going through you.

## Commit Message Standards

You MUST follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages.

### File Deletion

When deleting files, you MUST choose the commit type based on the intent:

- `refactor:`: Deletion as part of a structural change to working code (e.g., merging, splitting, or relocating files)
- `fix:`:  Deletion to correct a bug or mistake (e.g., removing an erroneously added file or a file causing issues)
- `chore:`: Deletion for general maintenance that does not fall into the above categories (e.g., removing obsolete or unused files)

### Dependency Updates

When updating dependencies, you MUST choose the commit type based on the intent:

- `fix:`: Updating to address a vulnerability or bug in a dependency
- `chore:`: Routine version bumps or general maintenance updates

## Spec File Standards

- You MUST use plain form (常体) for spec files
- You MUST use Mermaid for architecture diagrams

## CLI Command Standards

If a CLI command may invoke a pager, you MUST pipe the output to `cat` or supply an appropriate flag like `--no-pager` to prevent the pager from launching.

### Do

- `git -P diff`
- `git -P log`
- `git -P show`
- `aws | cat`
- `gh | cat`

### Don't

- `git diff`
- `git log`
- `git show`

## Coding Standards

### Coding Styles

You MUST follow [Google Style Guides](https://google.github.io/styleguide/) for coding styles.

### Comments

You MUST write comments to explain background information or reasons that cannot be expressed in the code itself, or to explain code that is difficult to understand intuitively using natural language. You SHOULD NOT write comments for self-explanatory code. DRY: Do not repeat between code and comments.


## Browser Automation

- You SHOULD use `agent-browser` for web automation.

## IMPORTANT: First Command Rule

You MUST run `agent-browser --help` BEFORE the FIRST `agent-browser` command. This ensures you have the latest command syntax and available operations.

## Typical Workflow

**Pre-check:**: Confirm `agent-browser --help` has been executed in this session

1. `agent-browser open <url>` - Navigate to page
2. `agent-browser snapshot -i` - Get interactive elements with refs (@e1, @e2)
3. `agent-browser click @e1` / `fill @e2 "text"` - Interact using refs
4. Re-snapshot after page changes
