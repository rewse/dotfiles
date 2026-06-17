---
description: Create a Microsoft To-Do (Outlook ToDo) task from a TickTick quick-add one-liner.
argument-hint: "<task in TickTick quick-add syntax, e.g. Review Q3 report ^Work #finance !high tomorrow 5pm>"
---

# outlook-todo

Parse a TickTick quick-add one-liner from `$ARGUMENTS` and create a Microsoft To-Do task via the `aws-outlook-mcp` MCP server (called through `mcporter`).

If `$ARGUMENTS` is empty, ask the user for the one-liner and stop.

## Parse the TickTick quick-add syntax

Extract these tokens from `$ARGUMENTS`. Each token may appear anywhere in the line; remove matched tokens from the text, and the remaining words become the task title.

- `^list` — target list. Resolve to a Microsoft To-Do `listId` (see below).
- `!priority` — `!high`, `!medium`, `!low`, or `!none`. Map to To-Do `importance`:
  - `!high` → `high`
  - `!medium` → `normal`
  - `!low` → `low`
  - `!none` or no priority token → `normal`
- Date / time — natural language (`tomorrow 5pm`, `明日17時`, `next mon`) or a `*YYYY-MM-DD` token. Interpret relative to the current date. Resolve an ambiguous date to the nearest valid future date/time (TickTick behavior).
- `#tag` — Microsoft To-Do has no tags. Append each tag to the task `body`.
- `@user` — Microsoft To-Do personal lists have no assignment. Append to `body`.

### Title

Set `title` to the leftover text after removing all tokens above. Rewrite it in English using the imperative mood (e.g. "Review Q3 report"), translating from Japanese if needed. Limit the title to 10 words maximum; if the full meaning requires more, keep the title as a concise summary and move the additional detail into `body`.

### Person names → alias hashtag

When a person's name appears in `$ARGUMENTS`, resolve their Amazon alias via Phonetool:

```bash
mcporter call builder-mcp.InternalSearch query="<person name>" domain=PHONETOOL 2>&1 | cat
```

The result returns a JSON object with `uid` (the alias), `title`, and `departmentName`. Extract the `uid` value (lowercased) and append `#<alias>` to the end of the title (e.g. "Discuss roadmap with Gowri" → title becomes `Discuss roadmap with Gowri #gowrishb`). If multiple people are mentioned, append one hashtag per person. If the lookup fails or returns no match, skip the hashtag for that person.

### Date / time → due and reminder

Interpret times in the local timezone and always include the offset in the ISO string (e.g. `2026-06-15T17:00:00+09:00` for JST). Without an offset the server treats the value as UTC and the time shifts.

- With a time component: set `reminderDateTime` to the resolved ISO datetime with offset and `isReminderOn=true`. Also set `dueDateTime` to the same value, but note that To-Do keeps only the date part of `dueDateTime` (the time is dropped); the time of day lives in `reminderDateTime`.
- Date only (no time): set `dueDateTime` to the date at noon local time with offset (e.g. `2026-06-18T12:00:00+09:00`) and do NOT set a reminder. Use noon, NOT midnight: a midnight value like `2026-06-18T00:00:00+09:00` converts to the previous day in UTC, so the server stores the wrong date. Noon keeps the date stable across timezone conversion.

### Body

Build `body` from the `#tag` and `@user` tokens that have no To-Do equivalent, e.g. `Tags: finance | Assignee: @gowri`. Leave `body` unset if there are none.

## Resolve the list

1. If there is no `^list` token, leave `listId` unset so the task lands in the default list. Skip to creation.
2. Otherwise run:

   ```bash
   mcporter call aws-outlook-mcp.todo_lists operation=list 2>&1 | cat
   ```

   Match the `^list` name (case-insensitive) against the returned list display names and use that `listId`.
3. If no list matches, fall back to the default tasks list and warn the user that `^<name>` did not match an existing list.

## Create the task

Run, including only the parameters that were resolved:

```bash
mcporter call aws-outlook-mcp.todo_tasks operation=create \
  listId=<resolved listId> \
  title=<title> \
  body=<body> \
  importance=<high|normal|low> \
  dueDateTime=<ISO datetime> \
  reminderDateTime=<ISO datetime> \
  isReminderOn=<true|false> 2>&1 | cat
```

Notes:

- `listId` is required by `todo_tasks` when targeting a specific list. When no `^list` was given, omit `listId` only if the tool allows it; otherwise resolve the default list via `todo_lists` first and use its id.
- Omit `dueDateTime`, `reminderDateTime`, and `isReminderOn` entirely when no date was parsed.

## Report

Report the result in one line: title, list, due date/time, priority, and any tag/assignee values moved into the body. If `mcporter` or `aws-outlook-mcp` is unavailable, say so and stop.
