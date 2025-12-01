# app/tools/article_fetcher.py
"""
Fetches full article text from a URL for deep-dive operations.
Mock implementation: returns a long dummy article body for testing.
Replace scraping / API logic with a reliable article extraction tool (newspaper3k, Mercury API, or direct fetch+parse).
"""

import os
from typing import Optional

USE_MOCK = os.getenv("USE_MOCK", "true").lower() in ("1", "true", "yes")

def fetch_full_article(url: str) -> Optional[str]:
    """
    Returns the full article text as a string or None if unavailable.
    """
    if USE_MOCK:
        body = (
            "Full article text (mock). This paragraph simulates a longer article body. "
            "Continue with additional sentences to emulate realistic content. "
            "The article provides background, quotes from experts, and a closing summary. "
        )
        return body * 6  # make it reasonably long
    else:
        # TODO: Replace with actual fetch-and-parse (requests + BeautifulSoup / readability / newspaper3k)
        # Example pseudocode:
        # resp = requests.get(url, timeout=10)
        # soup = BeautifulSoup(resp.text, "html.parser")
        # article_text = extract_main_text(soup)
        # return article_text
        raise NotImplementedError("Real article fetch not implemented. Set USE_MOCK=true to run locally.")
