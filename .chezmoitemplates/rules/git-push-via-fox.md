# Committing and Pushing via fox

The host `7cf34ded5d65` cannot push to `origin`. When working on it, commit and push from `fox` instead. This applies to every git repository (chezmoi, ansible-playbooks, etc.), not just one.

1. On `7cf34ded5d65`, generate a patch of the working-tree changes: `git -P diff -- <files> > /tmp/changes.patch`
2. Copy it to `fox`: `scp /tmp/changes.patch fox:/tmp/changes.patch`
3. On `fox`, bring the repo up to date and apply: `cd <repo path on fox> && git pull --ff-only && git apply --check /tmp/changes.patch && git apply /tmp/changes.patch`
4. Commit on `fox`, then `git push origin HEAD`
5. Sync `7cf34ded5d65` afterward with `git pull` (or `chezmoi update` for the chezmoi repo)
