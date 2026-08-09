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

### Approach Before Acting

When a request is ambiguous or spans multiple steps or files, state how it was read and the approach to be taken, then continue into the work in the same turn. This is a statement, not an approval gate. Act immediately on a small, clear request.

### Corrections

Note a correction to an earlier statement only when the error would change the user's code, conclusions, or decisions. For a slip that changes nothing, fix it and move on.

### Progress Updates

Report rather than narrate: give an interim update when something important is found or the direction changes, and lead the closing report with the outcome.

### Response Length

Spend most of a response on the main answer, keep caveats short, and summarize at a high level unless depth is requested.

### Task Scope

Deliver what was asked, at the scope intended. Make routine judgment calls without asking, and check in only when different readings would lead to materially different work. When the request looks mistaken or a better approach exists, say so in a sentence and continue as asked.

### Unexpected Changes

If you notice that the code or text you wrote has been unexpectedly changed, accept it without trying to undo it. That change was made by the user without going through you.

## Commit Message Standards

Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/) for commit messages.

Choose the type by the intent of the change, not by the mechanism. Deleting a file or updating a dependency is not `chore:` by default: use `fix:` for a bug or vulnerability, `refactor:` for restructuring working code, `docs:` when the file is documentation, `feat:` when a user-facing capability is removed, and `chore:` only for maintenance that fits none of these.

## Spec File Standards

- Use plain form (常体) for spec files
- Prefer Mermaid for architecture diagrams

## CLI Command Standards

### AWS Skill Discovery

Before starting an AWS task, look for a relevant AWS skill: run `mcporter call aws-mcp.aws___search_documentation search_phrase="..."` to discover what exists, then `mcporter call aws-mcp.aws___retrieve_skill skill_name="<skill-name>"` to load one, and prefer its guidance over general knowledge. Do not use `npx skills find/search` for AWS skill discovery.

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

### Web Search

Use `tvly` for web search, not a built-in web search or fetch tool. Before running `tvly`, read the matching skill for the subcommand in use (`tavily-crawl`, `tavily-extract`, `tavily-map`, `tavily-research`, `tavily-search`) and follow its guidance on flags and output handling.

## Ordering Standards

Sort entries alphabetically unless their order carries meaning (execution sequence, dependency order, priority). This applies to list items, configuration entries, package lists, dictionary keys, and similar collections.

## Rule Authoring Standards

Lead with the instruction or prohibition in rule files. Add rationale only when it clarifies the scope of a rule or forecloses a plausible wrong workaround.

## Writing Standards

### Document Length

Match document length to what the task needs. Cover the substance without filler sections, redundant summaries, or boilerplate.

### Line Wrapping

Do not hard-wrap prose: write each paragraph as a single line and let the editor soft-wrap it. This applies to Markdown documents, specs, READMEs, and rule files, but not to code, code blocks, or list items, where line breaks are meaningful.

### Humanizer

Before finalizing prose longer than a few paragraphs (documentation, README, specs), read `~/.agents/skills/humanizer/SKILL.md` and remove the AI writing patterns it lists. This does not apply to code comments, commit messages, chat messages, or structured data.

## Coding Standards

Follow [Google Style Guides](https://google.github.io/styleguide/) as the baseline for coding styles.

### Code Comments

Write comments about the code as it stands, not about the change that produced it. Put the history in the commit message: the previous behavior, the version that changed it, the alternatives rejected, and how the change was verified.
