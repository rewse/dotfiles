---
inclusion: always
---

# Browser Automation

### Preferred Option: agent-browser

Use `agent-browser` for web automation. Activate the `agent-browser` skill before the first command.

#### Engine Selection

Use `--engine lightpanda` by default. It is ~10x faster and uses ~16x less memory than Chrome.

Fall back to the default Chrome engine when:

- Authentication is explicitly required (login, `--profile`, `--state`)
- Headed mode is needed (`--headed`)
- Lightpanda fails or crashes on the target site

```bash
# Default: use Lightpanda
agent-browser --engine lightpanda open <url>

# Fallback: Chrome (omit --engine)
agent-browser open <url>

# Headed mode: connect to the user's existing Chrome via the DevToolsActivePort file
# Requires remote debugging enabled at chrome://inspect/#remote-debugging
PORT=$(sed -n '1p' "$HOME/Library/Application Support/Google/Chrome/DevToolsActivePort")
WS_PATH=$(sed -n '2p' "$HOME/Library/Application Support/Google/Chrome/DevToolsActivePort")
agent-browser --cdp "ws://127.0.0.1:${PORT}${WS_PATH}" open <url>
```

### Alternative Option: playwright-cli

If `agent-browser` cannot handle the task, use `playwright-cli` instead. Activate the `playwright-cli` skill before the first command.
