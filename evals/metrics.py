import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from apagent.domain import Invoice, to_money
from apagent.validation.tax_id import normalize_tax_id

CRITICAL_FIELDS = (
    "invoice_number",
    "issue_date",
    "issuer_tax_id",
    "recipient_tax_id",
    "subtotal",
    "vat_total",
    "irpf_amount",
    "total",
)


@dataclass(frozen=True)
class FieldScore:
    field: str
    expected: str | None
    actual: str | None
    correct: bool


def normalize_field(field: str, value: object) -> str | None:
    """Compare what matters: 'no withholding' is the same whether it is null or 0.00."""
    if value is None:
        return "0.00" if field == "irpf_amount" else None
    if field.endswith("tax_id"):
        return normalize_tax_id(str(value))
    if isinstance(value, Decimal):
        return str(to_money(value))
    if isinstance(value, date):
        return value.isoformat()
    return re.sub(r"\s+", "", str(value)).upper()


def score_fields(expected: Invoice, actual: Invoice | None) -> list[FieldScore]:
    scores: list[FieldScore] = []
    for field in CRITICAL_FIELDS:
        exp = normalize_field(field, getattr(expected, field))
        act = normalize_field(field, getattr(actual, field)) if actual is not None else None
        scores.append(FieldScore(field, exp, act, actual is not None and exp == act))
    return scores


@dataclass(frozen=True)
class DetectionCounts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def __add__(self, other: "DetectionCounts") -> "DetectionCounts":
        return DetectionCounts(self.tp + other.tp, self.fp + other.fp, self.fn + other.fn)

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None


def score_issues(expected: set[str], actual: set[str]) -> dict[str, DetectionCounts]:
    return {
        code: DetectionCounts(
            tp=int(code in expected and code in actual),
            fp=int(code in actual and code not in expected),
            fn=int(code in expected and code not in actual),
        )
        for code in sorted(expected | actual)
    }
