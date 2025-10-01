import os
import sys
import json
import subprocess
import socket
import logging
from datetime import datetime
import requests
from scapy.all import sniff, IP, TCP, UDP
import tkinter as tk
from tkinter import messagebox

# ========================
# Setup directories
# ========================
OUTPUT_DIR = "output"
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
RESULTS_FILE = os.path.join(OUTPUT_DIR, "results.json")
CONFIG_FILE = "config.json"

os.makedirs(LOG_DIR, exist_ok=True)

# ========================
# Logging
# ========================
logging.basicConfig(
    filename=os.path.join(LOG_DIR, "launcher.log"),
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ========================
# Config loader
# ========================
def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Config load error: {e}")
            return {}
    return {}

CONFIG = load_config()

# ========================
# JSON Results Manager
# ========================
def write_results(tool_name, result):
    results = []
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as f:
                results = json.load(f)
            if not isinstance(results, list):
                results = []
        except Exception:
            results = []
    results.append({"tool": tool_name, "result": result, "timestamp": datetime.now().isoformat()})
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=4)

# ========================
# External Tool Runner
# ========================
def run_external_tool(command, tool_name):
    try:
        logging.info(f"Running {tool_name}: {command}")
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        output = result.stdout if result.stdout else result.stderr
        log_path = os.path.join(LOG_DIR, f"{tool_name.lower().replace(' ', '_')}.log")
        with open(log_path, "a") as log_file:
            log_file.write(f"\n\n===== {datetime.now()} =====\n")
            log_file.write(output)
        write_results(tool_name, output[:200])  # store summary
        print(f"[+] {tool_name} executed. Logs saved: {log_path}")
    except Exception as e:
        logging.error(f"Error running {tool_name}: {e}")
        print(f"[!] Failed to run {tool_name}")

# ========================
# Internal Tools
# ========================
def port_scanner(target, ports=[21,22,23,25,53,80,110,443]):
    open_ports = []
    for port in ports:
        try:
            s = socket.socket()
            s.settimeout(0.5)
            s.connect((target, port))
            open_ports.append(port)
            s.close()
        except:
            continue
    result = f"Open ports on {target}: {open_ports}" if open_ports else "No common ports open."
    log_path = os.path.join(LOG_DIR, "port_scanner.log")
    with open(log_path, "a") as log_file:
        log_file.write(f"\n\n===== {datetime.now()} =====\n{result}")
    write_results("Port Scanner", result)
    print(result)

def ping_sweeper(subnet="192.168.1."):
    live_hosts = []
    for i in range(1, 5):
        host = f"{subnet}{i}"
        response = os.system(f"ping -c 1 {host} > /dev/null 2>&1")
        if response == 0:
            live_hosts.append(host)
    result = f"Live hosts: {live_hosts}" if live_hosts else "No hosts alive."
    log_path = os.path.join(LOG_DIR, "ping_sweeper.log")
    with open(log_path, "a") as log_file:
        log_file.write(f"\n\n===== {datetime.now()} =====\n{result}")
    write_results("Ping Sweeper", result)
    print(result)

def banner_grabber(target, port=80):
    try:
        s = socket.socket()
        s.settimeout(2)
        s.connect((target, port))
        s.send(b"HEAD / HTTP/1.1\r\nHost: example.com\r\n\r\n")
        response = s.recv(4096).decode(errors="ignore")
        s.close()
        result = response[:200]
    except Exception as e:
        result = f"Failed: {e}"
    log_path = os.path.join(LOG_DIR, "banner_grabber.log")
    with open(log_path, "a") as log_file:
        log_file.write(f"\n\n===== {datetime.now()} =====\n{result}")
    write_results("Banner Grabber", result)
    print(result)

def packet_sniffer(count=5):
    packets = sniff(count=count)
    summary = [pkt.summary() for pkt in packets]
    result = "\n".join(summary)
    log_path = os.path.join(LOG_DIR, "packet_sniffer.log")
    with open(log_path, "a") as log_file:
        log_file.write(f"\n\n===== {datetime.now()} =====\n{result}")
    write_results("Packet Sniffer", result)
    print(result)

def subdomain_finder(domain="example.com"):
    try:
        subs = ["www", "mail", "ftp"]
        found = []
        for sub in subs:
            url = f"http://{sub}.{domain}"
            try:
                r = requests.get(url, timeout=2)
                if r.status_code == 200:
                    found.append(url)
            except:
                continue
        result = f"Discovered: {found}" if found else "No subdomains found."
    except Exception as e:
        result = f"Error: {e}"
    log_path = os.path.join(LOG_DIR, "subdomain_finder.log")
    with open(log_path, "a") as log_file:
        log_file.write(f"\n\n===== {datetime.now()} =====\n{result}")
    write_results("Subdomain Finder", result)
    print(result)

# ========================
# CLI Menu
# ========================
def cli_menu():
    while True:
        print("\n=== CyberSec Multi Tool Launcher ===")
        print("1. Port Scanner")
        print("2. Ping Sweeper")
        print("3. Banner Grabber")
        print("4. Packet Sniffer")
        print("5. Subdomain Finder")
        print("6. Run Nmap (External)")
        print("7. Run All Internal")
        print("0. Exit")
        choice = input("Enter choice: ")
        if choice == "1":
            target = input("Target IP: ")
            port_scanner(target)
        elif choice == "2":
            subnet = input("Subnet (ex: 192.168.1.): ")
            ping_sweeper(subnet)
        elif choice == "3":
            target = input("Target: ")
            port = int(input("Port: "))
            banner_grabber(target, port)
        elif choice == "4":
            packet_sniffer()
        elif choice == "5":
            domain = input("Domain: ")
            subdomain_finder(domain)
        elif choice == "6":
            run_external_tool("nmap -F localhost", "Nmap")
        elif choice == "7":
            port_scanner("127.0.0.1")
            ping_sweeper()
            banner_grabber("example.com")
            packet_sniffer()
            subdomain_finder()
        elif choice == "0":
            break

# ========================
# GUI
# ========================
def gui_menu():
    root = tk.Tk()
    root.title("CMTL - CyberSec Multi Tool Launcher")
    tk.Button(root, text="Port Scanner", command=lambda: port_scanner("127.0.0.1")).pack(pady=5)
    tk.Button(root, text="Ping Sweeper", command=ping_sweeper).pack(pady=5)
    tk.Button(root, text="Banner Grabber", command=lambda: banner_grabber("example.com", 80)).pack(pady=5)
    tk.Button(root, text="Packet Sniffer", command=packet_sniffer).pack(pady=5)
    tk.Button(root, text="Subdomain Finder", command=lambda: subdomain_finder("example.com")).pack(pady=5)
    tk.Button(root, text="Run Nmap", command=lambda: run_external_tool("nmap -F localhost", "Nmap")).pack(pady=5)
    tk.Button(root, text="Run All Internal", command=lambda: [port_scanner("127.0.0.1"), ping_sweeper(), banner_grabber("example.com"), packet_sniffer(), subdomain_finder("example.com")]).pack(pady=5)
    root.mainloop()

# ========================
# Main
# ========================
if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        cli_menu()
    else:
        gui_menu()
