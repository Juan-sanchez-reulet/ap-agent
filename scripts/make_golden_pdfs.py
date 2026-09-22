"""Render golden-case PDFs from their expected.json ground truth.

Four visually different layouts so extraction is not tuned to one template.
Amounts are printed exactly as the ground truth says, including the deliberate
errors (that is what the traps test). Core fonts are latin-1, so we print 'EUR'.
"""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from fpdf import FPDF

GOLDEN = Path("evals/datasets/golden")
LAYOUTS = {
    "G001": "classic",
    "G002": "modern",
    "G003": "plain",
    "G004": "classic",
    "G005": "modern",
    "G006": "plain",
    "G007": "classic",
    "G008": "modern",
    "G009": "plain",
    "G010": "english",
}


def es(value: str | float | Decimal | None) -> str:
    """Spanish number format: 1.234,56"""
    if value is None:
        return ""
    return f"{Decimal(str(value)):,.2f}".replace(",", "@").replace(".", ",").replace("@", ".")


def en(value: str | float | Decimal | None) -> str:
    return "" if value is None else f"{Decimal(str(value)):,.2f}"


def _new(font: str = "Helvetica") -> FPDF:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font(font, size=10)
    return pdf


def _line(pdf: FPDF, text: str, size: int = 10, style: str = "", height: float = 5.5) -> None:
    pdf.set_font(pdf.font_family, style, size)
    pdf.cell(text=text, new_x="LMARGIN", new_y="NEXT", h=height)


def _table(
    pdf: FPDF, header: list[str], rows: list[list[str]], widths: list[float], border: int = 1
) -> None:
    pdf.set_font(pdf.font_family, "B", 9)
    for label, width in zip(header, widths, strict=True):
        pdf.cell(width, 7, label, border=border, align="C")
    pdf.ln()
    pdf.set_font(pdf.font_family, "", 9)
    for row in rows:
        for cell, width in zip(row, widths, strict=True):
            align = "R" if cell.replace(".", "").replace(",", "").isdigit() else "L"
            pdf.cell(width, 6.5, cell, border=border, align=align)
        pdf.ln()


def _totals_es(inv: dict[str, Any]) -> list[tuple[str, str]]:
    rows = [("Base imponible", f"{es(inv['subtotal'])} EUR")]
    for tax in inv["tax_breakdown"]:
        rows.append(
            (
                f"IVA {es(tax['rate']).rstrip('0').rstrip(',')}% s/ {es(tax['base'])}",
                f"{es(tax['amount'])} EUR",
            )
        )
    if inv.get("irpf_amount"):
        rows.append(
            (
                f"Retención IRPF {es(inv['irpf_rate']).rstrip('0').rstrip(',')}%",
                f"-{es(inv['irpf_amount'])} EUR",
            )
        )
    rows.append(("TOTAL FACTURA", f"{es(inv['total'])} EUR"))
    return rows


