# Common Standards

## Language Usage Guide

Use English for publicly accessible documents and Japanese for user-facing interaction:

- Chat communication: Japanese
- Code comment: English
- Commit message: English
- Skill file: English
- Spec file: Japanese
- Steering file: English
- Variable name / Function names: English

The language of `README.md` is undefined. Always ask the user what language to use before creating a `README.md`.

## Chat Standards

### Unexpected Changes

If you notice that the code or text you wrote has been unexpectedly changed, accept it without trying to undo it. That change was made by the user without going through you.

## Commit Message Standards

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages.

Choose the type by the intent of the change, not by the mechanism. Deleting a file or updating a dependency is not `chore:` by default: use `fix:` for a bug or vulnerability, `refactor:` for restructuring working code, `docs:` when the file is documentation, `feat:` when a user-facing capability is removed, and `chore:` only for maintenance that fits none of these.

## Spec File Standards

- Use plain form (常体) for spec files
- Prefer Mermaid for architecture diagrams

## CLI Command Standards

### Pager Prevention

Always pipe output to `cat` or supply a flag like `--no-pager` when a CLI command may invoke a pager, as an interactive pager hangs the process indefinitely.

- `aws | cat`
- `chezmoi --no-pager <any command>`
- `gh | cat`
- `git -P <any commands>`

### File Search

On macOS, use `mdfind` for file searches. Spotlight indexing makes broad paths like `mdfind -onlyin ~` fast and acceptable.

### Container Runtime

On macOS, use `container` instead of `docker`. On Linux, use `docker`.

### URL Fetch Retry

When a URL fetch is denied (403, access denied, bot block), retry with `tvly extract <URL> --format markdown --json`. Tavily fetches server-side, so the block on this host does not apply.

## Ordering Standards

Sort entries alphabetically whenever their order does not carry meaning. This applies everywhere: list items, configuration entries, package lists, dictionary keys, and similar collections. Keep a deliberate order only when it is significant (e.g., execution sequence, dependency order, or priority).

## Rule Authoring Standards

Lead with the instruction or prohibition in rule files. Keep rationale minimal, and add it only when it clarifies the scope of a rule or forecloses a plausible wrong workaround. Omit background that does not change how a rule is applied.

## Writing Standards

### Line Wrapping

Do not hard-wrap prose. Write each paragraph as a single line and let the editor soft-wrap it. This applies to Markdown documents, specs, READMEs, and rule files. It does not apply to code, code blocks, or list items, where line breaks are meaningful.

### Humanizer

Before finalizing prose longer than a few paragraphs (documentation, README, specs, or similar), read `~/.agents/skills/humanizer/SKILL.md` and remove the AI writing patterns it lists. This does not apply to code comments, commit messages, chat messages, or structured data.

## Coding Standards

Follow [Google Style Guides](https://google.github.io/styleguide/) as the baseline for coding styles.
