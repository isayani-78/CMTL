#!/usr/bin/env python3
"""
banner_grabber.py
Minimal banner grabbing via TCP connect.
Usage:
    python banner_grabber.py example.com 80
"""

import sys
import socket
import argparse

def grab_banner(host, port=80, timeout=3):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        # Try an HTTP HEAD (safe for HTTP servers)
        try:
            s.sendall(b"HEAD / HTTP/1.1\r\nHost: %b\r\nConnection: close\r\n\r\n" % host.encode())
        except Exception:
            pass
        data = s.recv(4096)
        s.close()
        return data.decode(errors="ignore").strip()
    except Exception as e:
        return f"ERROR: {e}"

def main():
    parser = argparse.ArgumentParser(description="Banner Grabber")
    parser.add_argument("host", help="Target hostname or IP")
    parser.add_argument("port", nargs="?", type=int, default=80)
    parser.add_argument("--timeout", type=int, default=3)
    args = parser.parse_args()

    banner = grab_banner(args.host, args.port, args.timeout)
    print("Banner output:")
    print(banner)

if __name__ == "__main__":
    main()
