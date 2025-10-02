#!/usr/bin/env python3
    """
    port_scanner.py - small TCP connect scanner
    Usage:
        python port_scanner.py <target> [ports]
    Example:
        python port_scanner.py 192.168.1.1 22,80,443
    """
    import sys
    import socket

    def scan(target, ports=None, timeout=0.6):
        if ports is None:
            ports = [21,22,23,25,53,80,110,139,143,443,445,3306,3389,8080]
        open_ports = []
        for p in ports:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(timeout)
            try:
                s.connect((target, p))
                open_ports.append(p)
            except Exception:
                pass
            finally:
                try:
                    s.close()
                except Exception:
                    pass
        return open_ports

    def main():
        if len(sys.argv) < 2:
            print("Usage: python port_scanner.py <target> [comma-separated-ports]")
            sys.exit(1)
        target = sys.argv[1]
        ports = None
        if len(sys.argv) >= 3:
            try:
                ports = [int(x.strip()) for x in sys.argv[2].split(",") if x.strip()]
            except Exception:
                ports = None
        open_ports = scan(target, ports)
        print(f"Open ports on {target}: {open_ports}")

    if __name__ == "__main__":
        main()
