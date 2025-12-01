# app/utils.py
"""
Small utilities used by coordinator and CLI
"""

import hashlib
from typing import Dict

def fingerprint_article(item: Dict) -> str:
    """
    Create a stable fingerprint for an article based on title+url
    """
    key = (item.get("title", "") + "|" + item.get("url", "")).encode("utf-8")
    return hashlib.sha256(key).hexdigest()
