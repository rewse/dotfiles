---
inclusion: always
---

# Browser Automation

### Preferred Option: agent-browser

Use `agent-browser` for web automation. Activate the `agent-browser` skill before the first command.

#### Engine Selection

Use `--engine lightpanda` by default. It is ~10x faster and uses ~16x less memory than Chrome.

Fall back to the default Chrome engine when Lightpanda fails or crashes on the target site:

```bash
# Default: use Lightpanda
agent-browser --engine lightpanda open <url>

# Fallback: Chrome (omit --engine)
agent-browser open <url>
```

When authentication or headed mode is needed, connect to the user's Arc browser instead of launching a new Chrome engine. See [Headed Mode: Connect to Arc](#headed-mode-connect-to-arc) below.

#### Headed Mode: Connect to Arc

Connect to the user's Arc browser (Chromium-based) via CDP when authentication or headed mode is needed. Arc is preferred over Chrome because:

- Chrome M136+ blocks `--remote-debugging-port` on the default profile (DevToolsActivePort not created)
- Arc uses a separate user data directory, so the restriction does not apply
- Arc retains the user's extensions (e.g., 1Password) and login state

Steps:

1. Quit Arc if already running.
2. Launch Arc with remote debugging enabled:

   ```bash
   nohup "/Applications/Arc.app/Contents/MacOS/Arc" --remote-debugging-port=9222 >/tmp/arc.log 2>&1 &
   ```

3. Extract the WebSocket debugger URL from `/tmp/arc.log`:

   ```bash
   WS_URL=$(grep -o 'ws://\[::1\]:9222/devtools/browser/[a-f0-9-]*' /tmp/arc.log | head -1)
   ```

   Arc binds only to IPv6 (`[::1]`), so the URL uses `ws://[::1]:9222/...` instead of `ws://127.0.0.1:...`.

4. Run agent-browser with `--cdp` pointing to the WebSocket URL:

   ```bash
   agent-browser --cdp "$WS_URL" open <url>
   ```

### Alternative Option: playwright-cli

If `agent-browser` cannot handle the task, use `playwright-cli` instead. Activate the `playwright-cli` skill before the first command.
