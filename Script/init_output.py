#!/usr/bin/env python3
"""
init_output.py
Create output folders and initial results.json if missing.
"""

import os
import json

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # repo root assuming script in scripts/
OUTPUT_DIR = os.path.join(ROOT, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.json")

def ensure_dirs():
    os.makedirs(LOG_DIR, exist_ok=True)
    # create .gitkeep for git tracking (if desired)
    gitkeep_output = os.path.join(OUTPUT_DIR, ".gitkeep")
    gitkeep_logs = os.path.join(LOG_DIR, ".gitkeep")
    for p in (gitkeep_output, gitkeep_logs):
        if not os.path.exists(p):
            open(p, "w").close()

def ensure_results_json():
    if not os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

def main():
    ensure_dirs()
    ensure_results_json()
    print(f"Initialized output folder and {RESULTS_FILE}")

if __name__ == "__main__":
    main()
