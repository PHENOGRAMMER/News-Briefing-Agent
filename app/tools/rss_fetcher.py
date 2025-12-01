# app/tools/rss_fetcher.py
"""
Robust RSS fetcher.
- Uses feedparser to parse RSS/Atom.
- Returns list of dicts: {"title","snippet","url","published","image"}
- Supports multiple feeds per category.
"""

from typing import List, Dict
import feedparser
import requests  # kept in case you later add direct HTTP checks
import logging
from html import unescape
import re
import time
import random

logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Main category -> list of feed URLs.
RSS_FEEDS = {
    "tech": [
        "https://www.theverge.com/tech/rss/index.xml",
        "https://techcrunch.com/feed/",
        "https://www.wired.com/feed/category/gear/latest/rss",
        "https://feeds.arstechnica.com/arstechnica/technology-lab",
        "https://www.engadget.com/rss.xml",
    ],
    "world": [
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.aljazeera.com/xml/rss/all.xml",
    ],
    "business": [
        "http://feeds.bbci.co.uk/news/business/rss.xml",
        "https://www.ft.com/?format=rss",
        "https://www.forbes.com/business/feed/",
    ],
    "sports": [
        "https://www.espn.com/espn/rss/news",
        "http://feeds.bbci.co.uk/sport/rss.xml?edition=uk",
        "https://www.cbssports.com/rss/headlines/",
    ],
    "health": [
        "https://rss.nytimes.com/services/xml/rss/nyt/Health.xml",
        "http://feeds.bbci.co.uk/news/health/rss.xml",
        "https://www.medicalnewstoday.com/rss",
    ],
    "entertainment": [
        "http://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
        "https://variety.com/feed/",
        "https://www.rollingstone.com/culture/culture-news/feed/",
    ],
    "science": [
        "https://www.sciencedaily.com/rss/all.xml",
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.livescience.com/feeds/all",
    ],
    # India-specific (optional)
    "india": [
        "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "https://www.hindustantimes.com/rss/feeds/homepage/rssfeed.xml",
        "https://www.thehindu.com/news/national/feeder/default.rss",
    ],
}

# Flatten keys and provide supported category list
SUPPORTED_CATEGORIES = sorted(list(RSS_FEEDS.keys()))


def _extract_image_from_entry(entry) -> str:
    # Try common RSS media fields

    # 1) media_content
    mc = entry.get("media_content") or entry.get("media:content")
    if mc:
        try:
            if isinstance(mc, list) and mc:
                return mc[0].get("url") or mc[0].get("value")
            if isinstance(mc, dict):
                return mc.get("url")
        except Exception:
            pass

    # 2) media_thumbnail
    mt = entry.get("media_thumbnail") or entry.get("media:thumbnail")
    if mt:
        try:
            if isinstance(mt, list) and mt:
                return mt[0].get("url")
            if isinstance(mt, dict):
                return mt.get("url")
        except Exception:
            pass

    # 3) enclosure link
    links = entry.get("links") or []
    for L in links:
        if L.get("rel") == "enclosure" and L.get("type", "").startswith("image"):
            return L.get("href")

    # 4) Try to parse an <img> from summary
    summary = entry.get("summary") or entry.get("description") or ""
    m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', summary)
    if m:
        return m.group(1)

    # 5) Try 'thumbnail' field
    if entry.get("thumbnail"):
        return entry.get("thumbnail")

    return ""


def _clean_text(html_text: str) -> str:
    if not html_text:
        return ""
    text = re.sub(r"<[^>]+>", "", html_text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_feed(url: str, num: int = 5) -> List[Dict]:
    """
    Parse a single feed URL and return up to ~num*3 articles.
    Actual trimming to final `num` is done in fetch_rss().
    """
    try:
        f = feedparser.parse(url)
        entries = f.entries or []
    except Exception as e:
        logger.warning("Failed parse %s : %s", url, e)
        return []

    articles: List[Dict] = []
    max_entries = max(num * 3, 30)  # look deeper for richer feeds

    for e in entries[:max_entries]:
        title = (e.get("title") or "").strip()
        snippet = _clean_text(e.get("summary", "") or e.get("description", ""))
        link = e.get("link") or e.get("id") or ""
        published = e.get("published") or e.get("updated") or ""
        image = _extract_image_from_entry(e) or ""

        if not (title or link):
            continue

        articles.append(
            {
                "title": title,
                "snippet": snippet,
                "url": link,
                "published": published,
                "image": image,
            }
        )

    return articles


def fetch_rss(category: str, num: int = 5) -> List[Dict]:
    """
    Fetch up to `num` articles for `category` (category key).
    If multiple feeds exist for the category, aggregate and dedupe by URL+title
    and return up to num.
    """
    cat = (category or "tech").lower()
    # tolerant lookup
    feeds = (
        RSS_FEEDS.get(cat)
        or RSS_FEEDS.get(cat.rstrip("s"))
        or RSS_FEEDS.get(cat + "s")
    )
    if not feeds:
        # ultimate fallback: tech feeds
        feeds = RSS_FEEDS.get("tech", [])

    if isinstance(feeds, str):
        feed_urls = [feeds]
    else:
        feed_urls = list(feeds)

    all_articles: List[Dict] = []
    seen = set()

    for url in feed_urls:
        try:
            parsed = _parse_feed(url, num=num)
            for a in parsed:
                url_clean = (a.get("url") or "").split("?")[0]
                title = a.get("title") or ""
                key = (url_clean + "|" + title).lower().strip()
                if not key:
                    continue
                if key in seen:
                    continue
                seen.add(key)
                all_articles.append(a)
        except Exception as e:
            logger.warning("Failed HTTP/parse %s : %s", url, e)

    # Shuffle for freshness / variety
    random.shuffle(all_articles)

    # Return at most num
    return all_articles[:num]


def test_feeds():
    """Handy test function (run: python -m app.tools.rss_fetcher)"""
    print("Testing feeds...")
    for k in SUPPORTED_CATEGORIES:
        print("==", k, "==")
        a = fetch_rss(k, num=5)
        print(len(a))
        for i, art in enumerate(a[:3]):
            print(i + 1, art["title"][:80])
        time.sleep(0.2)


if __name__ == "__main__":
    test_feeds()
