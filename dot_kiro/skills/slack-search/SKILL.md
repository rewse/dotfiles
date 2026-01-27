---
name: slack-search
description: Guide for searching in Slack using search modifiers and filters. Use when the user wants to find messages, files, or information in Slack, or asks about Slack search syntax, search modifiers (from:, in:, has:, before:, after:, etc.), or how to filter search results.
---

# Slack Search

Reference for Slack search features and modifiers.

## Search Modifiers List

| Modifier | Description | Example |
|---|---|---|
| `"phrase"` | Search for a specific phrase | `"marketing report"` |
| `-word` | Exclude a specific word | `marketing -report` |
| `in:` | Search within a specific channel/DM | `in:#team-marketing` |
| `from:` | Search for messages from a specific member | `from:@username` |
| `has:` | Messages with a specific emoji reaction | `has::eyes:` |
| `hasmy:` | Messages you reacted to | `hasmy::thumbsup:` |
| `is:saved` | Items added to bookmarks | `is:saved` |
| `has:pin` | Pinned items | `has:pin` |
| `before:` | Before a specified date | `before:2024-01-01` |
| `after:` | After a specified date | `after:2024-01-01` |
| `on:` | On a specified date | `on:2024-01-15` |
| `during:` | During a specified month/year | `during:January` or `during:2024` |
| `is:thread` | Search within threads | `is:thread` |
| `with:` | Search within threads/DMs with a specific member | `with:@username` |
| `creator:` | Search for canvases created by a specific user | `creator:@username` |
| `-in:` | Exclude a specific channel | `-in:#random` |
| `-from:` | Exclude a specific member | `-from:@bot` |
| `word*` | Wildcard - See results that begin with a partial word. Add an asterisk to a partial word with at least three characters to see results that begin with those specific letters. | `rep*` → reply, report |

## Combination Examples

```
# Search for messages from a specific member in a channel
marketing report in:#team-marketing from:@tanaka

# Search for threads within a specific time period
project is:thread after:2024-01-01 before:2024-03-01

# Bookmarked items you reacted to
is:saved hasmy::star:

# Search excluding specific channels
API specification -in:#general -in:#random
```

## References

- [Search in Slack - Slack Help Center](https://slack.com/help/articles/202528808-Search-in-Slack)
