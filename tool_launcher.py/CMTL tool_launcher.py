#!/usr/bin/env python3
"""tool_launcher.py
CyberSec Multi-Tool Launcher (CMTL) - full launcher (CLI + simple GUI)
Features:
 - Reads config.json
 - Ensures output/ and output/logs/ exist (creates them)
 - Runs internal mini-tools (tools/*.py) and configured external commands (if available)
 - Captures stdout/stderr, writes per-tool logs (output/logs/<tool>.log)
 - Appends structured run records to output/results.json
 - Supports: --cli, --gui, --run-all
"""

import os
import sys
import json
import subprocess
import shutil
import argparse
import threading
from datetime import datetime

# Try to import optional libraries (not fatal)
try:
    import tkinter as tk
    from tkinter import messagebox, simpledialog, ttk
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_PATH = os.path.join(OUTPUT_DIR, "results.json")
TOOLS_DIR = os.path.join(ROOT, "tools")

# Ensure directories and initial files
def ensure_output():
    os.makedirs(LOG_DIR, exist_ok=True)
    # Git keep files so empty dirs are tracked
    open(os.path.join(OUTPUT_DIR, ".gitkeep"), "a").close()
    open(os.path.join(LOG_DIR, ".gitkeep"), "a").close()
    if not os.path.exists(RESULTS_PATH):
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)

ensure_output()

# Utilities
def now_ts():
    return datetime.utcnow().isoformat() + "Z"

def write_log(tool_name, text):
    safe = tool_name.lower().replace(" ", "_")
    path = os.path.join(LOG_DIR, f"{safe}.log")
    try:
        with open(path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"--- {now_ts()} ---\n{text}\n\n")
    except Exception as e:
        print(f"[WARN] Could not write log for {tool_name}: {e}")

def append_result(entry):
    try:
        with open(RESULTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, list):
                data = []
    except Exception:
        data = []
    data.append(entry)
    try:
        with open(RESULTS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[WARN] Could not append result: {e}")

def is_executable_available(cmd):
    """
    Accepts a string or list; checks presence on PATH or absolute path existence.
    """
    if not cmd:
        return False
    if isinstance(cmd, (list, tuple)):
        exe = cmd[0]
    else:
        exe = cmd
    if not exe:
        return False
    if os.path.isabs(exe):
        return os.path.exists(exe) and os.access(exe, os.X_OK)
    return shutil.which(exe) is not None

def run_subprocess_capture(cmd_list, timeout=None):
    """
    Runs command (list) and returns (success_bool, stdout+stderr_str, returncode)
    """
    try:
        proc = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout)
        out = (proc.stdout or "") + ("\nERR:\n" + proc.stderr if proc.stderr else "")
        ok = proc.returncode == 0
        return ok, out, proc.returncode
    except FileNotFoundError:
        return False, f"Executable not found: {cmd_list[0] if cmd_list else ''}", None
    except subprocess.TimeoutExpired:
        return False, "Timed out", None
    except Exception as e:
        return False, str(e), None

# -------------------------
# Internal mini-tools runner (calls python scripts in tools/)
# -------------------------
def run_internal_tool_script(tool_script_name, args=None, timeout=120):
    """
    Executes: python tools/<tool_script_name>.py [args...]
    tool_script_name without .py (e.g., "port_scanner")
    """
    script = os.path.join(TOOLS_DIR, f"{tool_script_name}.py")
    if not os.path.exists(script):
        msg = f"Script not found: {script}"
        write_log(tool_script_name, msg)
        append_result({
            "tool": tool_script_name,
            "time": now_ts(),
            "success": False,
            "note": "script_not_found",
            "output_preview": msg
        })
        return False, msg, None

    cmd = [sys.executable, script] + (args if args else [])
    ok, out, rc = run_subprocess_capture(cmd, timeout=timeout)
    write_log(tool_script_name, out)
    append_result({
        "tool": tool_script_name,
        "time": now_ts(),
        "success": ok,
        "exit_code": rc,
        "cmd": " ".join(cmd),
        "output_preview": (out[:1000] if out else "")
    })
    return ok, out, rc

