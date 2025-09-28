#!/usr/bin/env python3
"""
port_scanner.py
Simple TCP port scanner (connect scan).
Usage:
    python port_scanner.py <host>         # scans default common ports
    python port_scanner.py <host> 1-1024  # scans port range
"""

import sys
import socket
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

COMMON_PORTS = [21,22,23,25,53,80,110,139,143,443,445,3306,3389,8080]

def scan_port(host, port, timeout=0.8):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        s.close()
        return port, True
    except Exception:
        return port, False

def parse_range(s):
    if "-" in s:
        a,b = s.split("-",1)
        return list(range(int(a), int(b)+1))
    else:
        return [int(x) for x in s.split(",") if x.strip()]

def main():
    parser = argparse.ArgumentParser(description="Simple TCP Port Scanner")
    parser.add_argument("host", help="Target host (IP or domain)")
    parser.add_argument("ports", nargs="?", help="Port list (e.g. 22,80,443) or range 1-1024", default=None)
    parser.add_argument("--timeout", type=float, default=0.8)
    parser.add_argument("--workers", type=int, default=100)
    args = parser.parse_args()

    host = args.host
    if args.ports:
        try:
            ports = parse_range(args.ports)
        except Exception:
            print("Invalid ports argument.")
            return
    else:
        ports = COMMON_PORTS

    print(f"Scanning {host} ({len(ports)} ports)...")
    open_ports = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(scan_port, host, p, args.timeout): p for p in ports}
        for fut in as_completed(futures):
            p, ok = fut.result()
            if ok:
                print(f"[+] {host}:{p} OPEN")
                open_ports.append(p)

    if not open_ports:
        print("No open ports found (on the scanned list).")
    else:
        print(f"Open ports: {sorted(open_ports)}")

if __name__ == "__main__":
    main()
