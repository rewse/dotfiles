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

Use a list or paragraph format to organize information. Do not use tables in chat, as they break in terminal output.

### Multiple Choices

Number multiple choices when presenting them to the user.

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

- Use plain form (常体) for spec files
- Prefer Mermaid for architecture diagrams

## CLI Command Standards

### Pager Prevention

Always pipe output to `cat` or supply a flag like `--no-pager` when a CLI command may invoke a pager, as an interactive pager hangs the process indefinitely.

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

On macOS, use `mdfind` for file searches. Spotlight indexing makes broad paths like `mdfind -onlyin ~` fast and acceptable.

On Linux, do not use `find ~` or other overly broad paths, as the search scope is too large and takes too long. Instead, infer a more specific path from context or ask the user.

### URL Fetch Retry

When a URL fetch is denied (403, access denied, bot block), retry with `defuddle parse -m <URL>`.

## Ordering Standards

Sort entries alphabetically whenever their order does not carry meaning. This applies everywhere: list items, configuration entries, package lists, imports, dictionary keys, and similar collections. Keep a deliberate order only when it is significant (e.g., execution sequence, dependency order, or priority).

## Rule Authoring Standards

Lead with the instruction or prohibition in rule files. Keep rationale minimal, and add it only when it clarifies the scope of a rule. Omit background that does not change how a rule is applied.

## Writing Standards

### Line Wrapping

Do not hard-wrap prose. Write each paragraph as a single line and let the editor soft-wrap it. This applies to Markdown documents, specs, READMEs, and rule files. It does not apply to code, code blocks, or list items, where line breaks are meaningful.

## Coding Standards

### Coding Styles

Follow [Google Style Guides](https://google.github.io/styleguide/) as the baseline for coding styles.

### Comments

Write comments to explain background information or reasons that cannot be expressed in the code itself, or to explain code that is difficult to understand intuitively. Do not write comments for self-explanatory code. DRY: do not repeat between code and comments.
