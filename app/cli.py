# app/cli.py
"""
Simple CLI for generating briefings.
Usage:
  python -m app.cli generate --num 5
  python -m app.cli generate --num 8 --category tech
  python -m app.cli generate --categories tech,business
"""

import argparse
import json
from app.coordinator import generate_briefing
from app.memory.memory_bank import load_memory, update_preferences, add_feedback

def _parse_args():
    p = argparse.ArgumentParser(prog="news-briefing-cli")
    sub = p.add_subparsers(dest="cmd")

    gen = sub.add_parser("generate", help="Generate a briefing")
    gen.add_argument("--num", type=int, default=5, help="number of items")
    gen.add_argument("--category", type=str, help="single category (e.g. tech)")
    gen.add_argument("--categories", type=str, help="comma-separated categories (e.g. tech,business)")

    prefs = sub.add_parser("prefs", help="Manage preferences")
    prefs.add_argument("action", choices=["show","add","remove"], help="action")
    prefs.add_argument("--category", type=str, help="category to add/remove")

    return p.parse_args()

def run():
    args = _parse_args()
    if args.cmd == "generate":
        cats = None
        if args.categories:
            cats = [c.strip() for c in args.categories.split(",") if c.strip()]
        elif args.category:
            cats = [args.category.strip()]
        briefing = generate_briefing(top_n=args.num, categories=cats)
        print(json.dumps(briefing, indent=2))
    elif args.cmd == "prefs":
        mem = load_memory()
        if args.action == "show":
            print(json.dumps(mem.get("user_prefs", {}), indent=2))
        elif args.action == "add" and args.category:
            update_preferences(add_category=args.category.strip())
            print("Added category:", args.category)
        elif args.action == "remove" and args.category:
            update_preferences(remove_category=args.category.strip())
            print("Removed category:", args.category)
        else:
            print("Invalid prefs command. Use --category with add/remove.")
    else:
        print("No command. Use --help for usage.")

if __name__ == "__main__":
    run()
