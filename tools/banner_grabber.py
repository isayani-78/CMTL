#!/usr/bin/env python3
    """
    banner_grabber.py - simple banner grabber for TCP services
    Usage:
        python banner_grabber.py example.com 80
    """
    import sys
    import socket

    def grab(host, port=80, timeout=3):
        s = socket.socket()
        s.settimeout(timeout)
        try:
            s.connect((host, port))
            try:
                # send HTTP HEAD to elicit a response from web servers
                s.sendall(f"HEAD / HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n".encode())
            except Exception:
                pass
            # read up to ~8KB
            chunks = []
            try:
                data = s.recv(8192)
                if data:
                    chunks.append(data)
            except Exception:
                pass
            s.close()
            return b"".join(chunks).decode(errors="ignore")
        except Exception as e:
            return f"ERROR: {e}"

    def main():
        if len(sys.argv) < 2:
            print("Usage: python banner_grabber.py <host> [port]")
            sys.exit(1)
        host = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) >= 3 else 80
        banner = grab(host, port)
        print(banner)

    if __name__ == "__main__":
        main()
