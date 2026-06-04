## Commit message

Generate commit messages following Conventional Commits 1.0.0 format:

  <type>[optional scope]: <description>

  [optional body]

  Types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert

  Rules:
  - Output only the raw commit message text. Do not wrap it in markdown code blocks or backticks
  - Subject line must start with a type prefix
  - Use imperative mood in the description
  - Do not capitalize the first letter of the description
  - Do not end the subject line with a period
  - Keep the subject line under 72 characters
  - Use a bulleted list in the body to describe individual changes. Each bullet starts with "- " and a capitalized verb in imperative mood.
  - Do not wrap or break lines. Write each bullet as a single continuous line.

  Type selection guidance:

  File deletion — choose type based on intent:
  - refactor: deletion as part of a structural change (merging, splitting, or relocating files)
  - fix: deletion to correct a bug or mistake (removing an erroneously added file or a file causing issues)
  - chore: deletion for general maintenance (removing obsolete or unused files)

  Dependency updates — choose type based on intent:
  - fix: updating to address a vulnerability or bug in a dependency
  - chore: routine version bumps or general maintenance updates
