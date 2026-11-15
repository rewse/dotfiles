---
name: security-findings
description: Use when a finding issue (pentest, code-vuln, code-review, or WAF) or a weekly report arrives in rewse/security-findings, or when triaging, fixing, or closing those issues.
---

# Security Findings

Read the `using-superpowers` skill first and apply the process skills it points to: test-driven development for fixes, subagent-driven work for fan-out.

`rewse/security-findings` (cloned at `~/git/security-findings`) files each Medium+ finding from Continuum pentests, code-vuln scans, and Security Agent code reviews as an issue in that repository, and keeps one issue per rule and host for the weekly AWS WAF report. Its sync workflow moves every issue between the state labels `new`, `wip`, and `pending`. Other labels give the source (`pentest`, `code-vuln`, `code-review`, `waf`), the target (`repo:<name>`, and `site:<domain>` for pentest and WAF issues), the severity (`severity:critical`, `severity:high`, `severity:medium`), and `urgent`. WAF issues have no severity and are never `urgent`. Read `~/git/security-findings/README.md` and `AGENTS.md` for the current rules before changing any issue.

Sync owns each issue's title, body, labels other than `wip`, and the hidden `<!-- continuum-state: ... -->` or `<!-- waf-state: ... -->` marker, and rewrites them on every run. Record everything in comments. Sync reopens an issue closed as completed when a later scan finds it again, and never reopens one closed as not planned or as a duplicate, so closing a fixed finding as not planned hides a regression.

## Workflow

