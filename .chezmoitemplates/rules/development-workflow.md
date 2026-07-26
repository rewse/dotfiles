# Development Workflow

Apply this workflow when implementing a feature or making a non-trivial change to a code project. Skip it for single-file edits, configuration changes, and questions.

## 1. Research Before Implementing

Search for an existing implementation before writing new code, in this order:

1. `gh search repos "<query>" -L 10` and `gh search code "<query>" -L 10` for existing implementations and patterns
2. `ctx7 library <name> "<query>"` to resolve the library ID, then `ctx7 docs <libraryId> "<query>"` for API behavior and version-specific details
3. `tvly search "<query>" --json` only when the first two are insufficient

Prefer adopting or porting a proven approach over writing net-new code when it meets the requirement.

## 2. Plan

Use the **planner** agent when the change spans multiple files or phases. Plan it yourself when you can plan it in a handful of tool calls. Write planning docs to disk only when the user asks for them.

## 3. Test First

Write a failing test before the implementation (RED), implement until it passes (GREEN), then refactor.

## 4. Review

Use the **code-reviewer** agent when the change spans multiple files or touches authentication, authorization, data handling, secrets, or infrastructure. Review smaller changes yourself as part of finishing them.

## 5. Before Requesting Review

Request review only after CI passes, conflicts are resolved, and the branch is up to date with its target.

## Subagent Delegation

Delegate only for large, independent, parallelizable work such as a wide multi-file investigation, and use one subagent where one suffices. Do not delegate what you can finish in a handful of tool calls, or use a subagent to verify your own work.