# -------------------------
# External tool runner (executables installed on system) - best-effort
# -------------------------
def run_external_tool(tool_name, cmd_def, timeout=300):
    """
    cmd_def may be:
      - list: ["nmap", "-A"]
      - string: "nmap -A"
      - absolute path to exe
    """
    if isinstance(cmd_def, str):
        cmd_list = cmd_def.split()
    elif isinstance(cmd_def, (list, tuple)):
        cmd_list = list(cmd_def)
    else:
        append_result({
            "tool": tool_name,
            "time": now_ts(),
            "success": False,
            "note": "invalid_cmd",
            "output_preview": ""
        })
        return False, "Invalid command specified", None

    # check executable available
    if not is_executable_available(cmd_list):
        msg = f"Executable not found: {cmd_list[0]}"
        write_log(tool_name, msg)
        append_result({
            "tool": tool_name,
            "time": now_ts(),
            "success": False,
            "note": "exe_not_found",
            "cmd": " ".join(cmd_list),
            "output_preview": msg
        })
        return False, msg, None

    ok, out, rc = run_subprocess_capture(cmd_list, timeout=timeout)
    write_log(tool_name, out)
    append_result({
        "tool": tool_name,
        "time": now_ts(),
        "success": ok,
        "exit_code": rc,
        "cmd": " ".join(cmd_list),
        "output_preview": (out[:1000] if out else "")
    })
    return ok, out, rc

# -------------------------
# Orchestrator: run all (internal + external)
# -------------------------
def run_all_sequential(config, target_override=None):
    """
    Runs all configured tools sequentially:
     - first internal mini-tools (config['internal_tools'])
     - then external tools (config['external_tools'] mapping)
    Returns a summary list.
    """
    summary = []
    # 1) internal tools
    internal = config.get("internal_tools", [])
    for t in internal:
        # some internal tools accept target; we pass default target from config or override
        target = target_override or config.get("default_target")
        args = []
        if t in ("port_scanner", "banner_grabber", "subdomain_finder"):
            # pass target as first arg
            if target:
                args = [str(target)]
        # ping_sweeper wants base like 192.168.1.
        if t == "ping_sweeper" and target:
            base = ".".join(str(target).split(".")[:3]) + "."
            args = [base, "1", "50"]
        ok, out, rc = run_internal_tool_script(t, args=args, timeout=config.get("timeout_seconds", 120))
        summary.append({"tool": t, "ok": ok, "exit_code": rc})
    # 2) external tools
    external = config.get("external_tools", {})
    for friendly_name, cmd_def in external.items():
        ok, out, rc = run_external_tool(friendly_name, cmd_def, timeout=config.get("timeout_seconds", 300))
        summary.append({"tool": friendly_name, "ok": ok, "exit_code": rc})
    # record run_all summary
    append_result({"tool": "run_all", "time": now_ts(), "summary": summary})
    return summary

