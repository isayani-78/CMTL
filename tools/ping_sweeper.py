#!/usr/bin/env python3
"""
ping_sweeper.py - cross-platform ping sweep with robust flags
Usage:
    python tools/ping_sweeper.py 192.168.1. 1 50
If run on Windows the script will use 'ping -n', on Unix it uses 'ping -c'.
"""
import sys
import subprocess
import platform

def is_reachable(ip):
    system = platform.system().lower()
    if system == "windows":
        # -n 1 = 1 echo, -w 1000 = timeout in ms
        cmd = ["ping", "-n", "1", "-w", "1000", ip]
    else:
        # Linux/macOS: -c 1 (1 packet), -W 1 (timeout seconds) on many systems
        # On some BSD/macOS `-W` uses milliseconds; we choose -c with short overall timeout using timeout command if available.
        cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return res.returncode == 0
    except Exception:
        return False

def sweep(base, start=1, end=50):
    alive = []
    for i in range(start, end+1):
        ip = f"{base}{i}"
        if is_reachable(ip):
            alive.append(ip)
            print(f"[UP] {ip}")
        else:
            print(f"[DOWN] {ip}")
    return alive

def main():
    if len(sys.argv) < 2:
        print("Usage: python ping_sweeper.py <base> [start] [end]")
        sys.exit(1)
    base = sys.argv[1]
    try:
        start = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
        end = int(sys.argv[3]) if len(sys.argv) >= 4 else 50
    except Exception:
        start, end = 1, 50
    alive = sweep(base, start, end)
    print("Alive hosts:", alive)

if __name__ == "__main__":
    main()
