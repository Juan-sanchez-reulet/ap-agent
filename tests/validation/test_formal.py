from datetime import date
from decimal import Decimal

from apagent.domain import Company, Invoice, LineItem, TaxLine
from apagent.validation import validate_invoice
from apagent.validation.formal import check_formal

COMPANY = Company(
    name="Rivera Componentes Industriales S.L.",
    tax_id="B46123451",
    address="Calle de Colón 18, 46004 Valencia",
)


def _invoice(**overrides: object) -> Invoice:
    data: dict[str, object] = {
        "invoice_number": "LB-2026-0098",
        "issue_date": date(2026, 9, 10),
        "issuer_name": "Limpiezas Brillo S.L.",
        "issuer_tax_id": "B29444338",
        "recipient_tax_id": "ESB46123451",
        "lines": [
            LineItem(
                description="Cleaning",
                quantity=Decimal(1),
                unit_price=Decimal("420.00"),
                line_total=Decimal("420.00"),
            )
        ],
        "tax_breakdown": [
            TaxLine(base=Decimal("420.00"), rate=Decimal(21), amount=Decimal("88.20"))
        ],
        "subtotal": Decimal("420.00"),
        "vat_total": Decimal("88.20"),
        "total": Decimal("508.20"),
    }
    data.update(overrides)
    return Invoice.model_validate(data)


def test_complete_invoice_has_no_formal_issues() -> None:
    assert check_formal(_invoice(), COMPANY) == []


def test_missing_required_fields_are_reported_one_by_one() -> None:
    issues = check_formal(_invoice(invoice_number=None, issue_date=None), COMPANY)
    assert [(i.code, i.field) for i in issues] == [
        ("MISSING_FIELD", "invoice_number"),
        ("MISSING_FIELD", "issue_date"),
    ]


def test_blank_string_counts_as_missing() -> None:
    issues = check_formal(_invoice(issuer_name="   "), COMPANY)
    assert [(i.code, i.field) for i in issues] == [("MISSING_FIELD", "issuer_name")]


def test_missing_tax_breakdown() -> None:
    issues = check_formal(_invoice(tax_breakdown=[]), COMPANY)
    assert [(i.code, i.field) for i in issues] == [("MISSING_FIELD", "tax_breakdown")]


def test_invalid_issuer_tax_id() -> None:
    issues = check_formal(_invoice(issuer_tax_id="B29444339"), COMPANY)
    assert [(i.code, i.field) for i in issues] == [("INVALID_TAX_ID", "issuer_tax_id")]


def test_wrong_recipient() -> None:
    issues = check_formal(_invoice(recipient_tax_id="B12345674"), COMPANY)
    assert [(i.code, i.field) for i in issues] == [("WRONG_RECIPIENT", "recipient_tax_id")]


def test_invalid_recipient_tax_id_is_not_also_wrong_recipient() -> None:
    issues = check_formal(_invoice(recipient_tax_id="B46123452"), COMPANY)
    assert [i.code for i in issues] == ["INVALID_TAX_ID"]


def test_validate_invoice_combines_formal_and_arithmetic() -> None:
    issues = validate_invoice(_invoice(invoice_number=None, total=Decimal("600.00")), COMPANY)
    assert sorted(i.code for i in issues) == ["MISSING_FIELD", "TOTAL_MISMATCH"]
