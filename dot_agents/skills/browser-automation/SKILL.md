---
name: browser-automation
description: Personal browser automation preferences and configuration. Use when the user needs web automation, browser interaction, headed mode, or connecting to Arc browser via CDP. Also use when agent-browser or playwright-cli is about to be used, to ensure correct engine selection and connection settings.
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

3. Run agent-browser with `--cdp 9222`. Close any stale daemon first to avoid cached state:

   ```bash
   agent-browser close --all
   agent-browser --cdp 9222 open <url>
   ```

   Arc may bind to IPv4 (`127.0.0.1`) or IPv6 (`[::1]`) depending on the launch — passing just the port number lets agent-browser auto-detect. If you get `Invalid CDP target` errors, the daemon is holding stale state; run `agent-browser close --all` and retry.

### Alternative Option: playwright-cli

If `agent-browser` cannot handle the task, use `playwright-cli` instead. Activate the `playwright-cli` skill before the first command.
