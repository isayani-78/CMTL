#!/usr/bin/env python3
"""
tool_launcher.py - CMTL launcher (CLI + simple GUI)
Safe output initialization included (ensures output/logs and results.json).
This file focuses on robust startup and calling internal tools.
"""
import os
import sys
import json
import subprocess
import shutil
import argparse
import threading
from datetime import datetime

# optional tkinter UI
try:
    import tkinter as tk
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_PATH = os.path.join(OUTPUT_DIR, "results.json")
TOOLS_DIR = os.path.join(ROOT, "tools")

# -------------------------
# Safe initialization helpers
# -------------------------
def ensure_output():
    """Ensure output folders exist and results.json is a JSON list."""
    os.makedirs(LOG_DIR, exist_ok=True)
    # create .gitkeep so empty dirs are tracked if required
    try:
        open(os.path.join(OUTPUT_DIR, ".gitkeep"), "a").close()
        open(os.path.join(LOG_DIR, ".gitkeep"), "a").close()
    except Exception:
        pass
    # create or sanitize results.json
    if not os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return
    # if exists, try to load and fix if corrupted or not a list
    try:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("results.json not a list")
    except Exception:
        # back up corrupted file and recreate empty list
        try:
            shutil.copy2(RESULTS_PATH, RESULTS_PATH + ".bak")
        except Exception:
            pass
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

def now_ts():
    return datetime.utcnow().isoformat() + "Z"

def write_log(tool_name, text):
    safe = tool_name.lower().replace(" ", "_")
    path = os.path.join(LOG_DIR, f"{safe}.log")
    try:
        with open(path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"--- {now_ts()} ---\n")
            f.write(text if isinstance(text, str) else str(text))
            f.write("\n\n")
    except Exception:
        pass

def append_result(entry):
    try:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            arr = json.load(f)
            if not isinstance(arr, list):
                arr = []
    except Exception:
        arr = []
    arr.append(entry)
    try:
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(arr, f, indent=2)
    except Exception:
        pass

def run_subprocess_capture(cmd_list, timeout=None):
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "") + (("\nERR:\n" + proc.stderr) if proc.stderr else "")
        ok = proc.returncode == 0
        return ok, out, proc.returncode
    except FileNotFoundError:
        return False, f"Executable not found: {cmd_list[0] if cmd_list else ''}", None
    except subprocess.TimeoutExpired:
        return False, "Timed out", None
    except Exception as e:
        return False, str(e), None

# -------------------------
# Internal tool runner (python scripts under tools/)
# -------------------------
def run_internal_tool_script(name, args=None, timeout=120):
    script = os.path.join(TOOLS_DIR, f"{name}.py")
    if not os.path.exists(script):
        msg = f"Script not found: {script}"
        write_log(name, msg)
        append_result({"tool": name, "time": now_ts(), "success": False, "note": "script_not_found", "output_preview": msg})
        return False, msg, None
    cmd = [sys.executable, script] + (args if args else [])
    ok, out, rc = run_subprocess_capture(cmd, timeout=timeout)
    write_log(name, out)
    append_result({"tool": name, "time": now_ts(), "success": ok, "exit_code": rc, "cmd": " ".join(cmd), "output_preview": (out[:1000] if out else "")})
    return ok, out, rc

# -------------------------
# Orchestrator: run all internal tools then external (if any)
# -------------------------
def run_all(cfg, target_override=None):
    summary = []
    internal = cfg.get("internal_tools", [])
    target = target_override or cfg.get("default_target")
    for t in internal:
        args = []
        if t in ("port_scanner", "banner_grabber", "subdomain_finder"):
            if target:
                args = [str(target)]
        if t == "ping_sweeper" and target:
            base = ".".join(str(target).split(".")[:3]) + "."
            args = [base, "1", "50"]
        ok, out, rc = run_internal_tool_script(t, args=args, timeout=cfg.get("timeout_seconds", 120))
        summary.append({"tool": t, "ok": ok, "exit_code": rc})
    # handle external tools if present (best-effort)
    for friendly, cmd_def in cfg.get("external_tools", {}).items():
        if isinstance(cmd_def, str):
            cmd_list = cmd_def.split()
        elif isinstance(cmd_def, (list, tuple)):
            cmd_list = list(cmd_def)
        else:
            write_log(friendly, "Invalid external tool definition")
            append_result({"tool": friendly, "time": now_ts(), "success": False, "note": "invalid_definition"})
            summary.append({"tool": friendly, "ok": False, "exit_code": None})
            continue
        # if command contains "{target}", replace placeholder
        cmd_list = [str(x).replace("{target}", str(target)) for x in cmd_list]
        ok, out, rc = run_subprocess_capture(cmd_list, timeout=cfg.get("timeout_seconds", 300))
        write_log(friendly, out if out else f"Executed: {' '.join(cmd_list)}")
        append_result({"tool": friendly, "time": now_ts(), "success": ok, "exit_code": rc, "cmd": " ".join(cmd_list), "output_preview": (out[:1000] if out else "")})
        summary.append({"tool": friendly, "ok": ok, "exit_code": rc})
    append_result({"tool": "run_all", "time": now_ts(), "summary": summary})
    return summary

