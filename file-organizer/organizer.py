#!/usr/bin/env python3
"""
Smart File Organizer - LITE (free)
----------------------------------
Sort a messy folder into Images / Documents / Videos / Audio / Archives / ...
in one command. Preview first, undo anytime. Pure Python, no installs.

    python organizer.py ~/Downloads --dry-run   # preview, changes nothing
    python organizer.py ~/Downloads             # sort
    python organizer.py --undo ~/Downloads      # put everything back

Full version (bulk rename with patterns, sort by date or extension,
sub-folders, filters): https://skeilster.gumroad.com/l/file-organizer
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

__version__ = "1.0.0-lite"
FULL_VERSION = "https://skeilster.gumroad.com/l/file-organizer"
LOG_DIR = ".organizer_logs"

CATEGORIES = {
    "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".svg", ".ico"],
    "Videos": [".mp4", ".mov", ".avi", ".mkv", ".wmv", ".webm", ".m4v"],
    "Audio": [".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"],
    "Documents": [".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".epub"],
    "Spreadsheets": [".xls", ".xlsx", ".ods", ".csv", ".numbers"],
    "Presentations": [".ppt", ".pptx", ".odp", ".key"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz"],
    "Code": [".py", ".js", ".ts", ".html", ".css", ".json", ".xml", ".yml", ".yaml", ".sh", ".bat", ".ps1"],
    "Installers": [".exe", ".msi", ".dmg", ".pkg", ".deb", ".rpm", ".apk"],
}
EXT = {e: c for c, exts in CATEGORIES.items() for e in exts}


def unique(target: Path, taken: set) -> Path:
    if not target.exists() and target not in taken:
        return target
    i = 1
    while True:
        c = target.with_name(f"{target.stem} ({i}){target.suffix}")
        if not c.exists() and c not in taken:
            return c
        i += 1


def plan(root: Path) -> list[tuple[Path, Path]]:
    taken, moves = set(), []
    for f in sorted(p for p in root.iterdir() if p.is_file() and not p.name.startswith(".")):
        t = unique(root / EXT.get(f.suffix.lower(), "Other") / f.name, taken)
        taken.add(t)
        moves.append((f, t))
    return moves


def sort_folder(root: Path, dry_run: bool) -> int:
    moves = plan(root)
    if not moves:
        print("Nothing to do - folder is already tidy.")
        return 0
    for s, d in moves:
        print(f"{'[dry-run] ' if dry_run else ''}{s.name}  ->  {d.parent.name}/{d.name}")
        if not dry_run:
            d.parent.mkdir(exist_ok=True)
            shutil.move(str(s), str(d))
    if dry_run:
        print(f"\n{len(moves)} file(s) would be moved. Run again without --dry-run to apply.")
        return 0
    (root / LOG_DIR).mkdir(exist_ok=True)
    log = root / LOG_DIR / f"{datetime.now():%Y-%m-%d_%H%M%S_%f}.json"
    log.write_text(json.dumps({"moves": [{"from": str(s), "to": str(d)} for s, d in moves]}, indent=2))
    print(f"\nMoved {len(moves)} file(s). Undo with:  python organizer.py --undo \"{root}\"")
    print(f"Want bulk renaming and sorting by date? Full version: {FULL_VERSION}")
    return 0


def undo(root: Path) -> int:
    logs = sorted((root / LOG_DIR).glob("*.json")) if (root / LOG_DIR).is_dir() else []
    if not logs:
        print("Nothing to undo.")
        return 1
    moves = json.loads(logs[-1].read_text())["moves"]
    for m in reversed(moves):
        s, d = Path(m["from"]), Path(m["to"])
        if d.exists() and not s.exists():
            shutil.move(str(d), str(s))
            try:
                d.parent.rmdir()
            except OSError:
                pass
    logs[-1].rename(logs[-1].with_suffix(".undone.json"))
    print(f"Restored {len(moves)} file(s).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Sort a folder by file type. Free lite version.",
                                 epilog=f"Full version: {FULL_VERSION}")
    ap.add_argument("folder")
    ap.add_argument("-n", "--dry-run", action="store_true", help="preview only")
    ap.add_argument("--undo", action="store_true", help="revert the last sort")
    ap.add_argument("--version", action="version", version=__version__)
    a = ap.parse_args(argv)
    root = Path(a.folder).expanduser().resolve()
    if not root.is_dir():
        print(f"Not a folder: {root}", file=sys.stderr)
        return 2
    return undo(root) if a.undo else sort_folder(root, a.dry_run)


if __name__ == "__main__":
    sys.exit(main())
