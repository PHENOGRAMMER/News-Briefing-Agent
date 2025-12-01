# app/coordinator.py
"""
Coordinator - orchestrates fetch -> summarize -> categorize -> produce final briefing.
This version:
- respects top_n as final total count
- dedupes using URL/title fingerprint
- avoids over-filtering (category + last briefing)
- uses memory via memory_bank functions (assumes they exist)
"""

from typing import List, Optional
import time
import random
import logging

from tools.rss_fetcher import fetch_rss, SUPPORTED_CATEGORIES
from summarizer_agent import call_gemini_summarize
from categorizer_agent import categorize_article
from memory.memory_bank import load_memory, save_memory
from observability.logger import log_event
from observability.traces import new_trace, add_step, end_trace
from utils import fingerprint_article

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def generate_briefing(
    user_id: str = "default",
    top_n: int = 10,
    categories: Optional[List[str]] = None,
):
    mem = load_memory() or {}
    preferred_categories = mem.get("user_prefs", {}).get("categories", [])
    last_fps = mem.get("last_briefing", {}).get("items", [])

    trace = new_trace()
    t0 = time.time()

    # normalize categories (case-insensitive, filter to supported)
    if categories:
        cats = [
            c.strip().lower()
            for c in categories
            if c and isinstance(c, str)
        ]
        cats = [c for c in cats if c in SUPPORTED_CATEGORIES]
        if not cats:
            cats = None
    else:
        cats = None

    # FETCH
    start_fetch = time.time()
    collected = []

    if cats:
        # explicit categories: fetch up to top_n per category (before trimming)
        for c in cats:
            try:
                arts = fetch_rss(c, num=max(top_n, 5))
                # annotate category at source level
                for a in arts:
                    a.setdefault("category", c)
                collected.extend(arts)
            except Exception as e:
                logger.warning("fetch_rss error for %s: %s", c, e)
    else:
        # if none provided, fetch across a subset of supported categories
        sample_cats = SUPPORTED_CATEGORIES[:5]
        for c in sample_cats:
            try:
                arts = fetch_rss(c, num=max(3, top_n // 2))
                for a in arts:
                    a.setdefault("category", c)
                collected.extend(arts)
            except Exception as e:
                logger.warning("fetch_rss error for %s: %s", c, e)

    fetch_ms = int((time.time() - start_fetch) * 1000)
    add_step(trace, "fetch", fetch_ms, "ok", {"collected": len(collected)})
    log_event(
        "fetch",
        {"requested_categories": cats, "collected": len(collected)},
    )

    # Dedupe by URL/title fingerprint
    seen = set()
    deduped = []
    for a in collected:
        fp = fingerprint_article(a)
        if not fp:
            continue
        if fp in seen:
            continue
        seen.add(fp)
        a["fingerprint"] = fp
        deduped.append(a)

    # Avoid items from last briefing if possible (but don't overkill)
    unique = [u for u in deduped if u["fingerprint"] not in last_fps]
    # If filtering by last briefing kills too many, fall back to full deduped list
    if len(unique) < max(1, int(top_n * 0.6)):
        unique = deduped

    # Shuffle for freshness
    random.shuffle(unique)

    # Summarize + categorize
    results = []
    for a in unique:
        title = a.get("title", "") or ""
        snippet = a.get("snippet", "") or title
        url = a.get("url", "") or ""

        # prefer feed-level category; otherwise classify via heuristics
        category = a.get("category") or categorize_article(title, snippet)

        s_start = time.time()
        summ = call_gemini_summarize(title, snippet, url, max_sentences=2)
        s_ms = int((time.time() - s_start) * 1000)
        add_step(
            trace,
            "summarize_item",
            s_ms,
            "ok",
            {"title": title[:80]},
        )

        results.append(
            {
                "title": title,
                "snippet": snippet,
                "url": url,
                "category": category,
                "image": a.get("image", ""),
                "summary": summ.get("summary"),
                "tldr": summ.get("tldr"),
                "confidence": float(summ.get("confidence", 0.5)),
                "fingerprint": a.get("fingerprint"),
            }
        )

    # If categories filter present, keep only those categories,
    # but don't throw everything away if misclassification happens.
    if cats:
        filtered = [r for r in results if r["category"] in cats]
        if len(filtered) >= max(1, int(top_n * 0.6)):
            results = filtered
        # else: keep unfiltered 'results' to avoid empty briefings

    # Sort: preferred categories first, then by confidence (desc)
    results = sorted(
        results,
        key=lambda r: (
            r["category"] not in preferred_categories,
            -float(r.get("confidence", 0.0)),
        ),
    )

    # Trim final list to exactly top_n (if not enough, keep what we have)
    final = results[:top_n]

    briefing = {
        "generated_at": time.time(),
        "items": final,
        "user_id": user_id,
        "selected_categories": cats or [],
    }

    add_step(
        trace,
        "compose",
        int((time.time() - t0) * 1000),
        "ok",
        {"final_count": len(final)},
    )
    trace_path = end_trace(trace)
    log_event(
        "briefing_generated",
        {"user_id": user_id, "count": len(final), "trace": trace_path},
    )

    # Save last briefing fingerprints
    mem["last_briefing"] = {
        "items": [i["fingerprint"] for i in final if i.get("fingerprint")],
        "ts": time.time(),
    }
    save_memory(mem)

    return briefing
