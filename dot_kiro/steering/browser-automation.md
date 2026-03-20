---
inclusion: always
---

# Browser Automation

### Preferred Option: agent-browser

Use `agent-browser` for web automation. Activate the `agent-browser` skill before the first command.

When taking snapshots, use filtering options to keep output small. Unfiltered snapshots can be very large and consume significant context.

- `-i`: Interactive elements only
- `-c`: Remove empty structural elements
- `-d <n>`: Limit tree depth
- `-s <sel>`: Scope to CSS selector

### Alternative Option: playwright-cli

If `agent-browser` cannot handle the task, use `playwright-cli` instead. Activate the `playwright-cli` skill before the first command.

Snapshot files are saved to `.playwright-cli/page-xxx.yml`. Search with `grep` to find the target element's ref instead of reading the entire file.
