---
name: browser-automation
description: Personal browser automation preferences and configuration. Use when the user needs web automation, browser interaction, headed mode, or connecting to the user's Google Chrome via CDP. Also use when agent-browser or playwright-cli is about to be used, to ensure correct engine selection and connection settings.
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

When authentication or headed mode is needed, connect to the user's running Google Chrome instead of launching a new Chrome engine. See [Headed Mode: Connect to Chrome](#headed-mode-connect-to-chrome) below.

#### Headed Mode: Connect to Chrome

Connect to the user's Google Chrome over CDP when authentication or headed mode is needed. This attaches to the real default profile (`~/Library/Application Support/Google/Chrome/Default`), so installed extensions such as 1Password and existing login state are available.

One-time setup: open `chrome://inspect/#remote-debugging` in Chrome and enable "Allow remote debugging for this browser instance" (requires Chrome 144+). The setting persists in `Local State` under `devtools.remote_debugging.user-enabled`, and Chrome then listens on port 9222 on every normal launch.

Steps:

1. Make sure Chrome is running. Launch it normally — do not pass `--remote-debugging-port`.
2. Connect to the GUID-less browser endpoint, and open a new tab before the first navigation so the user's existing tabs stay untouched:

   ```bash
   agent-browser --cdp "ws://127.0.0.1:9222/devtools/browser" tab new
   agent-browser --cdp "ws://127.0.0.1:9222/devtools/browser" open <url>
   ```

Start every new task with `tab new`. Never navigate a tab the user already had open, and keep working in the tab you created for the rest of the task. `tab list` shows which tab is active (`→`).

Constraints to respect:

- Chrome 136+ ignores `--remote-debugging-port` and `--remote-debugging-pipe` whenever the data directory is the default one, and prints `DevTools remote debugging requires a non-default data directory.` Passing a path that resolves to the default directory (trailing `/.`, a symlink) does not bypass the check, because Chrome normalizes the path first.
- Pass the WebSocket URL, not `--cdp 9222`. In this mode Chrome serves only the browser WebSocket; every `/json/*` HTTP endpoint returns 404, so port-only discovery times out.
- `--auto-connect` works only while `~/Library/Application Support/Google/Chrome/DevToolsActivePort` exists. That file disappears at times even though Chrome keeps listening on 9222, so prefer the explicit WebSocket URL.
- Never launch Chrome with a `--user-data-dir` that resolves to the default directory. Chrome treats the profile as tampered, resets its protected preferences, and uninstalls every extension in that profile. Recovering needs a backup.
- Do not use `--profile Default` to reach the real profile. agent-browser launches its bundled Chrome for Testing with a temporary user data directory, so extensions and login state are absent.
- Run `agent-browser close --all` only to clear a stale daemon holding `Invalid CDP target` errors. It can also close the connected Chrome window, so relaunch Chrome afterwards.
- While remote debugging is enabled, any local process can drive the browser and read its cookies. Keep it on only on a trusted machine.
