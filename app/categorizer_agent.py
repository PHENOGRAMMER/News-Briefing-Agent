# app/categorizer_agent.py
"""
Simple categorizer agent.
Uses keyword heuristics in mock mode.
For higher quality, replace with an LLM classification call or a small keyword model.
"""

import os
import random
from typing import List

USE_MOCK = os.getenv("USE_MOCK", "true").lower() in ("1", "true", "yes")

CATEGORIES = [
    "tech",
    "business",
    "world",
    "sports",
    "science",
    "health",
    "entertainment",
    "india",
]


def categorize_article(title: str, snippet: str) -> str:
    """
    Return a category string. In mock mode, uses simple keyword matching
    and falls back to a random valid category to avoid uncategorized items.
    """
    if USE_MOCK:
        lower = (title or "").lower() + " " + (snippet or "").lower()

        if any(w in lower for w in ["market", "econom", "stock", "business", "trade", "invest"]):
            return "business"

        if any(w in lower for w in ["ai", "tech", "sdk", "software", "developer", "chip", "semiconductor", "app", "startup"]):
            return "tech"

        if any(w in lower for w in ["football", "cricket", "tournament", "goal", "match", "penalt", "nba", "fifa", "olympic"]):
            return "sports"

        if any(w in lower for w in ["health", "flu", "vaccin", "hospital", "covid", "disease", "medical"]):
            return "health"

        if any(w in lower for w in ["science", "research", "battery", "study", "quantum", "space", "experiment"]):
            return "science"

        if any(w in lower for w in ["film", "movie", "concert", "celebr", "music", "series", "bollywood", "hollywood"]):
            return "entertainment"

        if any(w in lower for w in ["india", "delhi", "mumbai", "bangalore", "karnataka", "modi", "parliament"]):
            return "india"

        # default: "world" if obviously geopolitics, else random for variety
        if any(w in lower for w in ["war", "election", "government", "president", "minister", "united nations", "eu", "china", "russia"]):
            return "world"

        return random.choice(CATEGORIES)
    else:
        # TODO: Replace with LLM classifier or ML model
        raise NotImplementedError(
            "Categorizer with LLM not implemented. Set USE_MOCK=true to run locally."
        )
