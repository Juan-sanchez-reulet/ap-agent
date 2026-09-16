"""Formal checks based on Spanish invoicing requirements. Pure functions."""

from apagent.domain import Company, Invoice, Issue, Severity
from apagent.validation import codes
from apagent.validation.tax_id import is_valid_tax_id, normalize_tax_id

REQUIRED_FIELDS = (
    "invoice_number",
    "issue_date",
    "issuer_name",
    "issuer_tax_id",
    "recipient_tax_id",
)


def _is_missing(value: object) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def check_formal(invoice: Invoice, company: Company) -> list[Issue]:
    issues: list[Issue] = []
    for field in REQUIRED_FIELDS:
        if _is_missing(getattr(invoice, field)):
            issues.append(
                Issue(
                    code=codes.MISSING_FIELD,
                    severity=Severity.BLOCKER,
                    field=field,
                    message=f"Required field '{field}' is missing",
                )
            )
    if not invoice.tax_breakdown:
        issues.append(
            Issue(
                code=codes.MISSING_FIELD,
                severity=Severity.BLOCKER,
                field="tax_breakdown",
                message="VAT breakdown (base, rate, amount) is missing",
            )
        )

    for field in ("issuer_tax_id", "recipient_tax_id"):
        value = getattr(invoice, field)
        if not _is_missing(value) and not is_valid_tax_id(value):
            issues.append(
                Issue(
                    code=codes.INVALID_TAX_ID,
                    severity=Severity.BLOCKER,
                    field=field,
                    message=f"'{value}' is not a valid tax ID",
                    evidence={"found": value},
                )
            )

    recipient = invoice.recipient_tax_id
    if (
        recipient is not None
        and not _is_missing(recipient)
        and is_valid_tax_id(recipient)
        and normalize_tax_id(recipient) != normalize_tax_id(company.tax_id)
    ):
        issues.append(
            Issue(
                code=codes.WRONG_RECIPIENT,
                severity=Severity.BLOCKER,
                field="recipient_tax_id",
                message=f"Invoice is addressed to {recipient}, not to {company.tax_id}",
                evidence={"expected": company.tax_id, "found": recipient},
            )
        )
    return issues
