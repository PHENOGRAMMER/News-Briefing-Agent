import feedparser
from typing import List, Dict

# You can add/remove feeds here
RSS_FEEDS = [
    "http://feeds.bbci.co.uk/news/rss.xml",
    "https://www.aljazeera.com/xml/rss/all.xml",
    "https://feeds.reuters.com/reuters/topNews",
    "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"
]


def fetch_top_headlines(num: int = 5) -> List[Dict]:
    """
    Fetches real news headlines from RSS feeds.
    Returns a list of dicts: [{"title":..., "snippet":..., "url":...}, ...]
    """
    articles = []

    for feed_url in RSS_FEEDS:
        parsed = feedparser.parse(feed_url)

        if "entries" not in parsed:
            continue

        for entry in parsed.entries:
            title = entry.get("title", "")
            description = entry.get("summary", "") or entry.get("description", "")
            link = entry.get("link", "")

            if title and link:
                articles.append({
                    "title": title,
                    "snippet": description[:250],  # limit size
                    "url": link
                })

    # Deduplicate and trim
    unique_titles = set()
    cleaned_articles = []

    for a in articles:
        if a["title"] not in unique_titles:
            cleaned_articles.append(a)
            unique_titles.add(a["title"])

    # Return first N
    return cleaned_articles[:num]
