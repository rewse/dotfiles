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

## Agent Selection Standards

When using `delegate` or `use_subagent` tools:

- You MUST select an appropriate specialized agent based on the task requirements
- If no specialized agent is suitable, you MUST use `default` as the agent name
- You MUST NOT use `kiro_default` as an agent name

## Browser Automation

### Preferred Option: playwright-cli

- You SHOULD use `playwright-cli` for web automation
- You MUST activate the `playwright-cli` skill BEFORE the FIRST `playwright-cli` command
- Snapshot files are saved to `.playwright-cli/page-xxx.yml`. Search with `grep` to find the target element's ref instead of reading the entire file

### Alternative Option: agent-browser

- If you cannot do what you expect with `playwright-cli`, you MAY use `agent-browser`
- You MUST activate the `agent-browser` skill BEFORE the FIRST `agent-browser` command