# -------------------------
# Config loader
# -------------------------
def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        # minimal default
        default = {
            "project_name": "CMTL",
            "default_target": "192.168.1.1",
            "timeout_seconds": 300,
            "internal_tools": ["port_scanner", "ping_sweeper", "banner_grabber", "packet_sniffer", "subdomain_finder"],
            "external_tools": {}
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except Exception:
            pass
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"project_name": "CMTL", "default_target": "192.168.1.1", "timeout_seconds": 300, "internal_tools": [], "external_tools": {}}

# -------------------------
# CLI menu (simple)
# -------------------------
def cli_menu(cfg):
    while True:
        print("\nCMTL CLI - Options:")
        print("1) Run single internal tool")
        print("2) Run all (internal + external)")
        print("3) Show tools")
        print("0) Exit")
        choice = input("Choose: ").strip()
        if choice == "0":
            break
        if choice == "1":
            print("Internal tools:", cfg.get("internal_tools", []))
            t = input("Tool name: ").strip()
            if t:
                run_internal_tool_script(t, args=[cfg.get("default_target")])
        elif choice == "2":
            target = input(f"Target (default {cfg.get('default_target')}): ").strip() or cfg.get("default_target")
            print("Running all...")
            print(run_all(cfg, target_override=target))
        elif choice == "3":
            print("Internal:", cfg.get("internal_tools", []))
            print("External:", list(cfg.get("external_tools", {}).keys()))
        else:
            print("Unknown choice.")

# -------------------------
# Minimal GUI launcher (if tkinter available)
# -------------------------
def start_gui(cfg):
    if not TK_AVAILABLE:
        print("Tkinter not installed; use --cli or --run-all")
        return
    root = tk.Tk()
    root.title(cfg.get("project_name", "CMTL"))
    root.geometry("800x480")
    tk.Label(root, text=cfg.get("project_name", "CMTL"), font=("Helvetica", 16, "bold")).pack(pady=8)
    frame = tk.Frame(root)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    tk.Label(frame, text="Internal Tools:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
    r = 1
    for t in cfg.get("internal_tools", []):
        def mk(tool=t):
            return lambda: threading.Thread(target=run_internal_tool_script, args=(tool, [cfg.get("default_target")]), daemon=True).start()
        b = tk.Button(frame, text=tool, width=30, command=mk())
        b.grid(row=r, column=0, pady=4, sticky="w")
        r += 1

    tk.Button(root, text="Run All (sequential)", command=lambda: threading.Thread(target=run_all, args=(cfg,), daemon=True).start()).pack(pady=6)
    tk.Button(root, text="Open output folder", command=lambda: open_output()).pack(pady=2)
    root.mainloop()

def open_output():
    try:
        if os.name == "nt":
            os.startfile(OUTPUT_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", OUTPUT_DIR])
        else:
            subprocess.Popen(["xdg-open", OUTPUT_DIR])
    except Exception as e:
        print("Failed to open output folder:", e)

# -------------------------
# Main
# -------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", action="store_true")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--run-all", action="store_true")
    parser.add_argument("--target", help="override default target")
    args = parser.parse_args()

    ensure_output()
    cfg = load_config()

    if args.run_all:
        summary = run_all(cfg, target_override=args.target)
        print(json.dumps(summary, indent=2))
        return
    if args.gui:
        start_gui(cfg)
        return
    if args.cli:
        cli_menu(cfg)
        return

    # default: GUI if available else CLI
    if TK_AVAILABLE:
        start_gui(cfg)
    else:
        cli_menu(cfg)

if __name__ == "__main__":
    main()
