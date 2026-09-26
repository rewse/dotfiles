# Repository Location

Before starting a git-related task, check whether the target repository is already cloned under `/Users/shibtats/git`. Reuse the existing clone when it is present. When it is not, clone it into `/Users/shibtats/git` and work there. Do not clone into any other directory.

# Updating Before Working

Run `git pull` in the target repository before making any change, and check out the default branch first when the clone is on a stale feature branch. The remote often carries commits that are not in the local clone, and building on an outdated base means the work has to be rebased or reapplied later.

# GitHub Configuration

Keep `.github` consistent across the `rewse/*` repositories cloned here. A repository may differ only for a reason stated in this section or in its own AGENTS.md. Repositories hosted on GitLab and forks of upstream projects are out of scope.

- Give every repository a `.github/dependabot.yml` that covers `github-actions` and each package ecosystem it uses (`docker`, `npm`, `pre-commit`, `uv`). Each entry runs weekly, groups all updates of the ecosystem into one pull request, and sets `cooldown.default-days: 4` to match the 96-hour minimum package age.
- Pin every `uses:`, including reusable workflows, to a full commit SHA followed by `# vX.Y.Z`. Do not reference tags or branches, because a tag can be moved to malicious code; Dependabot keeps the pins current.
- Set top-level `permissions` to `contents: read` and grant anything more on the job that needs it.
- Set `persist-credentials: false` on `actions/checkout`, give every job a `name`, use Node.js 24 unless a dependency's `engines` rules it out, and read the Python version from `.python-version`.
- Run `gitleaks.yml` on push, pull request, and a weekly schedule, and `trufflehog.yml` as a weekly sweep, in every repository. Add `--exclude-detectors=<detector>` only in a repository where that detector reported a false positive.
- Add `dependency-scan.yml` to every repository with a lockfile: install dependencies through Aikido Safe Chain and call the OSV-Scanner reusable workflow. Pass `upload-sarif: false` in a private repository, since Code Scanning there requires GitHub Code Security.
- Give each repository's scheduled workflows their own cron minutes so they do not run at the same time.
- Name a workflow file after the tool it runs or the job it does (`gitleaks.yml`, `dependency-scan.yml`, `release.yml`), use the `.yml` extension, and never rename `release.yml`, because PyPI and npm Trusted Publishing are bound to that file name.
- Keep tool configuration at the path the tool reads by default (for example, `cliff.toml` at the repository root) so it works locally without extra flags.