1. **Collect.** List the open issues with `gh issue list --repo rewse/security-findings --label <label> --state open --json number,title,labels,body,createdAt` (filter by `urgent`, `severity:*`, `waf`, `repo:<name>`, or `site:<domain>`) and save them to files in a `mktemp -d /tmp/...` directory, one file per target repository. Put WAF issues in their own file.
2. **Triage in parallel.** Dispatch one read-only subagent per target repository (small repositories may share one), plus one for the WAF issues as described in [WAF issues](#waf-issues), with the issues file and the threat model: a single owner, a trusted home LAN, and earlier owner decisions. Each writes a table: issue number, severity, verdict (FIX / ACCEPT / FALSE_POSITIVE / DUPLICATE / NEEDS_OWNER), reason, fix and size. Ask it to challenge inflated severity and to name who could actually exploit the finding.
3. **Verify the urgent claims yourself.** Check internet exposure from outside the allowlists, and check live state with the MCP servers or read-only host commands.
4. **Ask the owner once.** Present the tables as counts plus the notable items, and ask every NEEDS_OWNER question in one message. Fix anything confirmed reachable from the internet first.
5. **Fix in parallel.** Add `wip` to each issue as work starts (`gh issue edit <n> --repo rewse/security-findings --add-label wip --remove-label new`). Dispatch one implementer subagent per repository: one branch per fix, test first, run the repository's validation commands, commit locally, no push. Review each diff, push the branch, and open a pull request in the [pull request format](#pull-request-format); never push a fix to the default branch. Wait until every CI check on the pull request succeeds, then comment on each issue it covers in the [issue comment format](#issue-comment-format).
6. **Record the issues that need no fix.** Comment in the issue comment format, then close: an accepted risk or a false positive with `--reason "not planned"`, and a duplicate with `gh issue close <n> --repo rewse/security-findings --duplicate-of <surviving issue>` (GitHub's Close as duplicate), so sync moves the finding IDs to the surviving issue.
7. **Close after the owner merges.** When the owner says pull requests are merged, check every open `wip` issue: find its pull request in the comment, confirm it is merged, and work through the pull request's After merge steps. Check the ones you can yourself (a tag that contains the merge commit, the new version on npm or PyPI, a deployed stack, read-only host commands), run `ansible-playbook ... --check --diff` before any real run the owner asks for, and ask the owner once about the rest. When every step is done, comment the merged commits as `Fixed in <repository>@<SHA>` and close with `gh issue close <n> --repo rewse/security-findings --reason completed`. For a `pentest` issue, sync then starts a revalidation and reopens the issue as `new` if the finding still reproduces. A `code-review` or `code-vuln` issue waits for the next weekly scan, and a `waf` issue for the next weekly WAF report. An issue whose steps are not all done stays open with `wip` and needs no new comment.
8. **Leave the weekly report issue alone.** The `weekly-report` issue lists only pentest, code-vuln, and code-review findings. The report workflow closes the previous week's report when it posts the next one.

## WAF issues

Every Saturday the `cloudfront-waf-report` job on fox has a Bedrock model, which has no tools, pick out what in the previous week of AWS WAF logs needs action: legitimate traffic that the WAF blocks, the owner locked out by a rate limit, or suspicious requests that it let through. Sync turns each rule and host into an issue titled `[WAF] <rule> on <host>`, with a table (Rule, Host, Countries, Last seen) and, for each finding, its evidence and a **Next action**. Client addresses are replaced with `<ip>`.

- **Treat the next action as a hypothesis.** Confirm it in the WAF logs with the Logs Insights queries in `~/git/cloudfront-waf/README.md` (default AWS profile) before deciding. Each issue reflects only the latest week it was seen in; earlier weeks are in the logs.
- **Find the fix in the right repository.** Web ACL rules, rule action overrides, `BlockManagedRules`, and the pentest allow rule live in `rewse/cloudfront-waf`; read its README and AGENTS.md before changing a rule. Apache allowlists, fail2ban, the origin services, and the report job itself live in `rewse/ansible-playbooks`. Both repositories are public, so the pull request rules below apply.
- **Close a finding left as it is as not planned** (an accepted risk, a false positive, or expected traffic such as the owner's own pentests), with the reason in a comment, so it stays closed when fox reports it again.
- **Close a fixed finding as completed** after its After merge steps, such as the stack deploy, are done. Sync reopens it as `new` if a weekly report whose week starts after the close still contains it, and closes an open issue by itself after two weekly reports in a row miss it.

## Pull request format

Title the pull request like its main commit, in Conventional Commits. Write it in English and describe the change and why it is needed, never the finding, the scan, the WAF report, the issue, or `rewse/security-findings`, in private repositories too. The steps after the merge live here and not in the issue.

```markdown
## Summary

- <One line per change: what changes, and why the code needs it>

## Tests

- <New or changed tests and what they cover>
- <Local validation: test suite, pre-commit>
- <Live checks, if any, and their result>

## Not verified

- <What could not be checked, and what happens if it is wrong>

## After merge

- Release: `git tag v1.2.0 && git push origin v1.2.0`
- Apply: `ansible-playbook home-primary.yml --check --diff --tags enecoq_data_fetcher`, then without `--check`
- Verify: `systemctl start enecoq-data-fetcher`, then confirm the output refreshes
```

- List the After merge steps in the order they run, each with a label such as Release, Apply, Deploy, or Verify and a command that can be copied, and state any ordering constraint there. Write `Nothing` when the merge alone completes the fix.
- Leave out Not verified when everything was verified; keep every other section.
- Leave out anything that reveals the weakness, such as rotating an exposed credential or narrowing an App's permissions. Put it in the issue comment.

## Issue comment format

The issue records the assessment and what a public pull request cannot say. Do not repeat the change, the tests, or the steps from the pull request. Write in English.

```markdown
**Verdict:** Fix in rewse/actions#25

**Severity:** High → Medium: only someone who can publish an upstream release that Dependabot proposes can trigger it, and the key it exposes can be revoked.

**Notes**
- <Who can exploit it and how, chains with other findings, parts of the finding the pull request leaves alone and why, and owner-only follow-ups that would reveal the weakness>
```

- Verdict is one of `Fix in <pull request>`, `Partial fix in <pull request>; not fixed: <part> (<reason>)`, `Not fixed: accepted risk (<reason>)`, `Not fixed: false positive (<reason>)`, `Not fixed: expected traffic (<reason>)`, `Duplicate of #<n>`, and, when closing after the merge, `Fixed in <repository>@<SHA>`.
- Severity is the reported severity, followed by `→ <assessed severity>: <reason>` when the assessment differs. For a WAF issue, write only the assessed severity and its reason. Leave the severity labels to sync. A closing comment leaves Severity out.
- Leave out Notes when there is nothing confidential to add.
- Put each item on its own line or bullet; never write a comment as one paragraph.

## Rules

| Situation | Do |
|---|---|
| Fix ready | Open a pull request; never push it to the default branch |
| Fix merged and its After merge steps done | Comment the merged commits and close as completed; sync reopens it if the finding returns |
| Finding left as it is, including WAF traffic that is expected | Comment the reason and close as not planned; sync never reopens it |
| Issue labeled `pending` | Leave the label to sync, which sets it after a completed scan or WAF report misses the finding; never add or remove it by hand |
| Issue body or hidden state marker | Never edit it; sync owns it and rewrites it |
| Public repository commit or pull request | Describe the change, never the finding or the issue |
| Owner rejects a fix after trying it | Revert, put the reason next to the setting, and close the issue as not planned with the reason |
| A blocked or destructive step, such as a history rewrite | Hand the owner the exact commands |
