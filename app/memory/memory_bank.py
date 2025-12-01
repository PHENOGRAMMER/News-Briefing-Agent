# app/memory/memory_bank.py
import json, os, time

DB_PATH = os.path.join(os.path.dirname(__file__), "memory.json")
DEFAULT = {"user_prefs": {"categories": ["tech","business"], "max_items": 5}, "muted_sources": []}

def load_memory():
    if not os.path.exists(DB_PATH):
        save_memory(DEFAULT)
    with open(DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_memory(obj):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)

def update_preferences(add_category=None, remove_category=None, set_categories=None):
    mem = load_memory()
    prefs = mem.get("user_prefs", {})
    cats = prefs.get("categories", [])
    if set_categories is not None:
        cats = set_categories
    if add_category:
        if add_category not in cats:
            cats.append(add_category)
    if remove_category:
        cats = [c for c in cats if c != remove_category]
    prefs["categories"] = cats
    mem["user_prefs"] = prefs
    save_memory(mem)
    return prefs

def add_feedback(fingerprint, score):
    mem = load_memory()
    fb = mem.get("feedback", [])
    fb.append({"fp": fingerprint, "score": score, "ts": time.time()})
    mem["feedback"] = fb
    save_memory(mem)
