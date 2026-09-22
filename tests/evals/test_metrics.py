from datetime import date
from decimal import Decimal

from apagent.domain import Invoice
from evals.metrics import CRITICAL_FIELDS, DetectionCounts, score_fields, score_issues


def test_score_fields_normalises_values() -> None:
    expected = Invoice(
        invoice_number="PC-2026-0412",
        issue_date=date(2026, 9, 2),
        issuer_tax_id="B46871232",
        recipient_tax_id="B46123451",
        subtotal=Decimal("214"),
        vat_total=Decimal("44.94"),
        total=Decimal("258.94"),
    )
    actual = Invoice(
        invoice_number="pc-2026-0412 ",
        issue_date=date(2026, 9, 2),
        issuer_tax_id="ES-B46871232",
        recipient_tax_id="B46123451",
        subtotal=Decimal("214.00"),
        vat_total=Decimal("44.94"),
        total=Decimal("258.95"),
        irpf_amount=Decimal("0"),
    )
    scores = {s.field: s.correct for s in score_fields(expected, actual)}
    assert set(scores) == set(CRITICAL_FIELDS)
    assert scores["invoice_number"] and scores["issuer_tax_id"] and scores["subtotal"]
    assert scores["irpf_amount"]  # None and 0 are equivalent
    assert not scores["total"]


def test_score_fields_without_extraction_is_all_wrong() -> None:
    scores = score_fields(Invoice(total=Decimal("1")), None)
    assert all(not s.correct for s in scores)


def test_score_issues_counts_per_code() -> None:
    counts = score_issues({"TOTAL_MISMATCH"}, {"TOTAL_MISMATCH", "INVALID_TAX_ID"})
    assert counts["TOTAL_MISMATCH"] == DetectionCounts(tp=1)
    assert counts["INVALID_TAX_ID"] == DetectionCounts(fp=1)
    missed = score_issues({"MISSING_FIELD"}, set())
    assert missed["MISSING_FIELD"] == DetectionCounts(fn=1)


def test_precision_recall() -> None:
    counts = DetectionCounts(tp=3, fp=1, fn=2)
    assert counts.precision == 0.75
    assert counts.recall == 0.6
    assert DetectionCounts().precision is None
    assert (DetectionCounts(tp=1) + DetectionCounts(fn=1)) == DetectionCounts(tp=1, fn=1)
