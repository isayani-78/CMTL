#!/usr/bin/env python3
"""
subdomain_finder.py
Lightweight subdomain probe using a small built-in wordlist.
Usage:
    python subdomain_finder.py example.com
Note: This is a simple, low-volume probe — for learning purposes only.
"""

import argparse

try:
    import requests
except Exception:
    requests = None

COMMON_SUBS = ["www", "mail", "ftp", "dev", "test", "staging", "api", "beta"]

def probe(domain, subs=None, timeout=2):
    subs = subs or COMMON_SUBS
    found = []
    if requests is None:
        print("requests not installed. Install: pip install requests")
        return found
    for s in subs:
        url = f"http://{s}.{domain}"
        try:
            r = requests.get(url, timeout=timeout, allow_redirects=True)
            if r.status_code < 400:
                print(f"[FOUND] {url} -> {r.status_code}")
                found.append((url, r.status_code))
        except requests.RequestException:
            pass
    return found

def main():
    parser = argparse.ArgumentParser(description="Lightweight subdomain finder")
    parser.add_argument("domain", help="Target domain (example.com)")
    parser.add_argument("--extra", nargs="*", help="Extra subdomains to try")
    args = parser.parse_args()

    subs = COMMON_SUBS + (args.extra or [])
    found = probe(args.domain, subs=subs)
    print("Done. Found:", found)

if __name__ == "__main__":
    import argparse
    main()
