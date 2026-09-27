# Repository Location

Before starting a git-related task, check whether the target repository is already cloned under `~/git`. Reuse the existing clone when it is present. When it is not, clone it into `~/git` and work there. Do not clone into any other directory.

# Updating Before Working

Run `git pull` in the target repository before making any change, and check out the default branch first when the clone is on a stale feature branch. The remote often carries commits that are not in the local clone, and building on an outdated base means the work has to be rebased or reapplied later.

# GitHub Configuration

Keep `.github` consistent across the `rewse/*` repositories cloned here. A repository may differ only for a reason stated in this section or in its own AGENTS.md. Repositories hosted on GitLab and forks of upstream projects are out of scope.

- Give every repository a `.github/dependabot.yml` that covers `github-actions` and each package ecosystem it uses (`docker`, `npm`, `pre-commit`, `uv`). Each entry runs weekly, groups all updates of the ecosystem into one pull request, and sets `cooldown.default-days: 5`, because Dependabot counts whole days and 4 can admit a release about 80 hours after publication, short of the 96-hour minimum package age. Exempt `rewse/*` from the cooldown in the `github-actions` entry, since those are our own actions. zizmor asks for at least 7 days, so end each `default-days: 5` line with `# zizmor: ignore[dependabot-cooldown]` and the reason instead of raising the value.
- Pin every `uses:`, including reusable workflows, to a full commit SHA followed by `# vX.Y.Z`. Do not reference tags or branches, because a tag can be moved to malicious code; Dependabot keeps the pins current.
- Set top-level `permissions` to `contents: read` and grant anything more on the job that needs it.
- Set `persist-credentials: false` on `actions/checkout`, give every job a `name`, use Node.js 24 unless a dependency's `engines` rules it out, and read the Python version from `.python-version`.
- Run `gitleaks.yml` on push, pull request, and a weekly schedule, and `trufflehog.yml` as a weekly sweep, in every repository. Exclude a detector (`--exclude-detectors`) or a path (`--exclude-paths`) only in a repository where it reported a false positive, and state the reason in a comment. When Dependabot bumps `trufflesecurity/trufflehog`, update the `version:` image tag and digest in the same pull request, since Dependabot leaves them at the old release.
- Add `dependency-scan.yml` to every repository with a lockfile: install dependencies through Aikido Safe Chain and call the OSV-Scanner reusable workflow. Pass `upload-sarif: false` in a private repository, since Code Scanning there requires GitHub Code Security.
- Give every repository a `.pre-commit-config.yaml` with the hooks for the languages it contains: actionlint, check-jsonschema, and zizmor everywhere, plus basedpyright and ruff for Python, shellcheck for shell scripts, and ansible-lint for Ansible, which match what Zed runs. Pin each `rev:` to a full commit SHA followed by `# frozen: vX.Y.Z`, set basedpyright's `typeCheckingMode = "standard"` in `pyproject.toml` or `pyrightconfig.json`, set ruff's `lint.isort` to `force-single-line = true` with `single-line-exclusions = ["collections.abc", "typing"]` to keep Google style's one import per line, and run `uvx --with pre-commit-uv==4.3.0 pre-commit@4.6.2 run --all-files` before committing.
- Run the same command in `lint.yml` after `rewse/actions/setup-safe-chain`, so the hook environments are installed through Safe Chain, and run tests in `test.yml` rather than in `dependency-scan.yml`.
- Fix lint and type findings instead of suppressing them. Suppress one only where the rule conflicts with a deliberate design or the cause lies outside the repository, and state the reason on the same line.
- Install Aikido Safe Chain with `rewse/actions/setup-safe-chain`, which takes the newest immutable release at least 96 hours old and verifies its checksum; do not pipe an installer from a branch into `sh`.
- Give each repository's scheduled workflows their own cron minutes so they do not run at the same time.
- Name a workflow file after the tool it runs or the job it does (`gitleaks.yml`, `dependency-scan.yml`, `release.yml`), use the `.yml` extension, and never rename `release.yml`, because PyPI and npm Trusted Publishing are bound to that file name.
- Keep tool configuration at the path the tool reads by default (for example, `cliff.toml` at the repository root) so it works locally without extra flags.
