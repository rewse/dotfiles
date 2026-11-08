---
name: handling-continuum-reports
description: Use when a Continuum weekly report or finding issue arrives in rewse/continuum, or when triaging, fixing, or closing those issues.
---

# Handling Continuum Reports

Read the `using-superpowers` skill first and apply the process skills it points to: test-driven development for fixes, subagent-driven work for fan-out.

`~/git/continuum` files each Medium+ finding from Continuum pentests and code-vuln scans as an issue in `rewse/continuum`, and its sync workflow moves the issue between the state labels `new`, `wip`, and `pending`. Other labels give the severity (`severity:critical`, `severity:high`, `severity:medium`), the source (`pentest`, `code-vuln`), the target (`repo:<name>`), and `urgent`. Sync reopens an issue closed as completed when a scan that started after the close finds the finding again, and never reopens an issue closed as not planned, so closing a fixed finding as not planned hides a regression. Read `~/git/continuum/README.md` and `AGENTS.md` for the current rules before changing any issue.

## Workflow

1. **Collect.** List the open issues with `gh issue list --repo rewse/continuum --label <label> --state open --json number,title,labels,body,createdAt` (filter by `urgent`, `severity:*`, or `repo:<name>`) and save them to files in a `mktemp -d /tmp/...` directory, one file per target repository.
2. **Triage in parallel.** Dispatch one read-only subagent per target repository (small repositories may share one) with the issues file and the threat model: a single owner, a trusted home LAN, and earlier owner decisions. Each writes a table: issue number, severity, verdict (FIX / ACCEPT / FALSE_POSITIVE / DUPLICATE / NEEDS_OWNER), reason, fix and size. Ask it to challenge inflated severity and to name who could actually exploit the finding.
3. **Verify the urgent claims yourself.** Check internet exposure from outside the allowlists (for example with `tvly extract`), and check live state with the MCP servers or read-only host commands.
4. **Ask the owner once.** Present the tables as counts plus the notable items, and ask every NEEDS_OWNER question in one message. Fix anything confirmed reachable from the internet first.
5. **Fix in parallel.** Add `wip` to each issue as work starts (`gh issue edit <n> --repo rewse/continuum --add-label wip --remove-label new`). Dispatch one implementer subagent per repository: test first, run the repository's validation commands, commit locally, no push. Review each diff, then push, and wait until every CI run on the pushed commit succeeds.
6. **Apply.** Run `ansible-playbook ... --check --diff` before every real run, then verify on the host. Apply `chezmoi` changes and check what they affect.
7. **Write the records.** Act on each issue in `rewse/continuum` with the GitHub controls:
   - Fixed and applied: comment with the fixing commits (repository and SHA), then `gh issue close <n> --repo rewse/continuum --reason completed`. For a `pentest` issue, sync then starts a revalidation and reopens the issue as `new` if the finding still reproduces. A `code-vuln` issue waits for the next weekly scan.
   - Accepted risk or false positive: comment with the reason, then close with `--reason "not planned"`.
   - Duplicate: close with `gh issue close <n> --repo rewse/continuum --duplicate-of <surviving issue>` (GitHub's Close as duplicate), so sync moves the finding IDs to the surviving issue.
   - Partly fixed, or waiting on a manual step: comment with the status and leave the issue open with `wip`.
8. **Leave the weekly report issue alone.** The report workflow closes the previous week's report when it posts the next one.

## Rules

| Situation | Do |
|---|---|
| Fix pushed and applied | Comment the commits and close as completed; sync reopens it if the finding returns |
| Issue labeled `pending` | Leave the label to sync, which sets it after a completed scan misses the finding; never add or remove it by hand |
| Hidden `<!-- continuum-state: ... -->` marker | Never edit it; sync owns it |
| Public repository commit | Describe the change, never the finding or the issue |
| Owner rejects a fix after trying it | Revert, put the reason next to the setting, and close the issue as not planned with the reason |
| A blocked or destructive step, such as a history rewrite | Hand the owner the exact commands |
