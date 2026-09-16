"""Arithmetic consistency checks. Pure functions: no LLM, no I/O."""

from decimal import Decimal

from apagent.domain import Invoice, Issue, Severity, to_money
from apagent.validation import codes

TOLERANCE = Decimal("0.01")


def _differs(expected: Decimal, found: Decimal) -> bool:
    return abs(expected - found) > TOLERANCE


def _issue(code: str, field: str, message: str, expected: Decimal, found: Decimal) -> Issue:
    return Issue(
        code=code,
        severity=Severity.BLOCKER,
        field=field,
        message=message,
        evidence={"expected": str(to_money(expected)), "found": str(to_money(found))},
    )


def check_line_totals(invoice: Invoice) -> list[Issue]:
    issues: list[Issue] = []
    for index, line in enumerate(invoice.lines):
        expected = to_money(line.quantity * line.unit_price * (100 - line.discount_pct) / 100)
        if _differs(expected, line.line_total):
            issues.append(
                _issue(
                    codes.LINE_TOTAL_MISMATCH,
                    f"lines[{index}].line_total",
                    f"Line {index + 1}: {line.quantity} x {line.unit_price} should be "
                    f"{expected}, invoice says {line.line_total}",
                    expected,
                    line.line_total,
                )
            )
    return issues


def check_subtotal(invoice: Invoice) -> list[Issue]:
    if invoice.subtotal is None:
        return []
    issues: list[Issue] = []
    if invoice.lines:
        lines_sum = sum((line.line_total for line in invoice.lines), Decimal(0))
        if _differs(lines_sum, invoice.subtotal):
            issues.append(
                _issue(
                    codes.SUBTOTAL_MISMATCH,
                    "subtotal",
                    f"Sum of lines is {lines_sum}, subtotal says {invoice.subtotal}",
                    lines_sum,
                    invoice.subtotal,
                )
            )
    if invoice.tax_breakdown:
        bases_sum = sum((tax.base for tax in invoice.tax_breakdown), Decimal(0))
        if _differs(bases_sum, invoice.subtotal):
            issues.append(
                _issue(
                    codes.SUBTOTAL_MISMATCH,
                    "tax_breakdown",
                    f"Sum of tax bases is {bases_sum}, subtotal says {invoice.subtotal}",
                    bases_sum,
                    invoice.subtotal,
                )
            )
    return issues


def check_vat(invoice: Invoice) -> list[Issue]:
    issues: list[Issue] = []
    for index, tax in enumerate(invoice.tax_breakdown):
        expected = to_money(tax.base * tax.rate / 100)
        if _differs(expected, tax.amount):
            issues.append(
                _issue(
                    codes.VAT_AMOUNT_MISMATCH,
                    f"tax_breakdown[{index}].amount",
                    f"{tax.rate}% of {tax.base} is {expected}, invoice says {tax.amount}",
                    expected,
                    tax.amount,
                )
            )
    if invoice.vat_total is not None and invoice.tax_breakdown:
        amounts_sum = sum((tax.amount for tax in invoice.tax_breakdown), Decimal(0))
        if _differs(amounts_sum, invoice.vat_total):
            issues.append(
                _issue(
                    codes.VAT_AMOUNT_MISMATCH,
                    "vat_total",
                    f"Sum of VAT amounts is {amounts_sum}, VAT total says {invoice.vat_total}",
                    amounts_sum,
                    invoice.vat_total,
                )
            )
    return issues


def check_irpf(invoice: Invoice) -> list[Issue]:
    if invoice.irpf_rate is None or invoice.irpf_amount is None or invoice.subtotal is None:
        return []
    expected = to_money(invoice.subtotal * invoice.irpf_rate / 100)
    if _differs(expected, invoice.irpf_amount):
        return [
            _issue(
                codes.IRPF_AMOUNT_MISMATCH,
                "irpf_amount",
                f"{invoice.irpf_rate}% IRPF of {invoice.subtotal} is {expected}, "
                f"invoice says {invoice.irpf_amount}",
                expected,
                invoice.irpf_amount,
            )
        ]
    return []


def check_total(invoice: Invoice) -> list[Issue]:
    if invoice.total is None or invoice.subtotal is None or invoice.vat_total is None:
        return []
    expected = invoice.subtotal + invoice.vat_total - (invoice.irpf_amount or Decimal(0))
    if _differs(expected, invoice.total):
        return [
            _issue(
                codes.TOTAL_MISMATCH,
                "total",
                f"Subtotal + VAT - IRPF is {expected}, total says {invoice.total}",
                expected,
                invoice.total,
            )
        ]
    return []


def check_arithmetic(invoice: Invoice) -> list[Issue]:
    return [
        *check_line_totals(invoice),
        *check_subtotal(invoice),
        *check_vat(invoice),
        *check_irpf(invoice),
        *check_total(invoice),
    ]
