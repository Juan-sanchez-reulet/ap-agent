from datetime import date
from decimal import Decimal

import pytest

from apagent.extraction.schema import (
    ConversionError,
    ExtractedInvoice,
    ExtractedLine,
    ExtractedTaxLine,
    to_invoice,
)


def _extracted(**overrides: object) -> ExtractedInvoice:
    data: dict[str, object] = {
        "invoice_number": " PC-2026-0412 ",
        "issue_date": "2026-09-02",
        "issuer_name": "Papelería Central Valencia S.L.",
        "issuer_tax_id": "B46871232",
        "recipient_tax_id": "",
        "lines": [
            ExtractedLine(
                description="Toner", quantity=2, unit_price=62.0, line_total=124.0, vat_rate=21
            )
        ],
        "tax_breakdown": [ExtractedTaxLine(base=124.0, rate=21, amount=26.04)],
        "subtotal": 124.0,
        "vat_total": 26.04,
        "total": 150.04,
    }
    data.update(overrides)
    return ExtractedInvoice.model_validate(data)


def test_converts_to_domain_types() -> None:
    invoice = to_invoice(_extracted())
    assert invoice.invoice_number == "PC-2026-0412"
    assert invoice.recipient_tax_id is None
    assert invoice.issue_date == date(2026, 9, 2)
    assert invoice.total == Decimal("150.04")
    assert invoice.lines[0].unit_price == Decimal("62.00")
    assert invoice.tax_breakdown[0].rate == Decimal("21")


def test_float_artefacts_are_rounded_to_cents() -> None:
    invoice = to_invoice(_extracted(vat_total=26.039999999))
    assert invoice.vat_total == Decimal("26.04")


def test_bad_date_raises_conversion_error() -> None:
    with pytest.raises(ConversionError, match="issue_date"):
        to_invoice(_extracted(issue_date="02/09/2026"))


def test_line_without_total_raises() -> None:
    with pytest.raises(ConversionError, match=r"lines\[0\].line_total"):
        to_invoice(_extracted(lines=[ExtractedLine(description="x", quantity=1)]))


def test_line_without_quantity_defaults_to_one_unit_at_line_total() -> None:
    invoice = to_invoice(_extracted(lines=[ExtractedLine(description="Fee", line_total=50.0)]))
    assert invoice.lines[0].quantity == Decimal("1")
    assert invoice.lines[0].unit_price == Decimal("50.00")


def test_incomplete_tax_line_raises() -> None:
    with pytest.raises(ConversionError, match=r"tax_breakdown\[0\]"):
        to_invoice(_extracted(tax_breakdown=[ExtractedTaxLine(base=124.0, rate=21)]))
