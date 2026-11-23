#!/usr/bin/env python3
"""Find (and optionally delete) duplicate transfers in Firefly III.

A transfer between two imported accounts shows up twice (once per account feed).
Transfers are grouped by (date, amount, source, destination, description).
In a group of n entries, n/2 are real, so the first n/2 (lowest IDs) are kept
and the rest are flagged. Groups with an odd count are only reported, never touched.

Dry-run by default. Pass --delete to actually delete.

Install dependencies: python -m pip install -r requirements.txt
Fill in FIREFLY_URL and FIREFLY_TOKEN in .env next to this script, or set
them in the environment. .env values take precedence, even when blank; remove
a key from .env to use its environment value.
Usage: python main.py [--days 14] [--delete]
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import requests
from dotenv import load_dotenv


def fetch_transfers(start, end, url, headers):
    page = 1
    while True:
        r = requests.get(
            f"{url}/api/v1/transactions",
            headers=headers,
            params={"type": "transfer", "start": start, "end": end, "page": page},
            timeout=30,
        )
        r.raise_for_status()
        body = r.json()
        yield from body["data"]
        if page >= body["meta"]["pagination"]["total_pages"]:
            break
        page += 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14, help="how many days back to scan")
    ap.add_argument("--delete", action="store_true", help="delete extras (default: dry run)")
    args = ap.parse_args()

    load_dotenv(Path(__file__).with_name(".env"), override=True)
    url = os.environ.get("FIREFLY_URL", "")
    token = os.environ.get("FIREFLY_TOKEN", "")
    missing = [name for name, value in (("FIREFLY_URL", url), ("FIREFLY_TOKEN", token)) if not value.strip()]
    if missing:
        ap.error(f"Set non-empty {', '.join(missing)} in .env or the environment.")
    url = url.rstrip("/")
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    end = date.today()
    start = end - timedelta(days=args.days)

    groups = defaultdict(list)
    for g in fetch_transfers(start.isoformat(), end.isoformat(), url, headers):
        splits = g["attributes"]["transactions"]
        if len(splits) != 1:  # skip split transactions
            continue
        t = splits[0]
        key = (
            t["date"][:10],
            t["amount"],
            t["source_id"],
            t["destination_id"],
            t["description"],
        )
        groups[key].append(int(g["id"]))

    to_delete = []
    for key, ids in groups.items():
        if len(ids) < 2:
            continue
        ids.sort()
        if len(ids) % 2:
            print(f"SKIP (odd count {len(ids)}, check manually): {key} -> {ids}")
            continue
        keep, extra = ids[: len(ids) // 2], ids[len(ids) // 2 :]
        print(f"{key}\n  keep {keep}  delete {extra}")
        to_delete.extend(extra)

    print(f"\n{len(to_delete)} duplicate(s) found.")
    if not args.delete:
        print("Dry run, nothing deleted. Re-run with --delete to remove them.")
        return

    for gid in to_delete:
        r = requests.delete(f"{url}/api/v1/transactions/{gid}", headers=headers, timeout=30)
        print(f"deleted {gid}" if r.status_code == 204 else f"FAILED {gid}: {r.status_code} {r.text}")


if __name__ == "__main__":
    sys.exit(main())