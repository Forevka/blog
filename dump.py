#!/usr/bin/env python3
"""
Wayback Machine blog dumper for forevka.dev
- Enumerates all crawled URLs via CDX API
- Downloads each article page from the best available snapshot
- Extracts clean text + markdown from HTML
- Saves each post as a .md file and produces a combined dump

Usage:
    pip install requests beautifulsoup4 html2text
    python dump_forevka_blog.py
"""

import json
import os
import re
import time
import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import html2text

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DOMAIN   = "forevka.dev"
OUTPUT_DIR    = "./forevka_dump"
DELAY_SECONDS = 2          # be polite to archive.org
CDX_LIMIT     = 500        # increase if you have more posts
# ─────────────────────────────────────────────────────────────────────────────

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "forevka-blog-recovery/1.0 (personal backup)"})


def cdx_list_urls() -> list[dict]:
    """Query the CDX API and return unique article URLs with their best timestamp."""
    print("📡 Querying Wayback Machine CDX API...")
    url = (
        f"https://web.archive.org/cdx/search/cdx"
        f"?url={BASE_DOMAIN}/*"
        f"&output=json"
        f"&fl=original,timestamp,statuscode,mimetype"
        f"&collapse=urlkey"          # one entry per unique URL
        f"&filter=statuscode:200"    # only successful captures
        f"&filter=mimetype:text/html"
        f"&limit={CDX_LIMIT}"
    )
    resp = SESSION.get(url, timeout=30)
    resp.raise_for_status()
    rows = resp.json()
    if not rows:
        return []
    headers, *data = rows
    return [dict(zip(headers, row)) for row in data]


def is_article(url: str) -> bool:
    """Heuristic: only download URLs that look like blog posts."""
    path = urlparse(url).path.rstrip("/")
    # Adjust these patterns to match your blog's URL structure
    return bool(re.search(r"/(articles|posts|blog)/[^/]+$", path))


def wayback_url(original: str, timestamp: str) -> str:
    return f"https://web.archive.org/web/{timestamp}/{original}"


def slug_from_url(url: str) -> str:
    path = urlparse(url).path.strip("/")
    return re.sub(r"[^a-zA-Z0-9_-]", "_", path)[:120] or "index"


def extract_content(html: str, source_url: str) -> dict:
    """Pull title + clean markdown body out of the archived HTML."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove Wayback Machine toolbar injected at top
    for tag in soup.find_all(id=re.compile(r"wm-ipp|wm-toolbar", re.I)):
        tag.decompose()
    for tag in soup.find_all(class_=re.compile(r"wb-autocomplete|wayback", re.I)):
        tag.decompose()

    # Title
    title = ""
    if soup.title:
        title = soup.title.get_text(strip=True)
    if og := soup.find("meta", property="og:title"):
        title = og.get("content", title)
    if h1 := soup.find("h1"):
        title = h1.get_text(strip=True)

    # Main content — try common article containers first
    body_el = (
        soup.find("article")
        or soup.find(class_=re.compile(r"post[-_]?content|article[-_]?body|entry[-_]?content|prose", re.I))
        or soup.find("main")
        or soup.body
    )

    h = html2text.HTML2Text()
    h.ignore_links    = False
    h.ignore_images   = False
    h.body_width      = 0       # don't wrap lines
    h.unicode_snob    = True
    markdown = h.handle(str(body_el)) if body_el else ""

    # Strip leftover Wayback Machine artefacts from the markdown
    markdown = re.sub(r"https?://web\.archive\.org/web/\d+/", "", markdown)
    markdown = markdown.strip()

    return {"title": title, "markdown": markdown, "source": source_url}


def save_post(post: dict, out_dir: str, slug: str):
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{slug}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {post['title']}\n\n")
        f.write(f"> Source: {post['source']}\n\n")
        f.write("---\n\n")
        f.write(post["markdown"])
    return path


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    entries = cdx_list_urls()
    print(f"  → Found {len(entries)} unique URLs in the archive")

    articles = [e for e in entries if is_article(e["original"])]
    other    = [e for e in entries if not is_article(e["original"])]

    print(f"  → {len(articles)} look like article pages")
    print(f"  → {len(other)} other URLs (home, tags, etc.) — skipping\n")

    if not articles:
        print("⚠️  No article URLs matched. Check the is_article() filter.")
        print("    All found URLs:")
        for e in entries:
            print(f"    {e['original']}")
        return

    combined_parts = []
    failed = []

    for i, entry in enumerate(articles, 1):
        original  = entry["original"]
        timestamp = entry["timestamp"]
        wb_url    = wayback_url(original, timestamp)
        slug      = slug_from_url(original)

        print(f"[{i}/{len(articles)}] {original}")
        print(f"  snapshot: {timestamp}")

        try:
            resp = SESSION.get(wb_url, timeout=30)
            resp.raise_for_status()
            post = extract_content(resp.text, original)
            path = save_post(post, OUTPUT_DIR, slug)
            print(f"  ✅ saved → {path}")
            combined_parts.append(f"# {post['title']}\n\n> Source: {original}\n\n---\n\n{post['markdown']}\n\n{'='*80}\n\n")
        except Exception as e:
            print(f"  ❌ failed: {e}")
            failed.append((original, str(e)))

        if i < len(articles):
            time.sleep(DELAY_SECONDS)

    # Write combined dump
    combined_path = os.path.join(OUTPUT_DIR, "_ALL_POSTS.md")
    with open(combined_path, "w", encoding="utf-8") as f:
        f.write(f"# forevka.dev — full blog dump\n\n")
        f.write(f"Total posts recovered: {len(articles) - len(failed)}\n\n")
        f.write("="*80 + "\n\n")
        f.writelines(combined_parts)
    print(f"\n📦 Combined dump → {combined_path}")

    # Write CDX JSON for reference
    cdx_path = os.path.join(OUTPUT_DIR, "_cdx_index.json")
    with open(cdx_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)
    print(f"📋 CDX index → {cdx_path}")

    if failed:
        print(f"\n⚠️  {len(failed)} failed:")
        for url, err in failed:
            print(f"   {url}: {err}")


if __name__ == "__main__":
    main()