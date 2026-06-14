# Committing and Pushing via fox

The host `7cf34ded5d65` cannot push to GitHub (`github.com`). Other remotes (e.g. internal GitLab) are unaffected. When a repository's `origin` is on GitHub, commit and push from `fox` instead. This applies to every such repository (chezmoi, ansible-playbooks, etc.), not just one.

1. On `7cf34ded5d65`, generate a patch of the working-tree changes: `git -P diff -- <files> > /tmp/changes.patch`
2. Copy it to `fox`: `scp /tmp/changes.patch fox:/tmp/changes.patch`
3. On `fox`, bring the repo up to date and apply: `cd <repo path on fox> && git pull --ff-only && git apply --check /tmp/changes.patch && git apply /tmp/changes.patch`
4. Commit on `fox` with the GitHub noreply author, then `git push origin HEAD`: `git commit --author="Shibata, Tats <868951+rewse@users.noreply.github.com>" -m "..."`. GitHub rejects pushes whose author is a private email with `GH007`, so the author must be the noreply address.
5. Sync `7cf34ded5d65` afterward with `git pull` (or `chezmoi update` for the chezmoi repo). When local commits made before pushing carry a different author, `git reset --hard origin/main` to adopt the pushed commits (verify trees match first with `git diff <local> origin/main`).
