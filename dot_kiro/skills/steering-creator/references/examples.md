# Steering File Examples

Independent examples of well-structured steering files across different domains and inclusion modes. Use these as patterns when creating new steering files.

Note: Examples below are wrapped in fenced code blocks for separation. When nested code blocks appear (e.g., JSON or SQL inside a Markdown example), read the content structurally rather than relying on fence boundaries.

## Example 1: API conventions (always included)

A workspace steering file for a REST API project. Demonstrates focused scope, Do/Don't examples, and reasoning behind rules.

```markdown
# API Conventions

## Response format

All API responses use a consistent envelope structure. This makes client-side
parsing predictable and error handling uniform across endpoints.

### Success response

```json
{
  "data": { ... },
  "meta": { "page": 1, "total": 42 }
}
```

### Error response

```json
{
  "error": {
    "code": "VALIDATION_FAILED",
    "message": "Email format is invalid",
    "details": [...]
  }
}
```

## Naming

Use plural nouns for resource endpoints. Verbs belong in HTTP methods, not URLs.

### Do

- GET /users
- POST /users
- GET /users/{id}/orders

### Don't

- GET /getUsers
- POST /createUser
- GET /user/{id}/fetchOrders

## Status codes

Use the most specific applicable status code. Generic 200/400/500 responses
make debugging harder for API consumers.

- 201 for successful resource creation (not 200)
- 404 for missing resources (not 400)
- 409 for conflict on duplicate creation (not 400)
- 422 for validation errors (not 400)
```

## Example 2: Testing patterns (fileMatch)

A workspace steering file that loads only when working with test files. Demonstrates conditional inclusion and concise, actionable rules.

```markdown
---
inclusion: fileMatch
fileMatchPattern: ["**/*.test.*", "**/*.spec.*", "**/__tests__/**"]
---

# Testing Patterns

## Test structure

Each test file mirrors the source file it tests. Place test files adjacent to
source files, not in a separate test directory. Colocated tests are easier to
find and maintain.

## Naming

Test descriptions should read as behavior specifications, not implementation
details. A failing test name should tell you what broke without reading the
test body.

### Do

- "returns empty array when no items match the filter"
- "throws AuthError when token is expired"

### Don't

- "test getItems"
- "should work correctly"

## Mocking

Mock at the boundary (HTTP calls, database queries, file system), not internal
functions. Over-mocking makes tests pass even when the real integration is
broken.

Prefer dependency injection over module-level mocking when the architecture
supports it.

## Coverage

Aim for meaningful coverage, not a number. A single test that exercises the
critical path through a payment flow is worth more than 20 tests on getter
methods.
```

## Example 3: Documentation style (fileMatch for Markdown)

A global steering file for writing documentation. Demonstrates fileMatch on Markdown files and style guidance.

```markdown
---
inclusion: fileMatch
fileMatchPattern: "*.md"
---

# Documentation Style

## Headings

Use sentence case for headings. Title Case Creates Unnecessary Cognitive Load
when scanning a document.

### Do

- ## Getting started
- ## API reference

### Don't

- ## Getting Started
- ## API Reference

## Code blocks

Always specify the language for syntax highlighting. Unlabeled code blocks
render as plain text and are harder to read.

## Links

Use descriptive link text. The reader should understand the destination without
clicking.

### Do

- See the [authentication guide](./auth.md) for setup instructions.

### Don't

- For setup instructions, click [here](./auth.md).
```

## Example 4: Security policies (always included)

A workspace steering file for security-sensitive projects. Demonstrates appropriate use of MUST for genuinely critical rules.

```markdown
# Security Policies

## Input validation

All user input MUST be validated before processing. This applies to API
request bodies, query parameters, headers, and file uploads. Unvalidated
input is the root cause of most injection vulnerabilities.

Use schema validation libraries (e.g., zod, joi) rather than manual checks.
Schema validation is declarative, composable, and harder to get wrong.

## Database queries

MUST use parameterized queries for all database operations. String
concatenation in queries creates SQL injection vulnerabilities regardless of
input validation.

### Do

```sql
SELECT * FROM users WHERE id = $1
```

### Don't

```sql
SELECT * FROM users WHERE id = '${userId}'
```

## Secrets

MUST NOT hardcode secrets, API keys, or credentials in source code. Use
environment variables or a secrets manager.

SHOULD use short-lived tokens over long-lived API keys when the service
supports it. Short-lived tokens limit the blast radius of a leak.
```

## Example 5: Auto-inclusion for specialized guidance

A steering file that loads based on topic relevance. Demonstrates the auto inclusion mode with name and description.

```markdown
---
inclusion: auto
name: database-migrations
description: Database migration patterns and safety procedures. Use when creating, modifying, or reviewing database migrations, schema changes, or data transformations.
---

# Database Migration Guide

## Safety rules

Every migration MUST be reversible. Write both `up` and `down` methods. A
migration that can't be rolled back is a deployment risk.

MUST NOT drop columns or tables in the same release that removes the code
using them. Use a two-phase approach:

1. Deploy code that stops reading/writing the column
2. Deploy migration that drops the column

## Naming

Use timestamps, not sequential numbers. Sequential numbers cause merge
conflicts when multiple developers create migrations simultaneously.

### Do

- 20250115143022_add_users_email_index.sql

### Don't

- 003_add_index.sql

## Large tables

For tables over 1M rows, SHOULD use online schema change tools (e.g.,
gh-ost, pt-online-schema-change) instead of direct ALTER TABLE. Direct
ALTER locks the table for the duration of the change.
```

## Example 6: Manual inclusion for reference material

A steering file loaded on-demand for occasional use. Demonstrates the manual inclusion mode.

```markdown
---
inclusion: manual
---

# Troubleshooting Guide

Reference for common issues. Include this file with #troubleshooting-guide
when debugging.

## Build failures

### "Module not found" after dependency update

Clear the dependency cache and reinstall:

```bash
rm -rf node_modules package-lock.json
npm install
```

If the error persists, check for peer dependency conflicts:

```bash
npm ls <package-name>
```

### TypeScript compilation errors after upgrade

Check for breaking changes in the release notes. Common causes:

- Stricter null checks in new TS versions
- Deprecated APIs removed
- Changed module resolution behavior

## Runtime errors

### Memory leaks in development server

The dev server accumulates memory over long sessions. Restart it if memory
usage exceeds 2GB. This is a known issue with the HMR implementation and
does not affect production builds.
```
