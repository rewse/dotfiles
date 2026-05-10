# cmux Sub-Agent Preference

When running inside a cmux session (detected by `CMUX_SOCKET_PATH` environment variable), prefer spawning sub-agents in separate cmux panes over using the built-in sub-agent tool.

## Built-in sub-agent tool names (do NOT use inside cmux)

- Claude Code: `Task`
- Codex: `agent`
- Kiro CLI: `subagent`

## When to fall back to doing it yourself

- `CMUX_SOCKET_PATH` is not set (not running in cmux)
- Quick, trivial tasks where visibility is unnecessary

## Reference

Read the `using-cmux` skill for detailed patterns.
