#!/usr/bin/env python3
"""
ping_sweeper.py
Simple ping sweep over an IPv4 subnet base.
Usage:
    python ping_sweeper.py 192.168.1 1 50
Which scans 192.168.1.1 .. 192.168.1.50
"""

import sys
import subprocess
import platform
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

def ping(ip, timeout=1000):
    """Return True if host responds to a single ping."""
    system = platform.system().lower()
    if system == "windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout), ip]
    else:
        # -c 1 (count 1), -W 1 (timeout seconds) or -W 1 on Linux; macOS uses -W in ms?
        cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def main():
    parser = argparse.ArgumentParser(description="Simple Ping Sweep")
    parser.add_argument("base", help="Base IP without last octet (e.g. 192.168.1)")
    parser.add_argument("start", type=int, nargs="?", default=1)
    parser.add_argument("end", type=int, nargs="?", default=20)
    parser.add_argument("--workers", type=int, default=50)
    args = parser.parse_args()

    ips = [f"{args.base}.{i}" for i in range(args.start, args.end+1)]
    print(f"Pinging {len(ips)} hosts on {args.base}.x ...")

    alive = []
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(ping, ip): ip for ip in ips}
        for fut in as_completed(futures):
            ip = futures[fut]
            try:
                if fut.result():
                    print(f"[UP] {ip}")
                    alive.append(ip)
            except Exception:
                pass

    print("Alive hosts:", alive)

if __name__ == "__main__":
    main()
