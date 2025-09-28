#!/usr/bin/env python3
"""logging_utils.py
Helper functions to write per-tool logs and append results to results.json
"""

import os
import json
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_DIR = os.path.join(ROOT, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.json")

def ts():
    return datetime.utcnow().isoformat() + "Z"

def write_tool_log(tool_name: str, text: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    safe_name = tool_name.lower().replace(" ", "_")
    path = os.path.join(LOG_DIR, f"{safe_name}.log")
    with open(path, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"--- {ts()} ---\n")
        f.write(text if text is not None else "")
        f.write("\n\n")

def append_result(result_obj: dict):
    # ensure structure exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f)
    # read, append, write
    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except Exception:
        data = []
    data.append(result_obj)
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
