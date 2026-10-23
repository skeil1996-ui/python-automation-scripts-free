#!/usr/bin/env python3
"""
Email Attachment Saver - LITE (free)
------------------------------------
Download all PDF attachments from one sender into a folder, once.
Works with Gmail (App Password) and any IMAP mailbox. Pure Python, no installs.

    python attachment_saver_lite.py --email you@gmail.com --from billing@shop.com
    (asks for your App Password; or set MAIL_APP_PASSWORD)

Full version (any file types, subject & Gmail-search filters, dated sub-folders,
watch mode, never saves the same file twice, config file, several mailboxes):
https://skeilster.gumroad.com/l/gmail-attachment-saver
"""
from __future__ import annotations

import argparse
import email
import email.policy
import getpass
import imaplib
import os
import re
import sys
from pathlib import Path

FULL_VERSION = "https://skeilster.gumroad.com/l/gmail-attachment-saver"


def safe(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name).strip(" .") or "attachment.pdf"


def unique(p: Path) -> Path:
    i = 1
    while p.exists():
        p = p.with_name(f"{p.stem} ({i}){p.suffix}")
        i += 1
    return p


def run(host: str, user: str, password: str, sender: str, folder: Path, imap=None) -> int:
    M = imap or imaplib.IMAP4_SSL(host)
    M.login(user, password.replace(" ", ""))
    M.select("INBOX", readonly=True)
    typ, data = M.uid("SEARCH", None, "FROM", f'"{sender}"')
    uids = data[0].split() if typ == "OK" and data and data[0] else []
    folder.mkdir(parents=True, exist_ok=True)
    saved = 0
    for uid in uids:
        _, msg_data = M.uid("FETCH", uid.decode() if isinstance(uid, bytes) else str(uid), "(BODY.PEEK[])")
        raw = next((p[1] for p in msg_data if isinstance(p, tuple)), None)
        if not raw:
            continue
        msg = email.message_from_bytes(raw, policy=email.policy.default)
        for part in msg.walk():
            name = part.get_filename()
            if name and name.lower().endswith(".pdf"):
                target = unique(folder / safe(name))
                target.write_bytes(part.get_payload(decode=True) or b"")
                print(f"  + {target}")
                saved += 1
    M.logout()
    print(f"\nSaved {saved} PDF(s) from {len(uids)} email(s).")
    print(f"Want it automatic, with filters and no duplicates? {FULL_VERSION}")
    return saved


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Save PDF attachments from one sender (free lite version).",
                                 epilog=f"Full version: {FULL_VERSION}")
    ap.add_argument("--email", required=True)
    ap.add_argument("--from", dest="sender", required=True, help="sender address or part of it")
    ap.add_argument("--host", default="imap.gmail.com")
    ap.add_argument("-o", "--out", default="Attachments")
    a = ap.parse_args(argv)
    pw = os.environ.get("MAIL_APP_PASSWORD") or getpass.getpass("App password: ")
    try:
        run(a.host, a.email, pw, a.sender, Path(a.out))
    except imaplib.IMAP4.error as e:
        print(f"Login failed: {e}. Gmail needs an App Password: https://myaccount.google.com/apppasswords",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
