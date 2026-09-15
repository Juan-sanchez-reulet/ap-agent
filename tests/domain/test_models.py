from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from apagent.domain import Invoice, Issue, Severity, to_money


def test_to_money_rounds_half_up_to_cents() -> None:
    assert to_money("65.1525") == Decimal("65.15")
    assert to_money(0.125) == Decimal("0.13")
    assert to_money(10) == Decimal("10.00")


def test_invoice_parses_json_like_input() -> None:
    invoice = Invoice.model_validate(
        {
            "invoice_number": "PC-2026-0412",
            "issue_date": "2026-09-02",
            "lines": [
                {
                    "description": "Toner",
                    "quantity": "2",
                    "unit_price": "62.00",
                    "line_total": "124.00",
                }
            ],
            "tax_breakdown": [{"base": "124.00", "rate": "21", "amount": "26.04"}],
            "subtotal": "124.00",
            "vat_total": "26.04",
            "total": "150.04",
        }
    )
    assert invoice.issue_date == date(2026, 9, 2)
    assert invoice.lines[0].discount_pct == Decimal("0")
    assert invoice.total == Decimal("150.04")
    assert invoice.currency == "EUR"


def test_issue_is_immutable() -> None:
    issue = Issue(code="TOTAL_MISMATCH", severity=Severity.BLOCKER, message="x")
    assert issue.severity == "blocker"
    assert issue.evidence == {}
    with pytest.raises(ValidationError):
        issue.code = "OTHER"  # type: ignore[misc]
