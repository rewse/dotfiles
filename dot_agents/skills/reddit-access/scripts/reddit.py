#!/usr/bin/env -S uv run
# /// script
# dependencies = [
#   "beautifulsoup4",
# ]
# ///
"""Reddit HTML scraper via old.reddit.com (no auth required)"""

import json
import re
import sys
import urllib.request
import urllib.parse
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"


def fetch_html(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_reddit_url(url):
    match = re.search(r'reddit\.com/r/([^/]+)/comments/([^/]+)', url)
    if match:
        return match.group(1), match.group(2)
    return None, None


def parse_post_thing(thing):
    """Extract post data from a div.thing element."""
    post_id = (thing.get("data-fullname") or "").replace("t3_", "")
    title_el = thing.select_one("a.title")
    return {
        "id": post_id,
        "title": title_el.get_text() if title_el else "",
        "author": thing.get("data-author", ""),
        "score": int(thing.get("data-score", 0)),
        "num_comments": int(thing.get("data-comments-count", 0)),
        "url": f"https://old.reddit.com{thing.get('data-permalink', '')}",
        "created_utc": int(thing.get("data-timestamp", 0)) // 1000,
    }


def parse_comment(thing):
    """Extract comment data from a div.thing[data-type=comment] element."""
    entry = thing.find("div", class_="entry", recursive=False)
    body_el = entry.select_one(".usertext-body .md") if entry else None
    score_el = entry.select_one(".score.unvoted") if entry else None
    score = 0
    if score_el and score_el.get("title"):
        try:
            score = int(score_el["title"])
        except ValueError:
            pass
    return {
        "author": thing.get("data-author", ""),
        "body": body_el.get_text().strip() if body_el else "",
        "score": score,
    }


def subreddit_posts(subreddit, limit=25, sort="hot"):
    url = f"https://old.reddit.com/r/{subreddit}/{sort}/"
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    things = soup.select("#siteTable > .thing[data-fullname^='t3_']")
    posts = []
    for thing in things[:limit]:
        if "promoted" in thing.get("class", []):
            continue
        posts.append(parse_post_thing(thing))
        if len(posts) >= limit:
            break
    return posts


def post_details(post_id_or_url, subreddit=None):
    if post_id_or_url.startswith("http"):
        subreddit, post_id = parse_reddit_url(post_id_or_url)
        if not post_id:
            raise ValueError("Invalid Reddit URL")
    else:
        post_id = post_id_or_url

    if subreddit:
        url = f"https://old.reddit.com/r/{subreddit}/comments/{post_id}/"
    else:
        url = f"https://old.reddit.com/comments/{post_id}/"

    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")

    # Parse post
    post_thing = soup.select_one(f".thing[data-fullname='t3_{post_id}']")
    post = {}
    if post_thing:
        title_el = post_thing.select_one("a.title")
        body_el = post_thing.select_one(".usertext-body .md")
        post = {
            "title": title_el.get_text() if title_el else "",
            "selftext": body_el.get_text().strip() if body_el else "",
            "author": post_thing.get("data-author", ""),
            "score": int(post_thing.get("data-score", 0)),
        }

    # Parse comments
    comment_things = soup.select(".commentarea .thing[data-type='comment']")
    comments = []
    for ct in comment_things:
        c = parse_comment(ct)
        if c["author"]:
            comments.append(c)

    return {"post": post, "comments": comments}


def search_subreddit(subreddit, query, limit=25):
    q = urllib.parse.quote(query)
    url = f"https://old.reddit.com/r/{subreddit}/search?q={q}&restrict_sr=on"
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    things = soup.select("#siteTable > .thing[data-fullname^='t3_']")
    posts = []
    for thing in things[:limit]:
        posts.append(parse_post_thing(thing))
    return posts


def user_posts(username, limit=25):
    url = f"https://old.reddit.com/user/{username}/"
    html = fetch_html(url)
    soup = BeautifulSoup(html, "html.parser")
    things = soup.select("#siteTable > .thing[data-fullname]")
    posts = []
    for thing in things[:limit]:
        fullname = thing.get("data-fullname", "")
        item_id = fullname.split("_", 1)[-1] if "_" in fullname else ""
        title_el = thing.select_one("a.title")
        body_el = thing.select_one(".usertext-body .md")
        posts.append({
            "id": item_id,
            "title": title_el.get_text() if title_el else (body_el.get_text()[:100].strip() if body_el else ""),
            "subreddit": thing.get("data-subreddit", ""),
            "score": int(thing.get("data-score", 0)),
            "url": f"https://old.reddit.com{thing.get('data-permalink', '')}",
        })
    return posts


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: reddit.py <command> [args]", file=sys.stderr)
        print("Commands:", file=sys.stderr)
        print("  posts <subreddit> [limit] [sort]", file=sys.stderr)
        print("  details <post_id|url> [subreddit]", file=sys.stderr)
        print("  search <subreddit> <query> [limit]", file=sys.stderr)
        print("  user <username> [limit]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "posts":
            sub = sys.argv[2]
            limit = int(sys.argv[3]) if len(sys.argv) > 3 else 25
            sort = sys.argv[4] if len(sys.argv) > 4 else "hot"
            result = subreddit_posts(sub, limit, sort)
        elif cmd == "details":
            target = sys.argv[2]
            sub = sys.argv[3] if len(sys.argv) > 3 else None
            result = post_details(target, sub)
        elif cmd == "search":
            sub = sys.argv[2]
            query = sys.argv[3]
            limit = int(sys.argv[4]) if len(sys.argv) > 4 else 25
            result = search_subreddit(sub, query, limit)
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
