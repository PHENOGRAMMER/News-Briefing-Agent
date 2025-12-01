# app/summarizer_agent.py
"""
Improved summarizer supporting:
- SUMY extractive summarizers: LSA, Luhn, LexRank, TextRank
- Simple keyword extraction (stopword-filtered TF)
- Hybrid extractive+compressive pipeline
- Optional generative rewrite via OpenAI (if OPENAI_API_KEY is set in env/secrets)
All implementations are torch-free.
"""

import os
import re
import json
import math
from typing import List, Tuple, Dict, Optional
from collections import Counter

# SUMY extractive summarizers
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lsa import LsaSummarizer
from sumy.summarizers.luhn import LuhnSummarizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize

# optional OpenAI generative rewrite (purely optional)
try:
    from openai import OpenAI
except Exception:
    OpenAI = None

# Ensure required NLTK data (quiet)
nltk.download("punkt", quiet=True)
nltk.download("stopwords", quiet=True)

EN_STOPWORDS = set(stopwords.words("english"))

# Optional OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or None
openai_client = None
if OPENAI_API_KEY and OpenAI is not None:
    try:
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        print("⚠️ OpenAI init failed (hybrid rewrite disabled):", e)
        openai_client = None


# ---------------------------
# Utilities
# ---------------------------
def _clean_text(text: str) -> str:
    """Basic cleanup for RSS snippet/title text."""
    if not text:
        return ""
    # remove HTML tags
    text = re.sub(r"<[^>]+>", " ", text)
    # remove multiple spaces/newlines
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _split_sentences(text: str) -> List[str]:
    text = text.strip()
    if not text:
        return []
    return sent_tokenize(text)


def _score_sentences_tfidf_like(text: str) -> Dict[str, float]:
    """Lightweight sentence scoring by counting keyword overlap.
    Returns dict sentence->score. Not a real TF-IDF but works well as a fallback."""
    sentences = _split_sentences(text)
    tokens = [w.lower() for w in word_tokenize(text) if w.isalpha()]
    tokens = [t for t in tokens if t not in EN_STOPWORDS and len(t) > 2]
    freq = Counter(tokens)
    scores = {}
    for s in sentences:
        s_tokens = [w.lower() for w in word_tokenize(s) if w.isalpha()]
        s_tokens = [t for t in s_tokens if t not in EN_STOPWORDS and len(t) > 2]
        # score = sum of freqs normalized
        score = sum(freq.get(t, 0) for t in s_tokens)
        scores[s] = float(score)
    return scores


def extract_keywords_simple(text: str, top_k: int = 8) -> List[Tuple[str, int]]:
    """Simple keyword extraction using word frequency excluding stopwords."""
    if not text:
        return []
    text = text.lower()
    tokens = [w for w in re.findall(r"[a-zA-Z]{3,}", text)]
    tokens = [t for t in tokens if t not in EN_STOPWORDS]
    counts = Counter(tokens)
    return counts.most_common(top_k)


def compress_sentence_heuristic(sentence: str) -> str:
    """Heuristic, rule-based sentence compression:
    - remove parenthetical or bracketed content
    - drop subordinate relative clauses starting with 'that', 'which', 'who'
    - collapse repeated commas, trim
    """
    if not sentence:
        return sentence

    s = sentence.strip()

    # remove parentheses/brackets content
    s = re.sub(r"\([^)]*\)", " ", s)
    s = re.sub(r"\[[^\\]]*\\]", " ", s)

    # remove relative clauses (naive)
    s = re.sub(r"\b(that|which|who|where|when)\b.*", "", s, flags=re.IGNORECASE)

    # remove multiple commas/ spaces
    s = re.sub(r",\s*,+", ",", s)
    s = re.sub(r"\s+", " ", s).strip()

    # Ensure sentence ends with period
    if not s.endswith("."):
        s = s.rstrip(".") + "."
    return s


# ---------------------------
# SUMY wrappers
# ---------------------------
_SUMMARY_METHODS = {
    "lsa": LsaSummarizer,
    "luhn": LuhnSummarizer,
    "lexrank": LexRankSummarizer,
    "textrank": TextRankSummarizer,
}


def summarize_with_sumy(text: str, method: str = "lexrank", sentence_count: int = 3) -> str:
    """Run SUMY summarizer and return joined sentences."""
    if not text:
        return ""

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    method = method.lower()
    SummClass = _SUMMARY_METHODS.get(method, LexRankSummarizer)
    summarizer = SummClass()
    try:
        summary_sentences = summarizer(parser.document, sentence_count)
        summary = " ".join(str(s) for s in summary_sentences).strip()
        if summary:
            return summary
    except Exception as e:
        # fallback to simple extractive scoring
        print(f"⚠️ SUMY {method} failed, fallback scoring: {e}")
    # fallback: highest scored sentences from simple scoring
    scores = _score_sentences_tfidf_like(text)
    if not scores:
        return ""
    # pick top sentence_count sentences, preserve original order
    top = sorted(scores.items(), key=lambda x: -x[1])[:sentence_count]
    top_set = set(s for s, _ in top)
    ordered = [s for s in _split_sentences(text) if s in top_set]
    return " ".join(ordered)


