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

### Paths and output setup
ROOT = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(ROOT, "config.json")
OUTPUT_DIR = os.path.join(ROOT, "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_JSON = os.path.join(OUTPUT_DIR, "results.json")

os.makedirs(LOG_DIR, exist_ok=True)

### Default config
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
    }
}

### Load / default config
def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            # ensure all default keys exist
            for k, v in DEFAULT_CONFIG.items():
                if k not in cfg:
                    cfg[k] = v
                elif isinstance(v, dict):
                    for subk, subv in v.items():
                        if subk not in cfg[k]:
                            cfg[k][subk] = subv
            return cfg
        except Exception:
            print("Warning: failed to parse config.json — using defaults.")
            return DEFAULT_CONFIG.copy()
    else:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CONFIG, f, indent=2)
        return DEFAULT_CONFIG.copy()

CONFIG = load_config()

### Utility functions
def now_ts():
    return datetime.utcnow().isoformat() + "Z"

def is_executable_available(cmd):
    if not cmd:
        return False
    exe = cmd[0] if isinstance(cmd, (list, tuple)) else cmd
    if os.path.sep in exe and os.path.exists(exe):
        return True
    return shutil.which(exe) is not None

def write_log(tool_name, text):
    path = os.path.join(LOG_DIR, f"{tool_name.lower().replace(' ', '_')}.log")
    with open(path, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"--- {now_ts()} ---\n{text}\n\n")

def append_result(result_obj):
    results = []
    if os.path.exists(RESULTS_JSON):
        try:
            with open(RESULTS_JSON, "r", encoding="utf-8") as f:
                results = json.load(f)
                if not isinstance(results, list):
                    results = []
        except Exception:
            results = []
    results.append(result_obj)
    with open(RESULTS_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

def run_command_capture(cmd_list, timeout=None):
    try:
        completed = subprocess.run(cmd_list, capture_output=True, text=True, timeout=timeout or CONFIG.get("timeout_seconds", 300))
        out = (completed.stdout or "") + ("\nERR:\n" + (completed.stderr or "") if completed.stderr else "")
        ok = completed.returncode == 0
        return ok, out
    except FileNotFoundError:
        return False, f"Command not found: {cmd_list[0]}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out."
    except Exception as e:
        return False, str(e)

def launch_detached(cmd_list):
    try:
        if os.name == "nt":
            subprocess.Popen(cmd_list, creationflags=subprocess.CREATE_NEW_CONSOLE)
        else:
            subprocess.Popen(cmd_list, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "Launched (detached)."
    except Exception as e:
        return False, str(e)

### OS detection
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

### Built-in mini-tools
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
            s.close()
    write_log("mini_port_scanner", "\n".join(res_lines))
    append_result({"tool":"mini_port_scanner","target":target,"time":now_ts(),"output_preview":res_lines[:10]})
    return res_lines

def mini_ping_sweep(base_ip=None, start=1, end=20):
    base_ip = base_ip or ".".join(CONFIG.get("default_target","192.168.1.1").split(".")[:3]) + "."
    up = []
    for i in range(start, end+1):
        ip = base_ip + str(i)
        if os.name == "nt":
            cmd = ["ping", "-n", "1", ip]
        else:
            cmd = ["ping", "-c", "1", "-W", "1", ip]
        res = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res == 0:
            up.append(ip)
            print(f"[UP] {ip}")
        else:
            print(f"[DOWN] {ip}")
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
        s.close()
        banner = data.decode(errors="ignore")
        print(banner.strip())
        write_log("mini_banner_grabber", banner)
        append_result({"tool":"mini_banner_grabber","target":f"{target}:{port}","time":now_ts(),"output_preview":banner[:500]})
        return banner
    except Exception as e:
        write_log("mini_banner_grabber", f"Error: {e}")
        return None

def mini_packet_sniffer(count=10, timeout=30):
    if not SCAPY_AVAILABLE:
        print("scapy not installed. Run: pip install scapy")
        return None
    print(f"Starting packet capture (count={count})...")
    pkts = sniff(count=count, timeout=timeout)
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

### External tool runners
def run_tool_cli(tool_name, extra_args=None, capture=True):
    cmd = CONFIG["tools"].get(tool_name)
    if not cmd:
        append_result({"tool":tool_name,"status":"no-launcher","time":now_ts(),"note":"No local launcher defined"})
        return False, "No local launcher defined for this tool."

    if not is_executable_available(cmd):
        return False, f"Executable not found: {cmd[0]}"

    final_cmd = cmd + (extra_args or [])
    print(f"Running (capture) → {' '.join(final_cmd)}")
    ok, out = run_command_capture(final_cmd)
    write_log(tool_name, out)
    append_result({"tool":tool_name,"cmd":" ".join(final_cmd),"time":now_ts(),"success":ok,"output_preview":(out[:200] if out else "")})
    return ok, out

def launch_tool_gui(tool_name):
    cmd = CONFIG["tools"].get(tool_name)
    if not cmd:
        return False, "No local launcher defined."
    if not is_executable_available(cmd):
        return False, f"'{cmd[0]}' not found in PATH."
    ok, msg = launch_detached(cmd)
    append_result({"tool":tool_name,"time":now_ts(),"launched":ok,"error":None if ok else msg})
    return ok, msg

### Run all CLI
def run_all_cli(tool_list=None):
    tool_list = tool_list or list(CONFIG["tools"].keys())
    summary = []
    for t in tool_list:
        print(f"\n=== Running {t} (CLI capture) ===")
        ok, out = run_tool_cli(t)
        summary.append({"tool":t,"success":ok,"time":now_ts()})
        time.sleep(0.5)
    append_result({"tool":"run_all_cli","time":now_ts(),"summary":summary})
    return summary

### Cross-platform folder opener
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

### Tkinter GUI
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
                if "not found" in msg.lower():
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

    bottom = ttk.Frame(root, padding=10)
    bottom.pack(fill="x", side="bottom")
    ttk.Button(bottom, text="Run All (sequential - captures output)", command=lambda: threading.Thread(target=run_all_cli, daemon=True).start()).pack(side="left", padx=6)
    ttk.Button(bottom, text="Open output folder", command=open_output_folder).pack(side="right", padx=6)

    root.mainloop()

### CLI Menu
def cli_menu():
    while True:
        print("\n=== CMTL CLI Menu ===")
        print("1) Run a single tool (capture output)")
        print("2) Run built-in mini-tool")
        print("3) Run all tools (sequential, CLI capture)")
        print("4) Show available tools")
        print("5) Auto-install helper")
        print("0) Exit")
        sel = input("Select: ").strip()
        if sel == "0":
            break
        elif sel == "1":
            tools = list(CONFIG["tools"].keys())
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
            ok, out = run_tool_cli(tool_name, extra_args=extra if extra and extra != [''] else None)
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
                base = input("Base IP (e.g. 192.168.1.): ").strip() or ".".join(CONFIG.get("default_target").split(".")[:3
