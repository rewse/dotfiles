# Best Practices for Steering Files

This document covers what makes steering files effective, drawing from prompt engineering research and Kiro-specific features. Use it as both a writing guide and a review checklist.

## Why steering files matter

Steering files are system-level prompts that persist across conversations. Unlike one-off chat instructions, they shape every interaction. A poorly written steering file can silently degrade AI output quality across hundreds of conversations, so getting them right has outsized impact.

## Content principles

### Explain the why, not just the what

Rules with reasoning are followed more reliably than bare directives. When the AI understands the intent behind a rule, it can apply the spirit of the rule in novel situations rather than just pattern-matching the letter.

Good:
```markdown
Use list or paragraph format to organize information. Tables render poorly in
terminal-based chat and are hard to scan when the content varies in length.
```

Weak:
```markdown
You MUST NOT use tables. You MUST use lists instead.
```

The first version gives the AI enough context to make good judgment calls (e.g., a small 2x3 table of fixed-width data might actually be fine). The second version is rigid and gives no basis for reasoning.

### Use Do/Don't examples

Concrete examples eliminate ambiguity more effectively than abstract descriptions. When a rule could be interpreted multiple ways, examples pin down the intended interpretation.

Good:
```markdown
## Commit messages

Follow Conventional Commits format.

### Do

- feat(auth): add OAuth2 login flow
- fix(api): handle null response from payment service

### Don't

- Added OAuth login
- fixed bug
```

### One domain per file

Each steering file should cover a single coherent topic. This makes files easier to maintain, review, and conditionally include. If a file covers both "API conventions" and "testing patterns," split it.

Signs a file should be split:
- It has more than 3-4 top-level sections covering unrelated topics
- Different sections would benefit from different inclusion modes
- Changes to one section don't logically relate to others

### Keep it focused

Every line in a steering file competes for the AI's attention. Remove content that doesn't directly influence behavior. Challenge each section: "If I removed this, would the AI's output actually get worse?"

Common bloat to cut:
- Explanations of concepts the AI already knows (what REST is, how Git works)
- Redundant restatements of the same rule in different words
- Aspirational guidelines that don't translate to concrete behavior

### Use consistent terminology

Pick one term for each concept and use it everywhere. Inconsistency forces the AI to guess whether "endpoint," "route," "path," and "URL" mean the same thing.

## Language and tone

### Choosing between natural language and RFC 2119 style

Both approaches work. Choose based on the density of rules:

- Few rules (under 10): Natural language reads better and conveys reasoning naturally
- Many rules (10+): RFC 2119 keywords (MUST, SHOULD, MAY) help the AI quickly parse priority levels

When using RFC 2119 style, maintain a clear hierarchy:
- MUST / MUST NOT: Non-negotiable rules. Violations are always wrong.
- SHOULD / SHOULD NOT: Strong recommendations. Exceptions exist but need justification.
- MAY: Acceptable options. The AI can choose based on context.

The most common mistake is making everything MUST. When every rule is critical, none of them are. Reserve MUST for rules where violations would cause real problems (security issues, breaking changes, data loss). Use SHOULD for style preferences and best practices.

### Prefer positive instructions

Tell the AI what to do, not just what to avoid. Negative-only rules leave the AI guessing about the correct alternative.

Good:
```markdown
Use `const` for variables that won't be reassigned. Use `let` only when
reassignment is necessary.
```

Weak:
```markdown
Don't use `var`.
```

## Structure and formatting

### Use Markdown headings for organization

Headings create scannable structure. The AI can quickly locate relevant sections rather than reading the entire file linearly.

Recommended structure:
```markdown
# Domain Title

Brief description of what this file covers and why.

## Topic 1

Rules and examples for topic 1.

### Do

- Good example

### Don't

- Bad example

## Topic 2

...
```

### Keep files concise

Every line competes for the AI's attention. Shorter files are more likely to be fully processed and followed. If a file grows large, consider whether it's covering too many domains or including unnecessary detail. There's no hard limit, but if you find yourself scrolling through a steering file, it's probably trying to do too much.

### Avoid time-sensitive content

Don't include dates, version-specific workarounds, or temporary instructions. Steering files tend to outlive the context that created them.

Bad:
```markdown
Until the v3 API launches in March, use the v2 endpoint.
```

Good:
```markdown
Use the v3 API endpoint: api.example.com/v3/resources
```

## Kiro-specific features

### Inclusion modes

Choose the right inclusion mode to balance relevance against context budget. Note that `manual` and `auto` modes are currently available in the IDE only; the CLI supports `always` and `fileMatch`.

- `always` (default): Use for core standards that apply to every interaction. Keep these files lean since they're always loaded. Examples: coding style, commit conventions, language preferences.

- `fileMatch`: Use for domain-specific rules tied to file types. This is the most efficient mode for specialized guidance since it only loads when relevant.
  ```yaml
  ---
  inclusion: fileMatch
  fileMatchPattern: "**/*.test.ts"
  ---
  ```

- `manual`: Use for reference material needed occasionally. The user triggers it with `#filename` in chat. Examples: migration guides, troubleshooting procedures, onboarding docs.

- `auto`: Use for context-heavy guidance that should load based on topic relevance. Requires `name` and `description` fields. Works like a lightweight skill.
  ```yaml
  ---
  inclusion: auto
  name: api-design
  description: REST API design patterns. Use when creating or modifying API endpoints.
  ---
  ```

Decision guide:
- "Does every conversation need this?" → `always`
- "Only relevant for certain file types?" → `fileMatch`
- "Only needed when the user explicitly asks?" → `manual`
- "Relevant based on the topic of conversation?" → `auto`

### Scope selection

- Global (`~/.kiro/steering/`): Personal conventions that apply across all projects. Examples: preferred language, chat tone, editor preferences.
- Workspace (`.kiro/steering/`): Project-specific standards. Examples: tech stack, architecture decisions, team conventions.

Workspace steering overrides global steering when they conflict, so you can set global defaults and override per-project.

### Foundational files

Kiro recognizes three foundational steering file patterns:

- `product.md`: Product purpose, target users, business context
- `tech.md`: Technology stack, frameworks, tools
- `structure.md`: File organization, naming conventions, architecture

These are optional but recommended for workspace steering. They give the AI broad project context that improves all interactions.

### File references (IDE only)

Link to live workspace files to keep steering current:
```markdown
#[[file:api/openapi.yaml]]
#[[file:components/ui/button.tsx]]
```

This is useful when the canonical source of truth lives in code rather than documentation.

## Review checklist

Use this checklist when reviewing or self-reviewing steering files:

### Content quality
- [ ] Each rule explains why it exists (or the reason is self-evident)
- [ ] Concrete Do/Don't examples for rules that could be misinterpreted
- [ ] No redundant or obvious content the AI already knows
- [ ] Consistent terminology throughout
- [ ] No time-sensitive or version-specific content
- [ ] No sensitive data (API keys, passwords, internal URLs)

### Structure
- [ ] Single coherent domain per file
- [ ] Clear Markdown heading hierarchy
- [ ] Concise (not covering too many domains or including unnecessary detail)
- [ ] Descriptive filename matching the content

### Language
- [ ] MUST/SHOULD/MAY hierarchy is intentional (not everything is MUST)
- [ ] Positive instructions preferred over negative-only rules
- [ ] Rules are specific enough to act on, not vague aspirations

### Kiro features
- [ ] Appropriate inclusion mode selected with correct frontmatter
- [ ] Scope (global vs. workspace) matches the content's applicability
- [ ] File references used where canonical source lives in code
