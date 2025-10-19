#!/usr/bin/env python3
"""
Email_Extract_hunter.py
Simple Hunter-only extractor (reads Hunter API key from ./api_key.txt)

Usage:
  python Email_Extract_hunter.py <domain> <out.csv> [--limit=10]

Output CSV columns:
  email,confidence,position
"""

import sys, requests, csv, re
from pathlib import Path

HUNTER_KEY_FILE = "api_key.txt"
USER_AGENT = "EmailExtractHunter/1.0"
REQUEST_TIMEOUT = 15
DEFAULT_LIMIT = 10

ROLE_RE = re.compile(r'^(admin|support|info|sales|postmaster|noreply|no-reply|webmaster|help|contact|security)@', re.I)

def read_hunter_key():
    p = Path(HUNTER_KEY_FILE)
    if not p.exists():
        return None
    return p.read_text(encoding="utf-8").strip().strip('"').strip("'")

def fetch_hunter(domain, api_key, limit=DEFAULT_LIMIT):
    url = "https://api.hunter.io/v2/domain-search"
    params = {"domain": domain, "api_key": api_key, "limit": limit}
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        j = r.json()
        out = []
        for e in j.get("data", {}).get("emails", []):
            val = e.get("value")
            if not val: 
                continue
            val = val.lower()
            if ROLE_RE.match(val):
                continue
            confidence = e.get("confidence") or ""
            position = e.get("position") or ""
            out.append({"email": val, "confidence": confidence, "position": position})
        return out
    except requests.HTTPError:
        try:
            print("[hunter] HTTP error:", r.json())
        except Exception:
            print("[hunter] HTTP error.")
        return []
    except Exception as ex:
        print("[hunter] request error:", ex)
        return []

def write_csv(path, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email","confidence","position"])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

def parse_limit_arg(argv):
    for a in argv:
        if a.startswith("--limit="):
            try:
                return int(a.split("=",1)[1])
            except:
                return DEFAULT_LIMIT
    return DEFAULT_LIMIT

def main():
    if len(sys.argv) < 3:
        print("Usage: python Email_Extract_hunter.py <domain> <out.csv> [--limit=10]")
        sys.exit(1)
    domain = sys.argv[1].strip()
    out_csv = sys.argv[2].strip()
    limit = parse_limit_arg(sys.argv[3:])

    api_key = read_hunter_key()
    if not api_key:
        print(f"Missing {HUNTER_KEY_FILE} (put your Hunter API key there).")
        sys.exit(1)

    print(f"[hunter] querying {domain} (limit={limit})...")
    results = fetch_hunter(domain, api_key, limit=limit)
    if not results:
        print("No emails found (or API returned no data).")
        return

    # dedupe by email (keep first)
    seen = set()
    unique = []
    for r in results:
        e = r["email"]
        if e in seen: continue
        seen.add(e)
        unique.append(r)

    write_csv(out_csv, unique)
    print(f"Wrote {len(unique)} emails to {out_csv}")

if __name__ == "__main__":
    main()
