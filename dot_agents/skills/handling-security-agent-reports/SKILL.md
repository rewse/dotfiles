---
name: handling-security-agent-reports
description: Use when an AWS Security Agent weekly report issue arrives in rewse/security-agent, or when triaging, fixing, documenting, or closing the draft security advisories and security-agent issues it files in rewse/* repositories.
---

# Handling Security Agent Reports

Read the `using-superpowers` skill first and apply the process skills it points to: test-driven development for fixes, subagent-driven work for fan-out.

`~/git/security-agent` files each Medium+ finding as a draft repository advisory (public repositories) or a `security-agent` issue (private repositories), identified by a `<!-- security-agent-fingerprint: ... -->` marker. Its reconciler drops every finding whose record is closed, so a record closed too early hides a regression for good. Read `~/git/security-agent/AGENTS.md` and `src/security_agent_scan/github.py` for the current rules before changing any record.

## Workflow

1. **Collect.** List open records per repository (`gh api repos/rewse/<repo>/security-advisories?state=draft`, `gh issue list -l security-agent`) and save them to files in a `mktemp -d /tmp/...` directory, keeping each repository's issue numbers separate.
2. **Triage in parallel.** Dispatch one read-only subagent per repository (small repositories may share one) with the records file and the threat model: a single owner, a trusted home LAN, and earlier owner decisions. Each writes a table: id, severity, verdict (FIX / ACCEPT / FALSE_POSITIVE / NEEDS_OWNER), reason, fix and size. Ask it to challenge inflated severity and to name who could actually exploit the finding.
3. **Verify the urgent claims yourself.** Check internet exposure from outside the allowlists (for example with `tvly extract`), and check live state with the MCP servers or read-only host commands.
4. **Ask the owner once.** Present the tables as counts plus the notable items, and ask every NEEDS_OWNER question in one message. Fix anything confirmed reachable from the internet first.
5. **Fix in parallel.** Dispatch one implementer subagent per repository: test first, run the repository's validation commands, commit locally, no push. Review each diff, then push.
6. **Apply.** Run `ansible-playbook ... --check --diff` before every real run, then verify on the host. Apply `chezmoi` changes and check what they affect.
7. **Write the records.** For a repository advisory, PATCH `description`, adding a section just before the marker and keeping the marker last; advisories have no comment API. For an issue, add a comment.
   - Fixed: `## Remediation (YYYY-MM-DD)` with the commits. Leave the record open.
   - Accepted or false positive: `## Resolution (YYYY-MM-DD)` with the reason. Close the record.
8. **Next scan.** Close a fixed record only after the next weekly scan no longer reports its fingerprint.

## Rules

| Situation | Do |
|---|---|
| Fix pushed and applied | Keep the record open until the next scan confirms |
| Public repository commit | Describe the change, never the finding or GHSA ID |
| Owner rejects a fix after trying it | Revert, put the reason next to the setting, and mark the record accepted |
| A blocked or destructive step, such as a history rewrite | Hand the owner the exact commands |
