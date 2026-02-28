# Project Dependency Update Prompt

Update the following projects in `~/Documents/git` according to the procedure:

- enecoq-data-fetcher
- stock-price-fetcher
- textlint-config-rewse
- textlint-rule-ja-space-around-phrase
- zenn-content

## 1. git pull

1. Run `git pull --rebase`

## 2. Update OSV-Scanner

1. Check the latest version number from https://github.com/google/osv-scanner-action/releases
2. If `.github/security-scan.yml` exists in the project, update the OSV-Scanner version to the latest

## 3. Determine if uv project or npm project

1. If it's a uv project, proceed to step 4
2. If it's an npm project, proceed to step 5

## 4. uv Project

1. Run `uv lock --upgrade --dry-run` to display packages to be updated
2. Run `uv lock --upgrade` to update dependencies
3. Review the updates
4. Read `.kiro/steering/tech.md` in the project and run tests if available
5. Commit the changes

## 5. npm Project

1. Run `npm outdated` to display packages to be updated
2. Run `npm update` to update dependencies
3. Run `npm outdated` again to verify the updates
4. Read `.kiro/steering/tech.md` in the project and run tests if available
5. Commit the changes

## 6. git push

Execute this step after completing step 3 or 4 for all projects:

1. Run `git push` in all projects to push the changes
2. Wait 1 minute
3. Run `gh run list` in all projects to verify GitHub Actions succeeded

## Notes

- You MUST handle breaking changes appropriately
- You MUST follow Conventional Commits (e.g., `chore: update dependencies`)
- If tests fail, you MUST explain the error and ask whether it's acceptable to ignore the error
