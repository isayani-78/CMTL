#!/usr/bin/env python3
    """
    ping_sweeper.py - ping sweep a /24 base range
    Usage:
        python ping_sweeper.py 192.168.1. 1 50
    """
    import sys
    import subprocess
    import platform

    def ping_one(ip):
        system = platform.system().lower()
        if system == "windows":
            cmd = ["ping", "-n", "1", "-w", "1000", ip]
        else:
            # Linux / mac
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
            if ping_one(ip):
                alive.append(ip)
        return alive

    def main():
        if len(sys.argv) < 2:
            print("Usage: python ping_sweeper.py <base> [start] [end]")
            sys.exit(1)
        base = sys.argv[1]
        start = int(sys.argv[2]) if len(sys.argv) >= 3 else 1
        end = int(sys.argv[3]) if len(sys.argv) >= 4 else 50
        alive = sweep(base, start, end)
        print("Alive hosts:", alive)

    if __name__ == "__main__":
        main()