# -------------------------
# Load config with safe defaults
# -------------------------
def load_config(path=CONFIG_PATH):
    if not os.path.exists(path):
        # create a default config if missing
        default = {
            "project_name": "CyberSec Multi Tool Launcher (CMTL)",
            "default_target": "192.168.1.1",
            "timeout_seconds": 300,
            "internal_tools": ["port_scanner", "ping_sweeper", "banner_grabber", "packet_sniffer", "subdomain_finder"],
            "external_tools": {
                # friendly name : command (list or string)
                "Nmap": ["nmap", "-F", "127.0.0.1"],
                "Wireshark": ["wireshark"],
                "Metasploit": ["msfconsole", "-q"]
            }
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except Exception:
            pass
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            return cfg
    except Exception:
        print("[WARN] Invalid config.json, using safe defaults.")
        return {
            "project_name": "CyberSec Multi Tool Launcher (CMTL)",
            "default_target": "192.168.1.1",
            "timeout_seconds": 300,
            "internal_tools": ["port_scanner", "ping_sweeper", "banner_grabber", "packet_sniffer", "subdomain_finder"],
            "external_tools": {}
        }

# -------------------------
# CLI menu
# -------------------------
def cli_menu(cfg):
    while True:
        print("\n=== CMTL CLI ===")
        print("1) Run single internal tool")
        print("2) Run single external tool (if present)")
        print("3) Run all (internal + external) sequentially")
        print("4) Show available tools")
        print("0) Exit")
        choice = input("Select: ").strip()
        if choice == "0":
            break
        elif choice == "1":
            print("Internal tools:", cfg.get("internal_tools", []))
            t = input("Tool name: ").strip()
            if t:
                run_internal_tool_script(t, args=[cfg.get("default_target")])
        elif choice == "2":
            print("External tools:", list(cfg.get("external_tools", {}).keys()))
            t = input("External tool friendly name: ").strip()
            if t and t in cfg.get("external_tools", {}):
                run_external_tool(t, cfg["external_tools"][t])
        elif choice == "3":
            target = input(f"Target (default {cfg.get('default_target')}): ").strip() or cfg.get("default_target")
            print("Running all -- this may take time. Check output/logs/ for logs.")
            summary = run_all_sequential(cfg, target_override=target)
            print("Summary:", summary)
        elif choice == "4":
            print("Internal tools:", cfg.get("internal_tools", []))
            print("External tools:", list(cfg.get("external_tools", {}).keys()))
        else:
            print("Unknown choice.")

# -------------------------
# Simple Tkinter GUI (keeps it minimal)
# -------------------------
def start_gui(cfg):
    if not TK_AVAILABLE:
        print("Tkinter not available. Use --cli or --run-all.")
        return
    root = tk.Tk()
    root.title(cfg.get("project_name", "CMTL"))
    root.geometry("800x520")
    tk.Label(root, text=cfg.get("project_name", "CMTL"), font=("Arial", 16, "bold")).pack(pady=8)
    frame = tk.Frame(root)
    frame.pack(padx=10, pady=10, fill="both", expand=True)
    # Internal tools buttons
    lbl_int = tk.Label(frame, text="Internal Mini-Tools", font=("Arial", 12, "bold"))
    lbl_int.grid(row=0, column=0, sticky="w", pady=(0,6))
    r = 1
    for t in cfg.get("internal_tools", []):
        def make_cmd(tool_name):
            return lambda: threading.Thread(target=run_internal_tool_script, args=(tool_name, [cfg.get("default_target")]), daemon=True).start()
        b = tk.Button(frame, text=t, width=28, command=make_cmd(t))
        b.grid(row=r, column=0, padx=6, pady=4, sticky="w")
        r += 1
    # External tools
    lbl_ext = tk.Label(frame, text="External Tools (launch if installed)", font=("Arial", 12, "bold"))
    lbl_ext.grid(row=0, column=1, sticky="w", padx=(20,0))
    r = 1
    for friendly, cmd in cfg.get("external_tools", {}).items():
        def make_cmd2(fn=friendly, cd=cmd):
            return lambda: threading.Thread(target=run_external_tool, args=(fn, cd), daemon=True).start()
        b = tk.Button(frame, text=friendly, width=28, command=make_cmd2())
        b.grid(row=r, column=1, padx=6, pady=4, sticky="w")
        r += 1

    # Bottom controls
    bottom = tk.Frame(root)
    bottom.pack(fill="x", padx=10, pady=8)
    tk.Button(bottom, text="Run All (sequential)", command=lambda: threading.Thread(target=run_all_sequential, args=(cfg,), daemon=True).start()).pack(side="left")
    tk.Button(bottom, text="Open output folder", command=lambda: open_output_folder()).pack(side="right")
    root.mainloop()

def open_output_folder():
    try:
        if os.name == "nt":
            os.startfile(OUTPUT_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", OUTPUT_DIR])
        else:
            subprocess.Popen(["xdg-open", OUTPUT_DIR])
    except Exception as e:
        print(f"[WARN] Could not open output folder: {e}")

# -------------------------
# Entry point
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="CMTL - CyberSec Multi-Tool Launcher")
    parser.add_argument("--cli", action="store_true", help="Start in CLI mode")
    parser.add_argument("--gui", action="store_true", help="Start GUI (Tkinter)")
    parser.add_argument("--run-all", action="store_true", help="Run all internal+external tools sequentially (one-line command)")
    parser.add_argument("--target", help="Override default target for internal tools")
    args = parser.parse_args()

    cfg = load_config()

    # ensure output folder
    ensure_output()

    if args.run_all:
        target = args.target or cfg.get("default_target")
        print(f"[INFO] Running all tools sequentially against target: {target}")
        summary = run_all_sequential(cfg, target_override=target)
        print("Run finished. Summary:")
        print(json.dumps(summary, indent=2))
        return

    if args.gui:
        start_gui(cfg)
        return

    if args.cli:
        cli_menu(cfg)
        return

    # default: try GUI if possible, else CLI
    if TK_AVAILABLE:
        start_gui(cfg)
    else:
        cli_menu(cfg)

if __name__ == "__main__":
    main()
