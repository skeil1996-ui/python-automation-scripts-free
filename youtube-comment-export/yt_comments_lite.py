#!/usr/bin/env python3
"""
YouTube Comment Export - LITE (free)
------------------------------------
Export the top-level comments of one YouTube video to a CSV (opens in Excel).
Uses the official YouTube Data API v3 with a free API key. Pure Python, no installs.

    python yt_comments_lite.py https://youtu.be/VIDEO_ID --api-key YOUR_KEY

Full version (all replies, whole channels, keyword counter and an insights
report: questions your audience asks, top comments, top words, most active fans):
https://skeilster.gumroad.com/l/youtube-comment-exporter
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

FULL_VERSION = "https://skeilster.gumroad.com/l/youtube-comment-exporter"


def video_id(s: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/live/)([A-Za-z0-9_-]{11})", s)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", s.strip()):
        return s.strip()
    raise SystemExit(f"Not a YouTube link or ID: {s}")


def default_get(params: dict) -> dict:
    url = "https://www.googleapis.com/youtube/v3/commentThreads?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode())


def comments(vid: str, key: str, get=default_get) -> list[dict]:
    rows, token = [], None
    while True:
        p = {"part": "snippet", "videoId": vid, "maxResults": 100, "textFormat": "plainText", "key": key}
        if token:
            p["pageToken"] = token
        data = get(p)
        for it in data.get("items", []):
            s = it["snippet"]["topLevelComment"]["snippet"]
            rows.append({"author": s.get("authorDisplayName", ""), "text": s.get("textDisplay", ""),
                         "likes": s.get("likeCount", 0), "replies": it["snippet"].get("totalReplyCount", 0),
                         "published": s.get("publishedAt", "")})
        token = data.get("nextPageToken")
        if not token:
            return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Export YouTube comments to CSV (free lite version).",
                                 epilog=f"Full version: {FULL_VERSION}")
    ap.add_argument("video")
    ap.add_argument("--api-key", default=os.environ.get("YOUTUBE_API_KEY", ""))
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)
    if not a.api_key:
        print("Missing --api-key (free: console.cloud.google.com -> YouTube Data API v3).", file=sys.stderr)
        return 2
    vid = video_id(a.video)
    try:
        rows = comments(vid, a.api_key)
    except urllib.error.HTTPError as e:
        print(f"YouTube API error {e.code} (key, quota or comments disabled).", file=sys.stderr)
        return 1
    out = a.out or f"comments_{vid}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["author", "text", "likes", "replies", "published"])
        w.writeheader()
        w.writerows(rows)
    print(f"Saved {len(rows)} comments to {out}")
    print(f"Want all replies and a report of your audience's questions? {FULL_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
