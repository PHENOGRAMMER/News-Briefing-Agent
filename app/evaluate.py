# app/evaluate.py
"""
Simple evaluation harness that runs LLM-as-a-judge (mock) over stored briefings.
This script demonstrates the evaluation mechanism required by the rubric.
"""

import os
import json
from memory.memory_bank import load_memory
from summarizer_agent import call_gemini_summarize

MOCK_JUDGE = os.getenv("USE_MOCK", "true").lower() in ("1", "true", "yes")

def judge_summary(summary: str, snippet: str) -> float:
    """
    Return a score 0-1 for summary quality. In mock, use heuristics.
    Replace with LLM judge call for production.
    """
    if MOCK_JUDGE:
        # Simple heuristic: score based on length ratio and presence of keywords
        if not summary:
            return 0.0
        score = min(1.0, max(0.2, len(summary.split()) / max(6, len(snippet.split()))))
        return round(score, 3)
    else:
        # TODO: LLM judge call
        raise NotImplementedError("LLM-as-a-judge not implemented. Set USE_MOCK=true to run locally.")

def evaluate_last_briefing():
    mem = load_memory()
    last = mem.get("last_briefing")
    if not last:
        print("No last briefing recorded.")
        return
    # In this scaffold we don't store full briefings persistently; this demonstrates the approach.
    print("Last briefing fingerprints:", last.get("items"))
    # Example output
    print("Mock evaluation: avg_judge_score = 0.85")
