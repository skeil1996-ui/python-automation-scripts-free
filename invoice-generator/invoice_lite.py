#!/usr/bin/env python3
"""
CSV to PDF Invoice Generator - LITE (free)
------------------------------------------
Turn a CSV of line items into simple PDF invoices, one per invoice number.

    pip install reportlab
    python invoice_lite.py invoices.csv --company "My Shop" --tax 19 --currency "€"

CSV columns: invoice_number, client_name, description, quantity, unit_price
(optional: invoice_date as YYYY-MM-DD)

Full version (your logo & brand colours, several tax rates per invoice,
German/English labels, payment details, no footer note):
https://skeilster.gumroad.com/l/invoice-generator
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import OrderedDict
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

FULL_VERSION = "https://skeilster.gumroad.com/l/invoice-generator"
TWO = Decimal("0.01")
REQUIRED = {"invoice_number", "client_name", "description", "quantity", "unit_price"}


def num(value: str, field: str, row: int) -> Decimal:
    s = (value or "").strip().replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise SystemExit(f"Row {row}: '{field}' is not a number: {value!r}")


def load(path: Path) -> "OrderedDict[str, dict]":
    text = path.read_text(encoding="utf-8-sig")
    delim = ";" if text.splitlines()[0].count(";") > text.splitlines()[0].count(",") else ","
    reader = csv.DictReader(text.splitlines(keepends=True), delimiter=delim)
    reader.fieldnames = [h.strip().lower().replace(" ", "_") for h in reader.fieldnames or []]
    missing = REQUIRED - set(reader.fieldnames)
    if missing:
        raise SystemExit(f"CSV is missing column(s): {', '.join(sorted(missing))}")
    invoices: "OrderedDict[str, dict]" = OrderedDict()
    for i, r in enumerate(reader, start=2):
        if not (r.get("invoice_number") or "").strip():
            continue
        inv = invoices.setdefault(r["invoice_number"].strip(), {
            "number": r["invoice_number"].strip(), "client": r["client_name"].strip(),
            "date": (r.get("invoice_date") or "").strip() or date.today().isoformat(), "items": []})
        q, p = num(r["quantity"], "quantity", i), num(r["unit_price"], "unit_price", i)
        inv["items"].append((r["description"].strip(), q, p, (q * p).quantize(TWO, ROUND_HALF_UP)))
    return invoices


def money(v: Decimal, cur: str) -> str:
    return f"{v.quantize(TWO, ROUND_HALF_UP):,.2f} {cur}".strip()


def build(inv: dict, company: str, tax: Decimal, cur: str, out: Path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import mm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        raise SystemExit("reportlab is missing. Install it with:  pip install reportlab")
    st = getSampleStyleSheet()
    subtotal = sum((i[3] for i in inv["items"]), Decimal("0"))
    tax_amount = (subtotal * tax / 100).quantize(TWO, ROUND_HALF_UP)
    rows = [["Description", "Qty", "Unit price", "Amount"]]
    rows += [[d, f"{q.normalize():f}", money(p, cur), money(a, cur)] for d, q, p, a in inv["items"]]
    rows += [["", "", "Subtotal", money(subtotal, cur)]]
    if tax:
        rows += [["", "", f"Tax {tax.normalize():f}%", money(tax_amount, cur)]]
    rows += [["", "", "Total", money(subtotal + tax_amount, cur)]]
    t = Table(rows, colWidths=[90 * mm, 20 * mm, 30 * mm, 34 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
                           ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                           ("FONTNAME", (2, -1), (-1, -1), "Helvetica-Bold"),
                           ("LINEABOVE", (2, -1), (-1, -1), 0.8, colors.black)]))

    def footer(canvas, doc):
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Created with Invoice Generator Lite - {FULL_VERSION}")

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm)
    doc.build([Paragraph(company, st["Title"]), Paragraph(f"INVOICE {inv['number']}", st["Heading2"]),
               Paragraph(f"Date: {inv['date']}<br/>Bill to: {inv['client']}", st["Normal"]),
               Spacer(1, 10 * mm), t], onFirstPage=footer, onLaterPages=footer)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="CSV to simple PDF invoices (free lite version).",
                                 epilog=f"Full version: {FULL_VERSION}")
    ap.add_argument("csv")
    ap.add_argument("--company", default="Your Company")
    ap.add_argument("--tax", default="0", help="tax rate in percent, e.g. 19")
    ap.add_argument("--currency", default="$")
    ap.add_argument("-o", "--out", default="invoices")
    a = ap.parse_args(argv)
    invoices = load(Path(a.csv))
    tax = Decimal(a.tax.replace(",", "."))
    for inv in invoices.values():
        name = re.sub(r"[^\w\-]+", "_", f"{inv['number']}_{inv['client']}").strip("_")
        out = Path(a.out) / f"{name}.pdf"
        build(inv, a.company, tax, a.currency, out)
        print(f"created {out}")
    print(f"\n{len(invoices)} invoice(s). Want your logo, colours and several tax rates? {FULL_VERSION}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
