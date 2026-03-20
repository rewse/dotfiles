---
name: steering-creator
description: Create, improve, and review Kiro steering files based on prompt engineering best practices. Use when the user wants to create a new steering file, improve or optimize an existing one, review steering files for quality, audit their steering setup, or asks about steering file best practices. Also trigger when the user mentions "steering", "steering file", ".kiro/steering", "project rules", "coding standards file", "conventions file", or wants to establish persistent AI guidelines for their project.
---

# Steering Creator

A skill for creating, improving, and reviewing Kiro steering files. Steering files give Kiro persistent knowledge about a project through markdown files, so writing them well directly impacts AI output quality.

## Determining the mode

Figure out which mode the user needs based on their request:

- Create: The user wants a new steering file. Go to "Creating a steering file."
- Improve: The user has an existing file and wants it better. Go to "Improving a steering file."
- Review: The user wants feedback on existing files without changes. Go to "Reviewing steering files."

If the intent is ambiguous, ask.

## Creating a steering file

### Step 1: Understand the domain

Ask the user what behavior or conventions the steering file should capture. Good steering files are focused on a single domain, so help narrow the scope if the request is broad. Examples of well-scoped domains: API design conventions, testing patterns, commit message format, component structure.

If the user describes multiple unrelated concerns, suggest splitting into separate files.

### Step 2: Determine scope and inclusion

Ask two questions:

- Scope: Should this be global (`~/.kiro/steering/`) or workspace-specific (`.kiro/steering/`)?
  - Global: conventions that apply across all projects (personal coding style, language preferences)
  - Workspace: project-specific patterns (tech stack, architecture decisions)

- Inclusion mode: When should Kiro load this file? The available modes depend on whether you're using the IDE or CLI.
  - `always` (default): core standards loaded every time (IDE and CLI)
  - `fileMatch`: loaded only when working with matching files, e.g., `*.test.ts` (IDE and CLI)
  - `manual`: on-demand via `#steering-file-name` in chat (IDE only)
  - `auto`: loaded when the request matches a description, like a lightweight skill (IDE only)

See [references/best-practices.md](references/best-practices.md) for guidance on choosing inclusion modes.

### Step 3: Interview for content

Ask focused questions to extract the user's conventions. Prioritize:

- What rules are absolute vs. preferred? This determines the strength of language.
- Are there concrete examples of right and wrong? Do/Don't pairs are the most effective way to communicate expectations.
- Why does each rule exist? Rules with reasoning are followed more reliably than bare directives.

Don't try to capture everything at once. A focused file with 5 well-explained rules beats 20 vague ones.

### Step 4: Draft and review

Write the steering file following the best practices in [references/best-practices.md](references/best-practices.md). Then self-review against the checklist in that file before presenting to the user.

For examples of well-structured steering files across different domains, see [references/examples.md](references/examples.md).

### Step 5: Save

Save to the appropriate location based on the scope decided in Step 2. Use a descriptive filename like `api-conventions.md` or `testing-patterns.md`.

## Improving a steering file

### Step 1: Read and analyze

Read the target file and evaluate it against the best practices checklist in [references/best-practices.md](references/best-practices.md). Identify specific issues, not just general impressions.

### Step 2: Propose changes

Present findings organized by priority:

- High: Issues that likely cause the AI to misunderstand or ignore rules (ambiguity, contradictions, missing context)
- Medium: Structural improvements that would make rules clearer (adding examples, explaining reasoning, better organization)
- Low: Polish (terminology consistency, formatting)

For each issue, explain what the problem is and why it matters for AI behavior.

### Step 3: Apply with approval

Make changes only after the user approves. Show a before/after for significant rewrites.

## Reviewing steering files

### Step 1: Determine scope

Ask whether to review a single file, all workspace steering, or all steering (global + workspace).

### Step 2: Evaluate

For each file, assess against the checklist in [references/best-practices.md](references/best-practices.md). Read the checklist before starting the review.

### Step 3: Report

Present a summary for each file with:

- What it does well
- Specific issues found (with priority)
- Suggested improvements (concrete, not vague)

Don't rewrite files in review mode. The user may want to make changes themselves or switch to improve mode for specific files.

## Writing style for steering files

When drafting or improving steering files, follow the best practices in [references/best-practices.md](references/best-practices.md). The key principles: explain reasoning behind rules, use Do/Don't examples, and reserve MUST for truly critical rules.
