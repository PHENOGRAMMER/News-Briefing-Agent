# app/observability/traces.py
"""
Simple trace utility: create a trace object per briefing, append steps, and save as JSON in traces/ folder.
"""

import json
import os
import uuid
import time
from typing import Dict, Any

TRACE_DIR = os.path.join(os.path.dirname(__file__), "traces")
os.makedirs(TRACE_DIR, exist_ok=True)

def new_trace() -> Dict[str, Any]:
    return {"trace_id": str(uuid.uuid4()), "start_time": time.time(), "steps": [], "end_time": None}

def add_step(trace: Dict[str, Any], name: str, duration_ms: int, status: str = "ok", meta: dict = None):
    trace["steps"].append({
        "name": name,
        "duration_ms": int(duration_ms),
        "status": status,
        "meta": meta or {}
    })

def end_trace(trace: Dict[str, Any]):
    trace["end_time"] = time.time()
    path = os.path.join(TRACE_DIR, f"{trace['trace_id']}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)
    return path

def record_trace(name: str, func, *args, **kwargs):
    """
    Convenience wrapper to automatically create a trace,
    time the function, store the step, and save the trace.
    """
    trace = new_trace()
    start = time.time()
    try:
        result = func(*args, **kwargs)
        duration = (time.time() - start) * 1000
        add_step(trace, name, duration_ms=duration, status="ok")
    except Exception as e:
        duration = (time.time() - start) * 1000
        add_step(trace, name, duration_ms=duration, status="error", meta={"error": str(e)})
        end_trace(trace)
        raise e
    end_trace(trace)
    return result
