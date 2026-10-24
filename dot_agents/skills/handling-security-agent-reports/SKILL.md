---
name: handling-security-agent-reports
description: Use when an AWS Security Agent weekly report issue arrives in rewse/security-agent, or when triaging, fixing, documenting, or closing the draft security advisories and security-agent issues it files in rewse/* repositories.
---

# Handling Security Agent Reports

Read the `using-superpowers` skill first and apply the process skills it points to: test-driven development for fixes, subagent-driven work for fan-out.

`~/git/security-agent` files each Medium+ finding as a draft repository advisory (public repositories) or a `security-agent` issue (private repositories), identified by a `<!-- security-agent-fingerprint: ... -->` marker. A record closed as fixed is reopened when its fingerprint is detected again; a record closed as not planned is suppressed for good, so closing a fixed finding as not planned hides a regression. Read `~/git/security-agent/AGENTS.md` and `src/security_agent_scan/github.py` for the current rules before changing any record.

## Workflow

1. **Collect.** List open records per repository (`gh api repos/rewse/<repo>/security-advisories?state=draft`, `gh issue list -l security-agent`) and save them to files in a `mktemp -d /tmp/...` directory, keeping each repository's issue numbers separate. For each record under Reopened, compare the `createdAt` of the job that detected it with the date in the record's Remediation section, since reopening clears `closed_at`. A job that started before the close scanned the unfixed code, so close the record again instead of triaging it.
2. **Triage in parallel.** Dispatch one read-only subagent per repository (small repositories may share one) with the records file and the threat model: a single owner, a trusted home LAN, and earlier owner decisions. Each writes a table: id, severity, verdict (FIX / ACCEPT / FALSE_POSITIVE / NEEDS_OWNER), reason, fix and size. Ask it to challenge inflated severity and to name who could actually exploit the finding.
3. **Verify the urgent claims yourself.** Check internet exposure from outside the allowlists (for example with `tvly extract`), and check live state with the MCP servers or read-only host commands.
4. **Ask the owner once.** Present the tables as counts plus the notable items, and ask every NEEDS_OWNER question in one message. Fix anything confirmed reachable from the internet first.
5. **Fix in parallel.** Dispatch one implementer subagent per repository: test first, run the repository's validation commands, commit locally, no push. Review each diff, then push, and wait until every CI run on the pushed commit succeeds.
6. **Apply.** Run `ansible-playbook ... --check --diff` before every real run, then verify on the host. Apply `chezmoi` changes and check what they affect.
7. **Write the records.** For a repository advisory, PATCH `description`, adding a section just before the marker and keeping the marker last; advisories have no comment API. For an issue, add a comment.
   - Fixed and applied: `## Remediation (YYYY-MM-DD)` with the commits. Close the record: an advisory with `state: closed`, an issue with `--reason completed`.
   - Accepted or false positive: `## Resolution (YYYY-MM-DD)` with the reason. Close the record as not planned: for an advisory, add `<!-- security-agent-resolution: not-planned -->` on its own line before the fingerprint marker in the same PATCH; for an issue, use `--reason "not planned"`.
   - Partly fixed, or waiting on a manual step: write the section and leave the record open.
8. **Close the weekly issue** once all its findings are handled. The workflow changes only the current week's issue.

## Rules

| Situation | Do |
|---|---|
| Fix pushed and applied | Close as fixed; the report reopens it if the finding returns |
| Public repository commit | Describe the change, never the finding or GHSA ID |
| Owner rejects a fix after trying it | Revert, put the reason next to the setting, and mark the record accepted |
| A blocked or destructive step, such as a history rewrite | Hand the owner the exact commands |
