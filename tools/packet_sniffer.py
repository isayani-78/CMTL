#!/usr/bin/env python3
    """
    packet_sniffer.py - simple scapy-based packet sniffer (requires scapy and root privileges)
    Usage:
        sudo python packet_sniffer.py [count]
    """
    import sys
    try:
        from scapy.all import sniff
        SCAPY = True
    except Exception:
        SCAPY = False

    def main():
        if not SCAPY:
            print("scapy not installed. Install via: pip install scapy")
            sys.exit(1)
        count = int(sys.argv[1]) if len(sys.argv) >= 2 else 10
        try:
            pkts = sniff(count=count, timeout=30)
            summaries = [p.summary() for p in pkts]
            for s in summaries:
                print(s)
        except PermissionError:
            print("Permission denied. Packet sniffing usually requires root/admin privileges.")
        except Exception as e:
            print(f"ERROR: {e}")

    if __name__ == "__main__":
        main()