def classic(inv: dict[str, Any]) -> bytes:
    pdf = _new("Times")
    _line(pdf, inv["issuer_name"], size=14, style="B")
    _line(pdf, inv["issuer_address"])
    _line(pdf, f"CIF: {inv['issuer_tax_id']}    IBAN: {inv['issuer_iban']}")
    pdf.ln(4)
    _line(pdf, "FACTURA", size=13, style="B")
    if inv.get("invoice_number"):
        _line(pdf, f"Número: {inv['invoice_number']}")
    iso = inv["issue_date"]
    _line(pdf, f"Fecha de emisión: {iso[8:10]}/{iso[5:7]}/{iso[:4]}")
    pdf.ln(2)
    _line(pdf, "FACTURAR A:", style="B")
    _line(pdf, inv["recipient_name"])
    _line(pdf, f"CIF: {inv['recipient_tax_id']}")
    pdf.ln(4)
    rows = [
        [
            ln["description"],
            es(ln["quantity"]).rstrip("0").rstrip(","),
            es(ln["unit_price"]),
            es(ln["line_total"]),
        ]
        for ln in inv["lines"]
    ]
    _table(pdf, ["Concepto", "Cant.", "Precio", "Importe"], rows, [95, 20, 30, 35])
    pdf.ln(4)
    for label, value in _totals_es(inv):
        pdf.cell(110, 6, "", border=0)
        pdf.cell(45, 6, label, align="R")
        pdf.cell(35, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def modern(inv: dict[str, Any]) -> bytes:
    pdf = _new()
    pdf.set_font("Helvetica", "B", 22)
    pdf.cell(text="FACTURA", new_x="LMARGIN", new_y="NEXT", h=12)
    pdf.set_font("Helvetica", size=10)
    if inv.get("invoice_number"):
        _line(pdf, f"Ref. {inv['invoice_number']}   |   {inv['issue_date']}")
    else:
        _line(pdf, f"{inv['issue_date']}")
    pdf.ln(3)
    start_y = pdf.get_y()
    _line(pdf, "EMISOR", size=9, style="B")
    _line(pdf, inv["issuer_name"], size=9)
    _line(pdf, inv["issuer_address"], size=9)
    _line(pdf, inv["issuer_tax_id"], size=9)
    _line(pdf, inv["issuer_iban"], size=9)
    end_y = pdf.get_y()
    pdf.set_xy(115, start_y)
    for text, style in [
        ("CLIENTE", "B"),
        (inv["recipient_name"], ""),
        (inv["recipient_tax_id"], ""),
    ]:
        pdf.set_font("Helvetica", style, 9)
        pdf.cell(text=text, new_x="LEFT", new_y="NEXT", h=5.5)
    pdf.set_xy(10, max(end_y, pdf.get_y()) + 6)
    rows = [
        [
            ln["description"],
            f"{es(ln['quantity']).rstrip('0').rstrip(',')} x {es(ln['unit_price'])}",
            es(ln["line_total"]),
        ]
        for ln in inv["lines"]
    ]
    _table(pdf, ["Descripción", "Detalle", "Importe"], rows, [100, 45, 35], border=0)
    pdf.ln(6)
    for label, value in _totals_es(inv):
        pdf.cell(100, 6, "", border=0)
        pdf.cell(50, 6, label, align="R")
        pdf.cell(30, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def plain(inv: dict[str, Any]) -> bytes:
    pdf = _new("Courier")
    _line(pdf, inv["issuer_name"], size=11, style="B")
    _line(pdf, inv["issuer_address"], size=9)
    _line(pdf, f"NIF {inv['issuer_tax_id']}", size=9)
    _line(pdf, f"Cuenta {inv['issuer_iban']}", size=9)
    pdf.ln(3)
    number = inv.get("invoice_number") or ""
    _line(pdf, f"Factura {number}".strip())
    _line(pdf, f"Fecha {inv['issue_date']}")
    _line(pdf, f"Cliente: {inv['recipient_name']} ({inv['recipient_tax_id']})")
    pdf.ln(3)
    _line(pdf, "-" * 74, size=9)
    for ln in inv["lines"]:
        qty = es(ln["quantity"]).rstrip("0").rstrip(",")
        _line(
            pdf,
            f"{ln['description'][:40]:<42}{qty:>4} x {es(ln['unit_price']):>9}"
            f"{es(ln['line_total']):>12}",
            size=9,
        )
    _line(pdf, "-" * 74, size=9)
    for label, value in _totals_es(inv):
        _line(pdf, f"{label:>56}{value:>18}", size=9)
    return bytes(pdf.output())


def english(inv: dict[str, Any]) -> bytes:
    pdf = _new()
    _line(pdf, inv["issuer_name"], size=13, style="B")
    _line(pdf, inv["issuer_address"], size=9)
    _line(pdf, f"VAT ID: {inv['issuer_tax_id']}   IBAN: {inv['issuer_iban']}", size=9)
    pdf.ln(5)
    _line(pdf, "INVOICE", size=15, style="B")
    _line(pdf, f"Invoice No. {inv['invoice_number']}")
    _line(pdf, f"Date: {inv['issue_date']}")
    pdf.ln(2)
    _line(pdf, "Bill to:", style="B")
    _line(pdf, inv["recipient_name"])
    _line(pdf, f"VAT ID: {inv['recipient_tax_id']}")
    pdf.ln(4)
    rows = [
        [
            ln["description"],
            en(ln["quantity"]).rstrip("0").rstrip("."),
            en(ln["unit_price"]),
            en(ln["line_total"]),
        ]
        for ln in inv["lines"]
    ]
    _table(pdf, ["Description", "Qty", "Unit price", "Amount"], rows, [95, 20, 30, 35])
    pdf.ln(4)
    totals = [("Net amount", f"{en(inv['subtotal'])} EUR")]
    for tax in inv["tax_breakdown"]:
        totals.append(
            (f"VAT {en(tax['rate']).rstrip('0').rstrip('.')}%", f"{en(tax['amount'])} EUR")
        )
    totals.append(("TOTAL DUE", f"{en(inv['total'])} EUR"))
    for label, value in totals:
        pdf.cell(110, 6, "", border=0)
        pdf.cell(45, 6, label, align="R")
        pdf.cell(35, 6, value, align="R", new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


RENDERERS = {"classic": classic, "modern": modern, "plain": plain, "english": english}


def main() -> None:
    for folder in sorted(p for p in GOLDEN.iterdir() if p.is_dir()):
        case = json.loads((folder / "expected.json").read_text(encoding="utf-8"))
        renderer = RENDERERS[LAYOUTS[case["case_id"]]]
        (folder / "invoice.pdf").write_bytes(renderer(case["invoice"]))
        print(f"{case['case_id']}: {LAYOUTS[case['case_id']]}")


if __name__ == "__main__":
    main()
