---
name: github-push-via-fox
description: Push commits to GitHub from this host by relaying them through fox. Use this skill whenever a push to github.com fails or hangs, when git reports GH007 or rejects the author email, or before pushing any repository whose origin is on GitHub from this host. Covers both uncommitted working-tree changes and commits already made locally. Does not apply to other remotes such as internal GitLab, which push directly.
---

# Push to GitHub via fox

This host cannot reach `github.com` for pushes. Relay the work to `fox` and push from there. Other remotes are unaffected and push directly from here.

Pick the transfer method by whether the work is committed yet.

## Uncommitted working-tree changes

The result collapses into a single commit on `fox`.

1. Generate a patch here: `git -P diff -- <files> > /tmp/changes.patch`
2. Copy it over: `scp /tmp/changes.patch fox:/tmp/changes.patch`
3. On `fox`, update the repo and apply: `cd <repo path on fox> && git pull --ff-only && git apply --check /tmp/changes.patch && git apply /tmp/changes.patch`
4. Commit and push: `git commit -m "..." && git push origin HEAD`

## Local commits already made

Commit history is preserved.

1. Export the unpushed commits: `git format-patch origin/main..HEAD -o /tmp`
2. Copy them over: `scp /tmp/000*.patch fox:/tmp/`
3. On `fox`, update the repo and apply in order: `cd <repo path on fox> && git pull --ff-only && git am /tmp/000*.patch`
4. Push: `git push origin HEAD`

## After pushing

Sync this host with `git pull`, or `chezmoi update` for the chezmoi repo.

If the local commits and the pushed commits differ, run `git reset --hard origin/main` to adopt the remote versions. Do not ask for confirmation on this step; it is pre-approved. Confirm the trees match first with `git diff HEAD origin/main`, where empty output means the working tree is identical and nothing is lost.

## Author rejected

If GitHub rejects the push with GH007, do not hand-write `--author`. The noreply address is not taking effect: check that `git config --show-origin --get user.email` resolves to `github.inc`, and that no `~/.gitconfig` is overriding it.
