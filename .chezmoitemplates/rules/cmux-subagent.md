# cmux Sub-Agent Preference

When running inside a cmux session (detected by `CMUX_SOCKET_PATH` environment variable), prefer spawning sub-agents in separate cmux panes over using the built-in sub-agent tool.

## Built-in sub-agent tool names (do NOT use inside cmux)

- Claude Code: `Task`
- Codex: `agent`
- Kiro CLI: `subagent`

## Use instead: cmux pane-based sub-agents

```bash
# 1. Create pane
SURF=$(cmux new-split right | awk '{print $2}')

# 2. Launch agent (pick one)
cmux send --surface $SURF "claude --dangerously-skip-permissions\n"
cmux send --surface $SURF "codex --dangerously-bypass-approvals-and-sandbox\n"
cmux send --surface $SURF "kiro-cli chat --trust-all-tools\n"

# 3. Wait for ready, send prompt
cmux send --surface $SURF "your prompt here\n"

# 4. Read result
cmux read-screen --surface $SURF

# 5. Cleanup
cmux send --surface $SURF "/quit\n"
sleep 2
cmux close-surface --surface $SURF
```

## When to fall back to doing it yourself

- `CMUX_SOCKET_PATH` is not set (not running in cmux)
- Quick, trivial tasks where visibility is unnecessary

## Reference

Read the `using-cmux` skill for detailed patterns: trust detection, completion polling, multi-line send rules, and `read-screen` troubleshooting.
