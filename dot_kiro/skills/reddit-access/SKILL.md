---
name: reddit-access
description: Access Reddit content via old.reddit.com JSON endpoints without authentication. Use when you need to fetch Reddit posts, search subreddits, get post details with comments, or retrieve user posts. Triggers include "get Reddit posts", "search Reddit", "fetch from r/", "Reddit comments", "user posts on Reddit", when the user provides a Reddit URL starting with "https://www.reddit.com/r/" or "https://old.reddit.com/r/", or any task involving reading public Reddit content.
---

# reddit-access

Access Reddit content via `old.reddit.com` JSON endpoints.

## Prerequisites

Python 3 with standard library (no external dependencies).

## Commands

### Get subreddit posts

```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py posts <subreddit> [limit] [sort]
```

- `subreddit`: Subreddit name (without r/)
- `limit`: Number of posts (default: 25, max: 100)
- `sort`: Sort order - `hot`, `new`, `top`, `rising` (default: hot)

**Example:**
```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py posts python 10 hot
```

**Output:**
```json
[
  {
    "id": "abc123",
    "title": "Post title",
    "author": "username",
    "score": 42,
    "num_comments": 15,
    "url": "https://old.reddit.com/r/python/comments/abc123/...",
    "created_utc": 1234567890
  }
]
```

### Get post details with comments

```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py details <post_id_or_url> [subreddit]
```

- `post_id_or_url`: Reddit post ID or full URL (new or old Reddit)
- `subreddit`: Optional subreddit name for faster lookup (ignored if URL provided)

**Example with post ID:**
```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py details abc123 python
```

**Example with new Reddit URL:**
```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py details "https://www.reddit.com/r/python/comments/abc123/post_title/"
```

**Output:**
```json
{
  "post": {
    "title": "Post title",
    "selftext": "Post content...",
    "author": "username",
    "score": 42
  },
  "comments": [
    {
      "author": "commenter",
      "body": "Comment text",
      "score": 10
    }
  ]
}
```

### Search within subreddit

```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py search <subreddit> <query> [limit]
```

- `subreddit`: Subreddit to search in
- `query`: Search query
- `limit`: Number of results (default: 25)

**Example:**
```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py search python "async await" 10
```

### Get user posts

```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py user <username> [limit]
```

- `username`: Reddit username (without u/)
- `limit`: Number of posts (default: 25)

**Example:**
```bash
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py user rewselab 10
```

## Common Workflows

### Read a Reddit post from URL

```bash
# Simply pass the Reddit URL (new or old Reddit)
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py details "https://www.reddit.com/r/python/comments/abc123/post_title/"
```

### Read discussion

```bash
# Get post and read comments
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py details abc123 python
```

### Monitor trending topics

```bash
# Get hot posts from multiple subreddits
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py posts programming 15 hot
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py posts python 15 hot
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py posts MachineLearning 15 hot
```

### Research a topic

```bash
# Search across relevant subreddits
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py search python "type hints" 20
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py search learnpython "type hints" 20
```

### Track user activity

```bash
# Get recent posts from a user
python3 ~/.kiro/skills/reddit-access/scripts/reddit.py user username 25
```

## Notes

- Uses `old.reddit.com` JSON endpoints (public, no auth required)
- Rate limiting: Be respectful, avoid rapid requests
- User-Agent is set automatically to avoid 403 errors
- All output is JSON format
- Standard library only (no pip dependencies)
- Works with public content only (no private subreddits or user data)

## Error Handling

Errors are returned as JSON to stderr:
```json
{
  "error": "Error message"
}
```

Common errors:
- Subreddit not found (404)
- Post not found (404)
- Rate limited (429) - wait and retry
- Network timeout - retry with exponential backoff
