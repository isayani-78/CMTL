#!/usr/bin/env python3
    """
    subdomain_finder.py - small dictionary-based subdomain probe (educational)
    Usage:
        python subdomain_finder.py example.com
    """
    import sys
    try:
        import requests
    except Exception:
        requests = None

    COMMON_SUBS = ["www","mail","ftp","dev","test","staging","api","beta"]

    def probe(domain, subs=None, timeout=2):
        if requests is None:
            print("requests not installed. Install via: pip install requests")
            return []
        subs = subs or COMMON_SUBS
        found = []
        for s in subs:
            url = f"http://{s}.{domain}"
            try:
                r = requests.get(url, timeout=timeout, allow_redirects=True)
                if r.status_code < 400:
                    found.append((url, r.status_code))
            except Exception:
                pass
        return found

    def main():
        if len(sys.argv) < 2:
            print("Usage: python subdomain_finder.py <domain>")
            sys.exit(1)
        domain = sys.argv[1]
        found = probe(domain)
        for url, code in found:
            print(f"[FOUND] {url} -> {code}")
        if not found:
            print("No subdomains found (with default list).")

    if __name__ == "__main__":
        main()
