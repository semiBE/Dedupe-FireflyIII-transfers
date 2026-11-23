#!/usr/bin/env python3
"""Find (and optionally delete) duplicate transfers in Firefly III.

A transfer between two imported accounts shows up twice (once per account feed).
Transfers are grouped by (date, amount, source, destination, description).
In a group of n entries, n/2 are real, so the first n/2 (lowest IDs) are kept
and the rest are flagged. Groups with an odd count are only reported, never touched.

Dry-run by default. Pass --delete to actually delete.

Env vars: FIREFLY_URL (e.g. https://firefly.example.com), FIREFLY_TOKEN (personal access token)
Usage:    python3 dedupe_transfers.py [--days 14] [--delete]
"""
import argparse
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import requests

URL = os.environ["FIREFLY_URL"].rstrip("/")
HEADERS = {
    "Authorization": f"Bearer {os.environ['FIREFLY_TOKEN']}",
    "Accept": "application/json",
}


def fetch_transfers(start, end):
    page = 1
    while True:
        r = requests.get(
            f"{URL}/api/v1/transactions",
            headers=HEADERS,
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

    end = date.today()
    start = end - timedelta(days=args.days)

    groups = defaultdict(list)
    for g in fetch_transfers(start.isoformat(), end.isoformat()):
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
        r = requests.delete(f"{URL}/api/v1/transactions/{gid}", headers=HEADERS, timeout=30)
        print(f"deleted {gid}" if r.status_code == 204 else f"FAILED {gid}: {r.status_code} {r.text}")


if __name__ == "__main__":
    sys.exit(main())