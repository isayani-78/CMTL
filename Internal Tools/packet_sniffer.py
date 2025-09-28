#!/usr/bin/env python3
"""
packet_sniffer.py
Simple packet capture using scapy.
Usage:
    sudo python packet_sniffer.py --count 20
Note: scapy requires elevated privileges for live capture on many systems.
"""

import argparse

try:
    from scapy.all import sniff  # type: ignore
    SCAPY = True
except Exception:
    SCAPY = False

def main():
    parser = argparse.ArgumentParser(description="Simple packet sniffer (scapy)")
    parser.add_argument("--count", type=int, default=10, help="Number of packets to capture")
    parser.add_argument("--timeout", type=int, default=30, help="Capture timeout (s)")
    args = parser.parse_args()

    if not SCAPY:
        print("scapy not installed. Install using: pip install scapy")
        return

    print(f"Capturing {args.count} packets (timeout {args.timeout}s)... Press Ctrl+C to stop early.")
    try:
        pkts = sniff(count=args.count, timeout=args.timeout)
        print(f"Captured {len(pkts)} packets. Summaries:")
        for p in pkts:
            print(p.summary())
    except PermissionError:
        print("Permission denied: run with sudo/Administrator privileges to capture packets.")
    except KeyboardInterrupt:
        print("\nCapture stopped by user.")
    except Exception as e:
        print("Error capturing:", e)

if __name__ == "__main__":
    main()
