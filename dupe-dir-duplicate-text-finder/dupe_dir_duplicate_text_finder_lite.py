#!/usr/bin/env python3
"""Dupe Dir Lite - Duplicate Text Finder (free edition).

Finds near-duplicate text files in ONE folder and prints the groups to the
console.

Lite limitations:
  * One folder only (no recursion into subfolders)
  * TXT and MD files only (no CSV)
  * Console output only (no reports, no JSON)
  * Read-only: no moving, quarantining or deleting of files

Need recursive scanning, CSV support, reports, exclude patterns and
automatic quarantine? Get the full version of Dupe Dir:
https://skeilster.gumroad.com/l/jjulwj

Standard library only. Python 3.8+.
"""
from __future__ import annotations

import argparse
import codecs
import difflib
import os
import sys
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Set, Tuple

FULL_VERSION_URL = "https://skeilster.gumroad.com/l/jjulwj"
LITE_EXTS = ("txt", "md")
SHINGLE_SIZE = 5
SNIFF_BYTES = 8192
JACCARD_CUTOFF_FACTOR = 0.5
DEFAULT_THRESHOLD = 0.85
DEFAULT_MIN_CHARS = 20


def warn(msg: str) -> None:
    sys.stderr.write("dupe_lite: %s\n" % msg)


# --------------------------------------------------------------------------
# Text handling
# --------------------------------------------------------------------------
def normalize_text(text: str) -> str:
    """NFKC, lowercase, punctuation -> space, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).lower()
    chars = []
    for ch in text:
        if unicodedata.category(ch).startswith("P"):
            chars.append(" ")
        else:
            chars.append(ch)
    return " ".join("".join(chars).split())


def load_text(path: str) -> Optional[str]:
    """Return decoded text, or None if the file looks binary.

    Raises OSError if the file cannot be read.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if b"\x00" in data[:SNIFF_BYTES]:
        return None
    if data.startswith(codecs.BOM_UTF8):
        data = data[len(codecs.BOM_UTF8):]
    return data.decode("utf-8", errors="replace")


