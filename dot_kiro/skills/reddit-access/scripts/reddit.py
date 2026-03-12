#!/usr/bin/env python3
"""Reddit JSON API access via old.reddit.com (no auth required)"""

import json
import sys
import urllib.request
import urllib.parse
import re

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

def parse_reddit_url(url):
    """Extract subreddit and post_id from Reddit URL"""
    pattern = r'reddit\.com/r/([^/]+)/comments/([^/]+)'
    match = re.search(pattern, url)
    if match:
        return match.group(1), match.group(2)
    return None, None

def fetch_json(url):
    """Fetch JSON from old.reddit.com"""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

def subreddit_posts(subreddit, limit=25, sort="hot"):
    """Get posts from a subreddit"""
    url = f"https://old.reddit.com/r/{subreddit}/{sort}.json?limit={limit}"
    data = fetch_json(url)
    posts = []
    for p in data["data"]["children"]:
        d = p["data"]
        posts.append({
            "id": d["id"],
            "title": d["title"],
            "author": d["author"],
            "score": d["score"],
            "num_comments": d["num_comments"],
            "url": f"https://old.reddit.com{d['permalink']}",
            "created_utc": d["created_utc"]
        })
    return posts

def post_details(post_id_or_url, subreddit=None):
    """Get post details and comments"""
    # Check if it's a URL
    if post_id_or_url.startswith('http'):
        subreddit, post_id = parse_reddit_url(post_id_or_url)
        if not post_id:
            raise ValueError("Invalid Reddit URL")
    else:
        post_id = post_id_or_url
    
    if subreddit:
        url = f"https://old.reddit.com/r/{subreddit}/comments/{post_id}.json"
    else:
        url = f"https://old.reddit.com/comments/{post_id}.json"
    data = fetch_json(url)
    post = data[0]["data"]["children"][0]["data"]
    comments = []
    for c in data[1]["data"]["children"]:
        if c["kind"] == "t1":
            cd = c["data"]
            comments.append({
                "author": cd["author"],
                "body": cd["body"],
                "score": cd["score"]
            })
    return {"post": post, "comments": comments}

def search_subreddit(subreddit, query, limit=25):
    """Search within a subreddit"""
    q = urllib.parse.quote(query)
    url = f"https://old.reddit.com/r/{subreddit}/search.json?q={q}&restrict_sr=on&limit={limit}"
    data = fetch_json(url)
    posts = []
    for p in data["data"]["children"]:
        d = p["data"]
        posts.append({
            "id": d["id"],
            "title": d["title"],
            "author": d["author"],
            "score": d["score"],
            "url": f"https://old.reddit.com{d['permalink']}"
        })
    return posts

def user_posts(username, limit=25):
    """Get posts by a user"""
    url = f"https://old.reddit.com/user/{username}.json?limit={limit}"
    data = fetch_json(url)
    posts = []
    for p in data["data"]["children"]:
        d = p["data"]
        posts.append({
            "id": d.get("id"),
            "title": d.get("title", d.get("body", "")[:100]),
            "subreddit": d.get("subreddit"),
            "score": d["score"],
            "url": f"https://old.reddit.com{d['permalink']}"
        })
    return posts

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: reddit.py <command> [args]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  posts <subreddit> [limit] [sort]", file=sys.stderr)
        print("  details <post_id> [subreddit]  - Get post by ID", file=sys.stderr)
        print("  details <url>                  - Get post by URL", file=sys.stderr)
        print("  search <subreddit> <query> [limit]", file=sys.stderr)
        print("  user <username> [limit]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    
    try:
        if cmd == "posts":
            subreddit = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 25
            sort = sys.argv[4] if len(sys.argv) > 4 else "hot"
            result = subreddit_posts(subreddit, limit, sort)
        elif cmd == "details":
            post_id_or_url = sys.argv[2]
            subreddit = sys.argv[3] if len(sys.argv) > 3 else None
            result = post_details(post_id_or_url, subreddit)
        elif cmd == "search":
            subreddit = sys.argv[2]
            query = sys.argv[3]
            limit = int(sys.argv[4]) if len(sys.argv) > 4 else 25
            result = search_subreddit(subreddit, query, limit)
        elif cmd == "user":
            username = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 25
            result = user_posts(username, limit)
        else:
            print(f"Unknown command: {cmd}", file=sys.stderr)
            sys.exit(1)
        
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)
