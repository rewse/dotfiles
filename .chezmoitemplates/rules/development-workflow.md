# Development Workflow

Apply this workflow when a change is high-risk, crosses subsystem boundaries, or requires architectural decisions. Skip it for bounded changes that stay within one subsystem, affect about five or fewer files, have clear acceptance criteria, and can be verified with focused tests in one pass. File count is a heuristic; always use the full workflow for authentication, secrets, data migrations, public APIs, or infrastructure.

## 1. Research Before Implementing

Search for an existing implementation before writing new code, in this order:

1. `gh search repos "<query>" -L 10` and `gh search code "<query>" -L 10` for existing implementations and patterns
2. `ctx7 library <name> "<query>"` to resolve the library ID, then `ctx7 docs <libraryId> "<query>"` for API behavior and version-specific details
3. `tvly search "<query>" --json` only when the first two are insufficient

Prefer adopting or porting a proven approach over writing net-new code when it meets the requirement.

## 2. Clarify and Plan

Use **brainstorming** when the goal is understood but the solution needs collaborative design. Use **grilling** to stress-test a concrete plan, decision, or idea. Do not run overlapping discovery workflows by default; choose the one that matches the work.

After the requirements and design are settled, use the **planner** agent when implementation spans multiple files or phases. Plan directly when it can be done in a handful of tool calls. Write planning documents only when the user asks for them or the selected workflow explicitly requires durable artifacts.

## 3. Test First

Write a failing test before the implementation (RED), implement until it passes (GREEN), then refactor.

## 4. Review

Use the **code-reviewer** agent when the change spans multiple files or touches authentication, authorization, data handling, secrets, or infrastructure. Review smaller changes yourself as part of finishing them.

## 5. Before Requesting Review

Request review only after CI passes, conflicts are resolved, and the branch is up to date with its target.

## Subagent Delegation

Delegate only for large, independent, parallelizable work such as a wide multi-file investigation, and use one subagent where one suffices. Do not delegate what you can finish in a handful of tool calls, or use a subagent to verify your own work.
