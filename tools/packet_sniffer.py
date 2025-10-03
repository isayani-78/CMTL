#!/usr/bin/env python3
"""
packet_sniffer.py - Scapy-based packet sniffer with permission checks and helpful messages.
Usage:
    sudo python packet_sniffer.py 10
Notes:
 - Requires scapy package installed (pip install scapy).
 - Requires libpcap / WinPcap / Npcap on the OS and usually root/admin privileges.
"""
import sys
import os

try:
    from scapy.all import sniff
    SCAPY_OK = True
except Exception:
    SCAPY_OK = False

def have_root_privileges():
    if os.name == "nt":
        # On Windows, checking admin is non-trivial; attempt to create raw socket or use env (best-effort)
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except Exception:
            return False
    else:
        return os.geteuid() == 0

def main():
    if not SCAPY_OK:
        print("scapy not installed. Install via: pip install scapy")
        sys.exit(1)
    if not have_root_privileges():
        print("Warning: packet sniffing typically requires root/Administrator privileges.")
        print("On Linux: run with sudo. On Windows: run PowerShell as Administrator and ensure Npcap is installed.")
        # we continue but sniff may fail
    try:
        count = int(sys.argv[1]) if len(sys.argv) >= 2 else 10
    except Exception:
        count = 10
    try:
        print(f"Capturing {count} packets (timeout 30s)...")
        pkts = sniff(count=count, timeout=30)
        if not pkts:
            print("No packets captured (timeout or interface issue).")
            return
        summaries = [p.summary() for p in pkts]
        for s in summaries:
            print(s)
    except PermissionError:
        print("Permission denied. Run as root/Administrator and ensure libpcap / Npcap is installed.")
    except Exception as e:
        print(f"Sniffer failed: {e}")

if __name__ == "__main__":
    main()
