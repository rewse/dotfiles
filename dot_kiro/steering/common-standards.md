---
inclusion: always
---

# Common Standards

## Language Usage Guide

Use English for publicly accessible documents and Japanese for user-specific documents:

- Chat communication: Japanese
- Code comment: English
- Commit message: English
- Skill file: English
- Spec file: Japanese
- Steering file: English
- Variable name / Function names: English

The language of `README.md` is undefined. Always ask the user what language to use before creating a `README.md`.

## Chat Standards

### Chat Formats

Use a list or paragraph format to organize information. Do not use tables in chat because they render poorly in terminal-based interfaces and are hard to scan when content varies in length.

### Multiple Choices

Number multiple choices when presenting them to the user. This lets the user reply using just the number.

### Unexpected Changes

If you notice that the code or text you wrote has been unexpectedly changed, accept it without trying to undo it. That change was made by the user without going through you.

## Commit Message Standards

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages.

### File Deletion

When deleting files, choose the commit type based on the intent:

- `refactor:`: Deletion as part of a structural change to working code (e.g., merging, splitting, or relocating files)
- `fix:`: Deletion to correct a bug or mistake (e.g., removing an erroneously added file or a file causing issues)
- `chore:`: Deletion for general maintenance that does not fall into the above categories (e.g., removing obsolete or unused files)

### Dependency Updates

When updating dependencies, choose the commit type based on the intent:

- `fix:`: Updating to address a vulnerability or bug in a dependency
- `chore:`: Routine version bumps or general maintenance updates

## Spec File Standards

- Use plain form (常体) for spec files to keep the tone consistent and concise
- Prefer Mermaid for architecture diagrams since it can be version-controlled as text

## CLI Command Standards

### Pager Prevention

Always pipe output to `cat` or supply a flag like `--no-pager` when a CLI command may invoke a pager. If a pager launches, the AI process hangs indefinitely.

**Do**

- `git -P diff`
- `git -P log`
- `git -P show`
- `aws | cat`
- `gh | cat`

**Don't**

- `git diff`
- `git log`
- `git show`

### File Search

Do not use `find ~` or other overly broad paths — the search scope is too large and the command will not return useful results. Instead, infer a more specific path from context or ask the user.

## Coding Standards

### Coding Styles

Follow [Google Style Guides](https://google.github.io/styleguide/) as the baseline for coding styles. This provides a consistent, well-documented standard across languages.

### Comments

Write comments to explain background information or reasons that cannot be expressed in the code itself, or to explain code that is difficult to understand intuitively. Do not write comments for self-explanatory code. DRY: do not repeat between code and comments.

## Subagent

Always delegate tasks to other agents via `use_subagent` or `delegate` tools. Do not pipe to another agent because it pollutes your context with the subagent's entire output.

- NG: `printf "Find the root cause\n/quit\n" | kiro-cli chat --agent default`

### Agent Selection Standards

When using `use_subagent` or `delegate` tools:

- Select an appropriate specialized agent based on the task requirements
- If no specialized agent is suitable, use `default` as the agent name
- Do not use `kiro_default` as an agent name
