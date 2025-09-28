#!/usr/bin/env python3

import os
import sys
import json
import shutil
import time
import socket
import subprocess
import platform
import threading
import ctypes
from datetime import datetime

# Optional dependencies
try:
    import requests
except Exception:
    requests = None

try:
    from scapy.all import sniff  # type: ignore
    SCAPY_AVAILABLE = True
except Exception:
    SCAPY_AVAILABLE = False

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, simpledialog
    TK_AVAILABLE = True
except Exception:
    TK_AVAILABLE = False

# ---------------- Paths and output setup ----------------
ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_JSON = os.path.join(OUTPUT_DIR, "results.json")

os.makedirs(LOG_DIR, exist_ok=True)
# ensure results.json exists as an empty list if not present
if not os.path.exists(RESULTS_JSON):
    try:
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump([], f)
    except Exception:
        pass

# ---------------- Default config ----------------
DEFAULT_CONFIG = {
    "project_name": "CyberSec Multi Tool Launcher (CMTL)",
    "default_target": "192.168.1.1",
    "timeout_seconds": 300,
    "tools": {
        "Nmap": ["nmap"],
        "Zenmap": ["zenmap"],
        "Angry IP Scanner": ["ipscan"],
        "Advanced IP Scanner": ["advanced_ip_scanner"],
        "LanSpy": ["lanspy"],
        "OpenVAS": ["gvm-start"],
        "Nessus": ["nessus"],
        "QualysGuard": [],
        "Acunetix": ["acunetix"],
        "Metasploit": ["msfconsole"],
        "Burp Suite": ["burpsuite"],
        "Sparta": ["sparta"],
        "Faraday": ["faraday-client"],
        "Wireshark": ["wireshark"],
        "Maltego": ["maltego"],
        "NetworkMiner": ["NetworkMiner"],
        "Kismet": ["kismet"],
        "Ettercap": ["ettercap"],
        "OWASP ZAP": ["zap.sh"],
        "Magnet AXIOM": [r"C:\Program Files\Magnet Forensics\Magnet AXIOM\AXIOM.exe"]
    },
    # optional explicit paths if user set them
    "paths": {
        "nmap_path": "",
        "metasploit_path": "",
        "burp_path": "",
        "zap_path": "",
        "magnet_axiom_path": ""
    },
    "run_as_admin_required": [
        "scapy"
    ]
}

