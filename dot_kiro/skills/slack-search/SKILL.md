---
name: slack-search
description: Guide for searching in Slack using search modifiers and filters. Use when the user wants to find messages, files, or information in Slack, or asks about Slack search syntax, search modifiers (from:, in:, has:, before:, after:, etc.), or how to filter search results. Also trigger when the user mentions "can't find a message", "looking for something in Slack", "search Slack history", "find old conversations", "filter Slack messages", "search in a channel", or needs help with advanced Slack search queries.
---

# Slack Search

Reference for Slack search features and modifiers.

## Important: GUI vs API Syntax Differences

When using Slack search through different interfaces, the syntax differs. Understanding these differences is critical because API-based searches (like through MCP tools) will fail or return unexpected results if you use GUI syntax. The main differences are in how channels and users are referenced.

### Channel References (`in:`)

**GUI (Slack app):**
- Channels (public/private): `in:#team-marketing` (with `#` prefix)
- DMs: `in:@username`

**API/MCP:**
- Channels (public/private): `in:team-marketing` or `in:channel_id` (without `#` prefix)
- DMs: `in:<@UserID>` (User ID wrapped in `<@>`)

### User References (`from:`, `with:`)

- **GUI (Slack app)**: Use `from:@username` or `from:@display_name`
- **API/MCP**: Usually `from:@username` works, but if it doesn't, use `from:<@UserID>` (User ID wrapped in `<@>`)

### How to Get Channel ID

**Via GUI (Slack app):**
1. Select the channel from the left-hand menu
2. Click "More" (three dots `...`)
3. Click "Open channel details"
4. The channel ID is at the bottom
5. Click "Copy channel ID"

**Via API:**
Use the `conversations.list` API method to retrieve all channels in the workspace, then search for the Channel ID by channel name.

### How to Get User ID

**Via GUI (Slack app):**
1. Click on the member's profile icon
2. Click "More" (three dots `...`)
3. Click "Copy member ID"

**Via API:**
Use the `users.list` API method to retrieve all users in the workspace, then search for the User ID by display name or username.

## Search Modifiers List

| Modifier | Description | Example |
|---|---|---|
| `"phrase"` | Search for a specific phrase | `"marketing report"` |
| `-word` | Exclude a specific word | `marketing -report` |
| `in:` | Search within a specific channel/DM | GUI: `in:#team-marketing` / API: `in:team-marketing` |
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
| `-in:` | Exclude a specific channel | GUI: `-in:#random` / API: `-in:random` |
| `-from:` | Exclude a specific member | `-from:@bot` |
| `word*` | Wildcard search - matches words starting with the prefix (minimum 3 characters) | `rep*` matches reply, report |

## Combination Examples

These examples show how to combine multiple modifiers to narrow down search results effectively. Use combinations when a single modifier returns too many results or when you need to search within a specific context.

### GUI Examples
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

### API/MCP Examples
```
# Search for messages from a specific member in a channel
marketing report in:team-marketing from:@tanaka

# Search for threads within a specific time period
project is:thread after:2024-01-01 before:2024-03-01

# Bookmarked items you reacted to
is:saved hasmy::star:

# Search excluding specific channels
API specification -in:general -in:random
```

## Common Search Scenarios

Use these patterns for frequently encountered search tasks:

**Find project discussions in a specific timeframe:**
```
project-name in:#channel-name after:2024-01-01 before:2024-03-31
```

**Find messages you bookmarked:**
```
is:saved keyword
```

**Find unread messages from a specific person:**
```
from:@username is:unread
```

**Find threads you participated in:**
```
is:thread with:@your-username keyword
```

**Find messages with attachments from last month:**
```
has:link during:January
```

## References

- [Search in Slack - Slack Help Center](https://slack.com/help/articles/202528808-Search-in-Slack)
- [search.messages method - Slack API](https://api.slack.com/methods/search.messages)
