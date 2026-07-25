# Development Workflow

Apply this workflow when implementing a feature or making a non-trivial change to a code project. Skip it for single-file edits, configuration changes, and questions.

## 1. Research Before Implementing

Search for an existing implementation before writing new code, in this order:

1. `gh search repos` and `gh search code` for existing implementations and patterns
2. `ctx7 library <name> "<query>"` to resolve the library ID, then `ctx7 docs <libraryId> "<query>"` for API behavior and version-specific details
3. `tvly search "<query>" --json` only when the first two are insufficient

Prefer adopting or porting a proven approach over writing net-new code when it meets the requirement.

## 2. Plan

Use the **planner** agent to create the implementation plan. Write planning docs to disk only when the user asks for them.

## 3. Test First

Write a failing test before the implementation (RED), implement until it passes (GREEN), then refactor.

## 4. Review

Use the **code-reviewer** agent immediately after writing code.

## 5. Before Requesting Review

Request review only after CI passes, conflicts are resolved, and the branch is up to date with its target.