# ---------------- Load / default config ----------------
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # merge missing defaults
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
                else:
                    if isinstance(v, dict):
                        for subk, subv in v.items():
                            if subk not in cfg[k]:
                                cfg[k][subk] = subv
            return cfg
        except Exception:
            print("Warning: failed to parse config.json — using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2)
        except Exception:
            pass
        return DEFAULT_CONFIG.copy()

CONFIG = load_config()

# ---------------- Utility functions ----------------
def now_ts():
    return datetime.utcnow().isoformat() + "Z"

def is_admin():
    try:
        if os.name == 'nt':
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except Exception:
        return False

def is_executable_available(cmd):
    """
    Accepts:
      - None/"" -> False
      - list like ["nmap"] or ["C:\\path\\to\\nmap.exe"] or single string "nmap"
    Returns True if executable name found in PATH or absolute path exists and is executable.
    """
    if not cmd:
        return False
    exe = cmd[0] if isinstance(cmd, (list, tuple)) else cmd
    if not exe:
        return False
    # absolute path provided
    if os.path.isabs(exe):
        return os.path.exists(exe) and os.access(exe, os.X_OK)
    # check PATH
    return shutil.which(exe) is not None

def write_log(tool_name, text):
    safe = tool_name.lower().replace(" ", "_")
    path = os.path.join(LOG_DIR, f"{safe}.log")
    try:
        with open(path, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"--- {now_ts()} ---\n{text}\n\n")
    except Exception:
        pass

def append_result(result_obj):
    results = []
    try:
        if os.path.exists(RESULTS_JSON):
            with open(RESULTS_JSON, "r", encoding="utf-8") as f:
                results = json.load(f)
                if not isinstance(results, list):
                    results = []
    except Exception:
        results = []
    results.append(result_obj)
    try:
        with open(RESULTS_JSON, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
    except Exception:
        pass

def run_command_capture(cmd_list, timeout=None):
    try:
        completed = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout or CONFIG.get("timeout_seconds", 300))
        out = (completed.stdout or "")
        if completed.stderr:
            out += "\nERR:\n" + completed.stderr
        ok = completed.returncode == 0
        return ok, out
    except FileNotFoundError:
        return False, f"Command not found: {cmd_list[0] if cmd_list else ''}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        return False, str(e)

def launch_detached(cmd_list):
    try:
        if os.name == "nt":
            subprocess.Popen(cmd_list, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            # use nohup-style detach
            subprocess.Popen(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Launched (detached)."
    except Exception as e:
        return False, str(e)

# ---------------- Environment validation ----------------
def validate_environment(cfg):
    missing = []
    tools = cfg.get("tools", {}) or {}
    paths = cfg.get("paths", {}) or {}
    for friendly_name, cmd in tools.items():
        # prefer a path override if exists in paths mapping (common keys like nmap_path)
        key = friendly_name.lower().split()[0] + "_path"  # crude attempt: "Nmap" -> "nmap_path"
        explicit = paths.get(key, "")
        candidate = None
        if explicit:
            candidate = explicit
        else:
            # cmd may be [] or list
            if isinstance(cmd, (list, tuple)) and len(cmd) > 0:
                candidate = cmd
            elif isinstance(cmd, str) and cmd.strip():
                candidate = cmd.strip()
            else:
                candidate = ""  # nothing defined
        if not is_executable_available(candidate):
            missing.append((friendly_name, candidate))
    return missing

missing_tools = validate_environment(CONFIG)
if missing_tools:
    print("\n[WARNING] The following tools appear missing or not executable (name / candidate):")
    for n, c in missing_tools:
        print(f"  - {n}: {c}")
    print("You can still use built-in Python mini-tools. Install external tools or update config.json to enable them.\n")

# ---------------- Mini-tools (built-in Python) ----------------
def mini_port_scanner(target=None, ports=None, timeout=0.5):
    target = target or CONFIG.get("default_target", "127.0.0.1")
    if ports is None:
        ports = [21,22,23,25,53,80,110,139,143,443,445,3306,3389]
    res_lines = []
    for p in ports:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            s.connect((target, p))
            line = f"[OPEN] {target}:{p}"
            print(line)
            res_lines.append(line)
        except Exception:
            line = f"[CLOSED] {target}:{p}"
            res_lines.append(line)
        finally:
            try:
                s.close()
            except Exception:
                pass
    write_log("mini_port_scanner", "\n".join(res_lines))
    append_result({"tool":"mini_port_scanner","target":target,"time":now_ts(),"output_preview":res_lines[:10]})
    return res_lines

def mini_ping_sweep(base_ip=None, start=1, end=20):
    base_ip = base_ip or (".".join(CONFIG.get("default_target","192.168.1.1").split(".")[:3]) + ".")
    up = []
    for i in range(start, end+1):
        ip = base_ip + str(i)
        if os.name == "nt":
            cmd = ["ping", "-n", "1", ip]
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip]
        try:
            res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res == 0:
                up.append(ip)
                print(f"[UP] {ip}")
            else:
                print(f"[DOWN] {ip}")
        except Exception:
            print(f"[ERROR] ping failed for {ip}")
    write_log("mini_ping_sweep", "\n".join(up))
    append_result({"tool":"mini_ping_sweep","base":base_ip,"time":now_ts(),"hosts_up":up})
    return up

def mini_banner_grabber(target=None, port=80, timeout=3):
    target = target or CONFIG.get("default_target","127.0.0.1")
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((target, port))
        try:
            s.send(f"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n".encode())
        except Exception:
            pass
        data = s.recv(4096)
        try:
            s.close()
        except Exception:
            pass
        banner = data.decode(errors="ignore")
        print(banner.strip())
        write_log("mini_banner_grabber", banner)
        append_result({"tool":"mini_banner_grabber","target":f"{target}:{port}","time":now_ts(),"output_preview":banner[:500]})
        return banner
    except Exception as e:
        write_log("mini_banner_grabber", f"Error: {e}")
        print(f"[ERROR] Banner grab failed: {e}")
        return None

def mini_packet_sniffer(count=10, timeout=30):
    if not SCAPY_AVAILABLE:
        print("scapy not installed. Run: pip install scapy")
        return None
    # scapy raw socket operations require elevated privileges on many OSes
    if "scapy" in CONFIG.get("run_as_admin_required", []) and not is_admin():
        print("[INFO] Packet sniffing may require root/administrator privileges. Re-run as admin/root.")
    print(f"Starting packet capture (count={count})...")
    try:
        pkts = sniff(count=count, timeout=timeout)
    except Exception as e:
        print(f"[ERROR] sniff failed: {e}")
        write_log("mini_packet_sniffer", f"Error: {e}")
        return None
    summaries = [p.summary() for p in pkts]
    for s in summaries:
        print(s)
    write_log("mini_packet_sniffer", "\n".join(summaries))
    append_result({"tool":"mini_packet_sniffer","count":len(summaries),"time":now_ts(),"preview":summaries[:10]})
    return pkts

def mini_subdomain_finder(domain, small_wordlist=None):
    if requests is None:
        print("requests not installed. Run: pip install requests")
        return []
    if small_wordlist is None:
        small_wordlist = ["www","mail","ftp","dev","test","stag","api"]
    found = []
    for sub in small_wordlist:
        url = f"http://{sub}.{domain}"
        try:
            r = requests.get(url, timeout=2)
            if r.status_code < 400:
                print(f"[FOUND] {url} ({r.status_code})")
                found.append(url)
        except Exception:
            pass
    write_log("mini_subdomain_finder", "\n".join(found))
    append_result({"tool":"mini_subdomain_finder","domain":domain,"time":now_ts(),"found":found})
    return found

# ---------------- External tool runners ----------------
def run_tool_cli(tool_name, extra_args=None, capture=True):
    cmd = CONFIG.get("tools", {}).get(tool_name)
    if not cmd:
        append_result({"tool":tool_name,"status":"no-launcher","time":now_ts(),"note":"No local launcher defined"})
        return False, "No local launcher defined for this tool."
    # try override path mapping if present
    paths = CONFIG.get("paths", {})
    key = tool_name.lower().split()[0] + "_path"
    explicit = paths.get(key, "")
    final_cmd = None
    if explicit:
        # if explicit is a string, try to use it as the executable
        if isinstance(explicit, str) and explicit:
            final_cmd = [explicit] + (extra_args or [])
    if final_cmd is None:
        # cmd may be list or string
        if isinstance(cmd, (list, tuple)):
            final_cmd = list(cmd) + (extra_args or [])
        else:
            final_cmd = [cmd] + (extra_args or [])
    if not is_executable_available(final_cmd):
        return False, f"Executable not found: {final_cmd[0]}"
    print(f"Running (capture) → {' '.join(final_cmd)}")
    ok, out = run_command_capture(final_cmd)
    write_log(tool_name, out or "")
    append_result({"tool":tool_name,"cmd":" ".join(final_cmd),"time":now_ts(),"success":ok,"output_preview":(out[:200] if out else "")})
    return ok, out

def launch_tool_gui(tool_name):
    cmd = CONFIG.get("tools", {}).get(tool_name)
    if not cmd:
        return False, "No local launcher defined."
    # use path overrides if provided
    paths = CONFIG.get("paths", {})
    key = tool_name.lower().split()[0] + "_path"
    explicit = paths.get(key, "")
    final_cmd = None
    if explicit:
        final_cmd = [explicit]
    else:
        if isinstance(cmd, (list, tuple)):
            final_cmd = list(cmd)
        else:
            final_cmd = [cmd]
    if not is_executable_available(final_cmd):
        return False, f"'{final_cmd[0]}' not found in PATH."
    ok, msg = launch_detached(final_cmd)
    append_result({"tool":tool_name,"time":now_ts(),"launched":ok,"error":None if ok else msg})
    return ok, msg

def run_all_cli(tool_list=None):
    tool_list = tool_list or list(CONFIG.get("tools", {}).keys())
    summary = []
    for t in tool_list:
        print(f"\n=== Running {t} (CLI capture) ===")
        ok, out = run_tool_cli(t)
        summary.append({"tool":t,"success":ok,"time":now_ts()})
        time.sleep(0.5)
    append_result({"tool":"run_all_cli","time":now_ts(),"summary":summary})
    return summary

# ---------------- helper: open output folder ----------------
def open_output_folder():
    try:
        if os.name == "nt":
            os.startfile(OUTPUT_DIR)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", OUTPUT_DIR])
        else:
            subprocess.Popen(["xdg-open", OUTPUT_DIR])
    except Exception as e:
        print(f"Failed to open output folder: {e}")

# ---------------- attempt_install (simple helper) ----------------
def attempt_install(tool_name):
    """
    Best-effort installer: for Debian/Ubuntu, try apt install <package_name>
    This is a convenience, not guaranteed. Returns (ok, message).
    """
    # map friendly names to apt package names (best-effort)
    mapping = {
        "Nmap": "nmap",
        "Wireshark": "wireshark",
        "Metasploit": "metasploit-framework",
        "OWASP ZAP": "owasp-zap",
        "Burp Suite": "",  # commercial - skip
    }
    pkg = mapping.get(tool_name, "")
    if not pkg:
        return False, "No automated installer mapping for this tool."
    if detect_os_family() != "linux":
        return False, "Auto-install supported only on Linux (apt) in this script."
    try:
        print(f"[INFO] Attempting to install {pkg} via apt (you will be prompted for sudo)...")
        subprocess.check_call(["sudo", "apt", "update"])
        subprocess.check_call(["sudo", "apt", "install", "-y", pkg])
        return True, f"{pkg} installed (or already present)."
    except Exception as e:
        return False, f"Auto-install failed: {e}"

# ---------------- OS detection ----------------
def detect_os_family():
    plat = sys.platform
    if plat.startswith("linux"):
        return "linux"
    if plat == "darwin":
        return "mac"
    if plat in ("win32", "cygwin"):
        return "windows"
    return "other"

OS_FAMILY = detect_os_family()

# ---------------- Tkinter GUI ----------------
def simple_input(prompt, default=""):
    if not TK_AVAILABLE:
        return input(f"{prompt} [{default}]: ") or default
    return simpledialog.askstring(prompt, f"{prompt} (default {default})") or default

def start_gui():
    if not TK_AVAILABLE:
        print("Tkinter not available.")
        return

    root = tk.Tk()
    root.title(CONFIG.get("project_name", "CMTL"))
    root.geometry("900x600")

    frame_top = ttk.Frame(root, padding=10)
    frame_top.pack(fill="x")
    ttk.Label(frame_top, text=CONFIG.get("project_name"), font=("Helvetica", 16, "bold")).pack(side="left")
    ttk.Label(frame_top, text=f"Default target: {CONFIG.get('default_target')}", foreground="gray").pack(side="right")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True, padx=10, pady=10)

    tools_by_cat = {
        "Network Scanners": ["Nmap","Zenmap","Angry IP Scanner","Advanced IP Scanner","LanSpy"],
        "Vulnerability": ["OpenVAS","Nessus","QualysGuard","Acunetix","OWASP ZAP"],
        "Pentesting": ["Metasploit","Burp Suite","Sparta","Faraday","Acunetix"],
        "Forensics": ["Wireshark","Maltego","NetworkMiner","Kismet","Ettercap","Magnet AXIOM"]
    }

    def make_tool_button(frame, name):
        def on_click():
            ok, msg = launch_tool_gui(name)
            if ok:
                messagebox.showinfo("Launched", f"{name} launched.")
            else:
                if "not found" in (msg or "").lower() or "not executable" in (msg or "").lower():
                    if messagebox.askyesno("Not found", f"{name} not found. Attempt install?"):
                        ok2, m2 = attempt_install(name)
                        messagebox.showinfo("Install", f"{'OK' if ok2 else 'FAIL'}: {m2}")
                else:
                    messagebox.showerror("Error", msg)
        b = ttk.Button(frame, text=name, width=25, command=on_click)
        return b

    for cat, tool_names in tools_by_cat.items():
        page = ttk.Frame(notebook)
        notebook.add(page, text=cat)
        r = c = 0
        for tname in tool_names:
            btn = make_tool_button(page, tname)
            btn.grid(row=r, column=c, padx=6, pady=6)
            c += 1
            if c >= 3:
                c = 0
                r += 1

    # Mini-tools tab
    mini_page = ttk.Frame(notebook)
    notebook.add(mini_page, text="Mini Tools")
    ttk.Label(mini_page, text="Built-in Python mini tools (run inside launcher)").pack(anchor="w", pady=6)
    ttk.Button(mini_page, text="Port Scanner", command=lambda: threading.Thread(target=mini_port_scanner, args=(simple_input("Target", CONFIG.get("default_target")), None), daemon=True).start()).pack(padx=6, pady=6, anchor="w")
    ttk.Button(mini_page, text="Ping Sweep", command=lambda: threading.Thread(target=mini_ping_sweep, args=(simple_input("Base IP", ".".join(CONFIG.get("default_target").split(".")[:3]) + "."),1,20), daemon=True).start()).pack(padx=6, pady=6, anchor="w")
    ttk.Button(mini_page, text="Banner Grabber", command=lambda: threading.Thread(target=mini_banner_grabber, args=(simple_input("Host", CONFIG.get("default_target")), int(simple_input("Port", "80") or "80")), daemon=True).start()).pack(padx=6, pady=6, anchor="w")
    ttk.Button(mini_page, text="Packet Sniffer (scapy)", command=lambda: threading.Thread(target=mini_packet_sniffer, args=(int(simple_input("Packet count", "10") or "10"), int(simple_input("Timeout sec", "30") or "30")), daemon=True).start()).pack(padx=6, pady=6, anchor="w")
    ttk.Button(mini_page, text="Subdomain Finder", command=lambda: threading.Thread(target=mini_subdomain_finder, args=(simple_input("Domain (example.com)","example.com"), None), daemon=True).start()).pack(padx=6, pady=6, anchor="w")

    bottom = ttk.Frame(root, padding=10)
    bottom.pack(fill="x", side="bottom")
    ttk.Button(bottom, text="Run All (sequential - captures output)", command=lambda: threading.Thread(target=run_all_cli, daemon=True).start()).pack(side="left", padx=6)
    ttk.Button(bottom, text="Open output folder", command=open_output_folder).pack(side="right", padx=6)

    root.mainloop()

# ---------------- CLI Menu ----------------
def cli_menu():
    while True:
        print("\n=== CMTL CLI Menu ===")
        print("1) Run a single tool (capture output)")
        print("2) Run built-in mini-tool")
        print("3) Run all tools (sequential, CLI capture)")
        print("4) Show available tools")
        print("5) Auto-install helper (best-effort for Linux/apt)")
        print("0) Exit")
        sel = input("Select: ").strip()
        if sel == "0":
            break
        elif sel == "1":
            tools = list(CONFIG.get("tools", {}).keys())
            for i,t in enumerate(tools, start=1):
                print(f"{i}) {t}")
            choice = input("Select tool (num): ").strip()
            try:
                idx = int(choice)-1
                if not (0 <= idx < len(tools)):
                    raise ValueError
                tool_name = tools[idx]
            except Exception:
                print("Invalid selection.")
                continue
            extra = input("Extra args (space-separated) or Enter: ").strip().split()
            extra_args = extra if extra and extra != [''] else None
            ok, out = run_tool_cli(tool_name, extra_args=extra_args)
            print("OK" if ok else "FAIL")
            if isinstance(out, str):
                print(out[:1000])
        elif sel == "2":
            print("Mini tools: 1) Port scanner 2) Ping sweep 3) Packet sniffer 4) Banner grabber 5) Subdomain finder")
            m = input("Select mini-tool: ").strip()
            if m == "1":
                host = input(f"Target (default {CONFIG.get('default_target')}): ").strip() or CONFIG.get("default_target")
                ports_in = input("Ports (comma) or Enter for defaults: ").strip()
                try:
                    ports = [int(p.strip()) for p in ports_in.split(",")] if ports_in else None
                except Exception:
                    ports = None
                mini_port_scanner(host, ports)
            elif m == "2":
                base = input("Base IP (e.g. 192.168.1.): ").strip() or (".".join(CONFIG.get("default_target").split(".")[:3]) + ".")
                try:
                    s = int(input("Start (default 1): ").strip() or "1")
                    e = int(input("End (default 20): ").strip() or "20")
                except Exception:
                    s, e = 1, 20
                mini_ping_sweep(base, s, e)
            elif m == "3":
                if not SCAPY_AVAILABLE:
                    print("Scapy not installed or import failed. Run: pip install scapy")
                    continue
                if "scapy" in CONFIG.get("run_as_admin_required", []) and not is_admin():
                    print("[INFO] Packet capture may require elevated privileges. Re-run as root/administrator.")
                try:
                    cnt = int(input("Packet count (default 10): ").strip() or "10")
                    tout = int(input("Timeout seconds (default 30): ").strip() or "30")
                except Exception:
                    cnt, tout = 10, 30
                mini_packet_sniffer(count=cnt, timeout=tout)
            elif m == "4":
                host = input(f"Host (default {CONFIG.get('default_target')}): ").strip() or CONFIG.get("default_target")
                try:
                    port = int(input("Port (default 80): ").strip() or "80")
                except Exception:
                    port = 80
                mini_banner_grabber(host, port)
            elif m == "5":
                dom = input("Domain (example.com): ").strip()
                if not dom:
                    print("Invalid domain.")
                else:
                    mini_subdomain_finder(dom)
            else:
                print("Invalid selection.")
        elif sel == "3":
            run_all_cli()
        elif sel == "4":
            print("Available tools (from config):")
            for t in CONFIG.get("tools", {}).keys():
                print(" - " + t)
        elif sel == "5":
            tools = list(CONFIG.get("tools", {}).keys())
            for i,t in enumerate(tools, start=1):
                print(f"{i}) {t}")
            choice = input("Select tool to auto-install (num) or 'all': ").strip()
            if choice.lower() == "all":
                for t in tools:
                    ok, msg = attempt_install(t)
                    print(f"{t}: {'OK' if ok else 'FAIL'} - {msg}")
            else:
                try:
                    idx = int(choice)-1
                    t = tools[idx]
                    ok, msg = attempt_install(t)
                    print(f"{t}: {'OK' if ok else 'FAIL'} - {msg}")
                except Exception:
                    print("Invalid selection.")
        else:
            print("Unknown option.")

# ---------------- CLI arguments and main ----------------
def print_help():
    print("Usage: python tool_launcher.py [--gui|--cli]")
    print("If no argument provided, will try GUI if available, else CLI.")

if __name__ == "__main__":
    try:
        arg = sys.argv[1] if len(sys.argv) > 1 else ""
    except Exception:
        arg = ""
    if arg in ("-h", "--help"):
        print_help()
        sys.exit(0)

    if arg == "--cli":
        cli_menu()
    elif arg == "--gui":
        start_gui()
    else:
        # prefer GUI if available
        if TK_AVAILABLE:
            start_gui()
        else:
            print("Tkinter GUI not available; falling back to CLI.")
            cli_menu()
