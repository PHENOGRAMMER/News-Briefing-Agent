# app/summarizer_agent.py
"""
FAST Summarizer using HuggingFace Transformers
Model: sshleifer/distilbart-cnn-12-6
- Very fast
- Good summary quality
- No API keys required
"""

import re
import json
from transformers import pipeline

# Load summarizer (fast distilbart model)
summarizer = pipeline(
    "summarization",
    model="sshleifer/distilbart-cnn-12-6",
    tokenizer="sshleifer/distilbart-cnn-12-6"
)

def call_gemini_summarize(title: str, snippet: str, url: str, max_sentences=2):
    """
    Returns:
    {
        'summary': '...',
        'tldr': '...',
        'confidence': 0.85
    }
    """
    base_text = (snippet or title or "").strip() or "News article"

    # Combine text for better summarization
    content = f"{title}\n\n{snippet}" if snippet else title

    try:
        result = summarizer(
            content,
            max_length=100,
            min_length=25,
            do_sample=False
        )
        summary_text = result[0]["summary_text"]

        # TL;DR = first sentence
        tldr = summary_text.split(".")[0].strip() + "."

        return {
            "summary": summary_text,
            "tldr": tldr,
            "confidence": 0.85
        }

    except Exception as e:
        print("❌ Summarizer error, fallback used:", e)
        return {
            "summary": base_text[:250] + ("..." if len(base_text) > 250 else ""),
            "tldr": base_text.split(".")[0][:120] + "...",
            "confidence": 0.4
        }
