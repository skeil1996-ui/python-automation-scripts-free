#!/usr/bin/env python3
"""
Shopify Low-Stock Check - LITE (free)
-------------------------------------
List every product variant at or below a stock threshold. One command, read-only.

    python stock_check_lite.py --shop your-store.myshopify.com --token shpat_xxx --threshold 5

Needs an Admin API access token with read_products + read_inventory.
Pure Python, no installs.

Full version (automatic alerts to Discord, Slack, Telegram or email; per-SKU
thresholds; alerts once when low / sold out / restocked; daily summary; works
with the 2026 Dev Dashboard client-credentials setup):
https://skeilster.gumroad.com/l/shopify-low-stock-bot
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

FULL_VERSION = "https://skeilster.gumroad.com/l/shopify-low-stock-bot"
QUERY = """query($c:String){productVariants(first:250,after:$c){edges{node{title sku inventoryQuantity
inventoryItem{tracked} product{title status}}} pageInfo{hasNextPage endCursor}}}"""


def fetch(shop: str, token: str, version: str, post=None) -> list[dict]:
    shop = shop.replace("https://", "").strip("/")
    url = f"https://{shop}/admin/api/{version}/graphql.json"

    def default_post(body):
        req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                     headers={"X-Shopify-Access-Token": token, "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    post = post or default_post
    out, cursor = [], None
    while True:
        data = post({"query": QUERY, "variables": {"c": cursor}})
        if data.get("errors"):
            raise SystemExit(f"Shopify error: {json.dumps(data['errors'])[:300]}")
        conn = data["data"]["productVariants"]
        out += [e["node"] for e in conn["edges"]]
        if not conn["pageInfo"]["hasNextPage"]:
            return out
        cursor = conn["pageInfo"]["endCursor"]


def low_stock(variants: list[dict], threshold: int) -> list[tuple[int, str]]:
    rows = []
    for v in variants:
        if not (v.get("inventoryItem") or {}).get("tracked", True) or v["product"].get("status") != "ACTIVE":
            continue
        qty = int(v.get("inventoryQuantity") or 0)
        if qty <= threshold:
            name = v["product"]["title"] + ("" if v["title"] == "Default Title" else f" - {v['title']}")
            rows.append((qty, name + (f" (SKU {v['sku']})" if v.get("sku") else "")))
    return sorted(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="List low-stock Shopify variants (free lite version).",
                                 epilog=f"Full version with automatic alerts: {FULL_VERSION}")
    ap.add_argument("--shop", required=True)
    ap.add_argument("--token", default=os.environ.get("SHOPIFY_ACCESS_TOKEN", ""))
    ap.add_argument("--threshold", type=int, default=5)
    ap.add_argument("--api-version", default="2026-07")
    a = ap.parse_args(argv)
    if not a.token:
        print("Missing --token (or SHOPIFY_ACCESS_TOKEN).", file=sys.stderr)
        return 2
    try:
        rows = low_stock(fetch(a.shop, a.token, a.api_version), a.threshold)
    except urllib.error.HTTPError as e:
        print(f"Shopify HTTP {e.code}: check shop domain, token and scopes.", file=sys.stderr)
        return 1
    for qty, name in rows:
        print(f"{qty:>5}  {name}")
    print(f"\n{len(rows)} item(s) at or below {a.threshold}.")
    print(f"Get alerted automatically on Discord/Telegram/Slack/email: {FULL_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
