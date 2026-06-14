# Committing and Pushing via fox

The host `7cf34ded5d65` cannot push to GitHub (`github.com`). Other remotes (e.g. internal GitLab) are unaffected. When a repository's `origin` is on GitHub, commit and push from `fox` instead. This applies to every such repository (chezmoi, ansible-playbooks, etc.), not just one.

GitHub rejects pushes whose author is a private email with `GH007`, so commits pushed from `fox` must use the noreply author `Shibata, Tats <868951+rewse@users.noreply.github.com>`.

Choose the transfer method by whether you have committed locally yet:

## Uncommitted working-tree changes (collapses into one commit)

1. On `7cf34ded5d65`, generate a patch: `git -P diff -- <files> > /tmp/changes.patch`
2. Copy it to `fox`: `scp /tmp/changes.patch fox:/tmp/changes.patch`
3. On `fox`, bring the repo up to date and apply: `cd <repo path on fox> && git pull --ff-only && git apply --check /tmp/changes.patch && git apply /tmp/changes.patch`
4. Commit with the noreply author, then push: `git commit --author="Shibata, Tats <868951+rewse@users.noreply.github.com>" -m "..." && git push origin HEAD`

## Local commits already made (preserves commit history)

1. On `7cf34ded5d65`, export each unpushed commit as a patch: `git format-patch origin/main..HEAD -o /tmp`
2. Copy them to `fox`: `scp /tmp/000*.patch fox:/tmp/`
3. On `fox`, bring the repo up to date and apply in order: `cd <repo path on fox> && git pull --ff-only && git am /tmp/000*.patch`
4. Rewrite every applied commit to the noreply author: `git rebase --exec 'git commit --amend --no-edit --author="Shibata, Tats <868951+rewse@users.noreply.github.com>"' origin/main`
5. Push: `git push origin HEAD`

## After pushing (either method)

Sync `7cf34ded5d65` with `git pull` (or `chezmoi update` for the chezmoi repo). When local commits carry a different author than the pushed ones, `git reset --hard origin/main` to adopt them — verify the trees match first with `git diff HEAD origin/main` (empty output means identical).
