---
inclusion: always
---

# Browser Automation

### Preferred Option: playwright-cli

- You SHOULD use `playwright-cli` for web automation
- You MUST activate the `playwright-cli` skill BEFORE the FIRST `playwright-cli` command
- Snapshot files are saved to `.playwright-cli/page-xxx.yml`. Search with `grep` to find the target element's ref instead of reading the entire file

### Alternative Option: agent-browser

- If you cannot do what you expect with `playwright-cli`, you MAY use `agent-browser`
- You MUST activate the `agent-browser` skill BEFORE the FIRST `agent-browser` command
