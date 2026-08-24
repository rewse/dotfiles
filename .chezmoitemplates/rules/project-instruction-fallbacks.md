# Project Instruction Fallbacks

Apply these fallbacks only to instruction sources in the project root. Do not apply them to user-level configuration under `~/.codex`, `~/.claude`, or `~/.kiro`.

Use all native project instruction sources that exist:

- Codex: `AGENTS.md`
- Claude Code: `CLAUDE.md`
- Kiro: `AGENTS.md` and every instruction file under `.kiro/steering/`

Do not read fallback sources when at least one native project instruction source exists.

When no native project instruction source exists, use every fallback source that exists:

- Codex: read `CLAUDE.md` and every instruction file under `.kiro/steering/`, and treat them as `AGENTS.md` instructions.
- Claude Code: read `AGENTS.md` and every instruction file under `.kiro/steering/`, and treat them as `CLAUDE.md` instructions.
- Kiro: read `CLAUDE.md` and treat it as `AGENTS.md` instructions.

Ignore fallback sources that do not exist. If multiple fallback sources exist, read all of them.