# ---------------------------
# Hybrid: extract + compress + optional generative rewrite
# ---------------------------
def _openai_rewrite(extractive: str, direction: str = "concise") -> Optional[str]:
    """If openai_client is available, ask it to rewrite/fuse extractive summary into a concise coherent paragraph.
    This is optional and only used when OPENAI_API_KEY is configured in the environment/streamlit secrets.
    """
    if not openai_client:
        return None

    # create a small prompt instructing to rewrite concisely
    prompt = (
        "Take the following sentences (extracted from a news article) and rewrite them into "
        "a single clear, concise 2-sentence summary. Keep facts only; do not add new facts.\n\n"
        "Extracted sentences:\n"
        + extractive
        + "\n\nRewrite:"
    )

    try:
        resp = openai_client.responses.create(
            model="gpt-4o-mini",  # small inexpensive model; adjust if you prefer
            input=prompt,
            max_output_tokens=200
        )
        raw = None
        # `output_text` property may be present depending on OpenAI client version
        if hasattr(resp, "output_text"):
            raw = resp.output_text
        else:
            # try to get first text from choices / output
            outputs = getattr(resp, "output", None)
            if outputs:
                # try to join text segments safely
                if isinstance(outputs, list):
                    raw = " ".join([o.get("text", "") for o in outputs if isinstance(o, dict)])
                elif isinstance(outputs, dict):
                    raw = outputs.get("text") or json.dumps(outputs)
        if raw:
            return raw.strip()
    except Exception as e:
        print("⚠️ OpenAI rewrite failed:", e)
    return None


def hybrid_summarize(title: str, snippet: str, url: str, method: str = "lexrank", max_sentences: int = 3, use_openai_if_available: bool = True) -> Dict:
    """
    Hybrid pipeline:
    1. Run extractive summarizer (SUMY) with chosen method
    2. Extract keywords from (title + snippet)
    3. Compress sentences heuristically
    4. Optionally use OpenAI to rewrite/fuse into a final 1-2 sentence summary (if secret present)
    Returns dict: {summary, tldr, confidence, keywords, method}
    """
    title = _clean_text(title or "")
    snippet = _clean_text(snippet or "")
    combined = (title + "\n\n" + snippet).strip() or title or snippet

    # 1) Extractive output
    extractive_raw = summarize_with_sumy(combined, method=method, sentence_count=max_sentences)
    if not extractive_raw:
        # fallback: use first N sentences of snippet/title
        sents = _split_sentences(combined)
        extractive_raw = " ".join(sents[:max_sentences])

    # 2) keywords
    keywords = extract_keywords_simple(combined, top_k=8)

    # 3) compress sentences
    sents = _split_sentences(extractive_raw)
    compressed = " ".join(compress_sentence_heuristic(s) for s in sents if s.strip())
    if not compressed:
        compressed = extractive_raw

    # 4) optional generative rewrite
    final = compressed
    gen_used = False
    if use_openai_if_available and openai_client:
        rewritten = _openai_rewrite(compressed)
        if rewritten:
            final = rewritten
            gen_used = True

    # short tldr = first sentence of final
    tldr = _split_sentences(final)
    tldr = (tldr[0].strip() + ".") if tldr else (compressed.split(".")[0].strip() + ".")

    # confidence heuristic:
    # - extractive only -> 0.60-0.70 depending on method
    # - hybrid with gen -> 0.88
    base_conf = 0.6
    method_conf_map = {"lexrank": 0.65, "lsa": 0.62, "luhn": 0.60, "textrank": 0.66}
    base_conf = method_conf_map.get(method.lower(), 0.63)
    if gen_used:
        confidence = 0.88
    else:
        # scale confidence by ratio of compressed length to raw extractive (shorter = more concise but maybe lossy)
        try:
            ratio = min(1.0, len(compressed) / (len(extractive_raw) + 1e-6))
            confidence = round(base_conf * (0.75 + 0.5 * ratio), 2)
        except Exception:
            confidence = base_conf

    return {
        "summary": final,
        "tldr": tldr,
        "confidence": float(confidence),
        "keywords": [k for k, _ in keywords],
        "method": method,
        "gen_used": gen_used,
    }


# ---------------------------
# Backwards-compatible API
# ---------------------------
def call_gemini_summarize(title: str, snippet: str, url: str, max_sentences: int = 3):
    """
    Default entrypoint used by coordinator.
    Uses hybrid_summarize with LexRank by default.
    Returns dict with summary, tldr, confidence (and optionally keywords/method).
    """
    try:
        res = hybrid_summarize(title, snippet, url, method="lexrank", max_sentences=max_sentences, use_openai_if_available=True)
        # keep the same minimal keys as before for compatibility
        return {
            "summary": res.get("summary"),
            "tldr": res.get("tldr"),
            "confidence": res.get("confidence"),
            # attach extras for debugging/analytics (coordinator/UI can ignore)
            "keywords": res.get("keywords"),
            "method": res.get("method"),
            "gen_used": res.get("gen_used"),
        }
    except Exception as e:
        print("❌ hybrid summarizer failed, fallback:", e)
        base_text = (snippet or title or "").strip() or "News article"
        return {
            "summary": base_text[:250] + ("..." if len(base_text) > 250 else ""),
            "tldr": base_text.split(".")[0] + "...",
            "confidence": 0.4
        }
