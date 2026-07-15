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

- `aws | cat`
- `chezmoi --no-pager <any command>`
- `gh | cat`
- `git -P <any commands>`

**Don't**

- `chezmoi diff`
- `git diff`

### Python stdin Read Hangs

Do not pipe into a `python3 -c` snippet that reads standard input (`sys.stdin.read()`, `json.load(sys.stdin)`, `for line in sys.stdin`) inside a Bash tool call. When the upstream stream does not send EOF, Python blocks on the read forever. `timeout` does not help: the `python3` runs as a grandchild of `timeout`, so it is reparented and keeps waiting after `timeout` kills its parent shell (same failure mode as the grep hang above).

Instead, save the data to a file and read it with the Read tool, or pass the path as an argument (`python3 script.py /tmp/foo.json`) so Python opens the file directly. If a pipe is unavoidable, redirect from a file (`python3 -c '...' < /tmp/foo.json`) so EOF is guaranteed.

### File Search

On macOS, use `mdfind` for file searches. Spotlight indexing makes broad paths like `mdfind -onlyin ~` fast and acceptable.

On Linux, do not use `find ~` or other overly broad paths, as the search scope is too large and takes too long. Instead, infer a more specific path from context or ask the user.

### Container Runtime

On macOS, use `container` instead of `docker`. On Linux, use `docker`.

### URL Fetch Retry

When a URL fetch is denied (403, access denied, bot block), retry with `defuddle parse -m <URL>`.

## Ordering Standards

Sort entries alphabetically whenever their order does not carry meaning. This applies everywhere: list items, configuration entries, package lists, imports, dictionary keys, and similar collections. Keep a deliberate order only when it is significant (e.g., execution sequence, dependency order, or priority).

## Rule Authoring Standards

Lead with the instruction or prohibition in rule files. Keep rationale minimal, and add it only when it clarifies the scope of a rule. Omit background that does not change how a rule is applied.

## Writing Standards

### Line Wrapping

Do not hard-wrap prose. Write each paragraph as a single line and let the editor soft-wrap it. This applies to Markdown documents, specs, READMEs, and rule files. It does not apply to code, code blocks, or list items, where line breaks are meaningful.

### Humanizer

When writing prose longer than a few sentences (documentation, README, specs, commit descriptions, or any multi-paragraph text), apply the humanizer skill to remove AI writing patterns before finalizing. This does not apply to code comments, chat messages, or structured data.

## Coding Standards

### Coding Styles

Follow [Google Style Guides](https://google.github.io/styleguide/) as the baseline for coding styles.

### Comments

Write comments to explain background information or reasons that cannot be expressed in the code itself, or to explain code that is difficult to understand intuitively. Do not write comments for self-explanatory code. DRY: do not repeat between code and comments.
