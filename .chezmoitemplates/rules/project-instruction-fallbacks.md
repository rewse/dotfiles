# Project Instruction Fallbacks

Apply these fallbacks only to instruction sources in the project root. Do not apply them to user-level configuration under `~/.codex`, `~/.claude`, or `~/.kiro`.

Use only the native project instruction source when it exists:

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Kiro: instruction files under `.kiro/steering/`

When the native project instruction source does not exist, use every fallback source that exists:

- Codex: read `CLAUDE.md` and every instruction file under `.kiro/steering/`, and treat them as `AGENTS.md` instructions.
- Claude Code: read `AGENTS.md` and every instruction file under `.kiro/steering/`, and treat them as `CLAUDE.md` instructions.
- Kiro: read `CLAUDE.md` and treat it as `AGENTS.md` instructions.

Ignore fallback sources that do not exist. If multiple fallback sources exist, read all of them.