def shingle_set(tokens: Sequence[str], n: int = SHINGLE_SIZE) -> Set[str]:
    if not tokens:
        return set()
    if len(tokens) < n:
        return {" ".join(tokens)}
    return {" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)}


def exact_score(a: Sequence[str], b: Sequence[str], threshold: float = 0.0) -> float:
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    if threshold > 0.0:
        if sm.real_quick_ratio() < threshold or sm.quick_ratio() < threshold:
            return 0.0
    return sm.ratio()


# --------------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------------
@dataclass
class Doc:
    name: str
    path: str
    tokens: List[str]
    chars: int


@dataclass
class Cluster:
    docs: List[Doc]
    best_score: float


# --------------------------------------------------------------------------
# Scanning (single folder, non-recursive)
# --------------------------------------------------------------------------
def build_documents(folder: str, min_chars: int = DEFAULT_MIN_CHARS
                    ) -> Tuple[List[Doc], Dict[str, int]]:
    """Read TXT/MD files directly inside ``folder`` (no subfolders)."""
    stats = {"scanned": 0, "short_or_empty": 0, "binary": 0,
             "unreadable": 0, "symlink": 0}
    docs: List[Doc] = []
    with os.scandir(folder) as it:
        entries = sorted(it, key=lambda e: e.name)
    for entry in entries:
        ext = os.path.splitext(entry.name)[1].lstrip(".").lower()
        if ext not in LITE_EXTS:
            continue
        if entry.is_symlink():
            stats["symlink"] += 1
            continue
        if not entry.is_file(follow_symlinks=False):
            continue
        stats["scanned"] += 1
        try:
            text = load_text(entry.path)
        except OSError as exc:
            warn("cannot read %s: %s" % (entry.name, exc))
            stats["unreadable"] += 1
            continue
        if text is None:
            warn("skipping binary file %s" % entry.name)
            stats["binary"] += 1
            continue
        norm = normalize_text(text)
        if not norm or len(norm) < min_chars:
            stats["short_or_empty"] += 1
            continue
        docs.append(Doc(name=entry.name, path=entry.path,
                        tokens=norm.split(" "), chars=len(norm)))
    return docs, stats


# --------------------------------------------------------------------------
# Clustering
# --------------------------------------------------------------------------
class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


def find_clusters(docs: Sequence[Doc], threshold: float) -> List[Cluster]:
    n = len(docs)
    sets = [shingle_set(d.tokens) for d in docs]
    index: Dict[str, List[int]] = {}
    for i, s in enumerate(sets):
        for sh in s:
            index.setdefault(sh, []).append(i)

    uf = UnionFind(n)
    best: Dict[int, float] = {}
    pairs: List[Tuple[int, int, float]] = []
    cutoff = threshold * JACCARD_CUTOFF_FACTOR
    for i in range(n):
        counts: Dict[int, int] = {}
        for sh in sets[i]:
            for j in index[sh]:
                if j > i:
                    counts[j] = counts.get(j, 0) + 1
        for j in sorted(counts):
            c = counts[j]
            union = len(sets[i]) + len(sets[j]) - c
            jac = c / union if union else 0.0
            if jac < cutoff:
                continue
            score = exact_score(docs[i].tokens, docs[j].tokens, threshold)
            if score >= threshold:
                uf.union(i, j)
                pairs.append((i, j, score))

    for i, j, score in pairs:
        r = uf.find(i)
        best[r] = max(best.get(r, 0.0), score)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        groups.setdefault(uf.find(i), []).append(i)

    clusters = []
    for root_idx, members in groups.items():
        if len(members) < 2:
            continue
        cdocs = sorted((docs[i] for i in members), key=lambda d: d.name)
        clusters.append(Cluster(docs=cdocs, best_score=best.get(root_idx, 0.0)))
    clusters.sort(key=lambda c: c.docs[0].name)
    return clusters


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dupe_lite",
        description=(
            "Dupe Dir Lite (free): find near-duplicate TXT/MD files in one "
            "folder. Lite limits: single folder (not recursive), TXT/MD only, "
            "console output only, read-only (no moving or deleting)."),
        epilog=("Want recursive scans, CSV support, reports, exclude patterns "
                "and quarantine? Full version: " + FULL_VERSION_URL),
    )
    p.add_argument("folder", help="folder to scan (subfolders are ignored)")
    p.add_argument("-t", "--threshold", type=float, default=DEFAULT_THRESHOLD,
                   help="similarity threshold 0.0-1.0 (default: %(default)s)")
    p.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS,
                   help="ignore files shorter than this after normalisation "
                        "(default: %(default)s)")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not 0.0 < args.threshold <= 1.0:
        warn("threshold must be in (0.0, 1.0]")
        return 2
    if not os.path.isdir(args.folder):
        warn("not a directory: %s" % args.folder)
        return 2
    try:
        docs, stats = build_documents(args.folder, args.min_chars)
    except OSError as exc:
        warn("cannot scan folder: %s" % exc)
        return 2

    clusters = find_clusters(docs, args.threshold)
    print("Dupe Dir Lite (threshold %.2f)" % args.threshold)
    print("Files matched: %d | analysed: %d | skipped: short/empty=%d "
          "binary=%d unreadable=%d symlink=%d" % (
              stats["scanned"], len(docs), stats["short_or_empty"],
              stats["binary"], stats["unreadable"], stats["symlink"]))
    if not clusters:
        print("No near-duplicates found.")
    for k, c in enumerate(clusters, 1):
        print("")
        print("Group %d (%d files, best similarity %.2f)" % (
            k, len(c.docs), c.best_score))
        for d in c.docs:
            print("  - %s" % d.name)
    print("")
    print("Lite edition: one folder, console only. Full version: "
          + FULL_VERSION_URL)
    return 0


if __name__ == "__main__":
    sys.exit(main())
