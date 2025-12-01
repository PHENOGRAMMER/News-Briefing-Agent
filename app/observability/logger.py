# app/observability/logger.py
"""
Simple structured logger. Writes to stdout and an events log file (events.log).
Logs are JSON-lines for easy ingestion.
"""

import json
import os
import sys
import datetime

LOG_PATH = os.path.join(os.path.dirname(__file__), "events.log")

def _now_iso():
    return datetime.datetime.utcnow().isoformat() + "Z"

def log_event(event_type: str, payload: dict):
    record = {
        "ts": _now_iso(),
        "event": event_type,
        "payload": payload
    }
    line = json.dumps(record, ensure_ascii=False)
    # stdout
    print(line, file=sys.stdout)
    # append to file
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")
