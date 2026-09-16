from apagent.domain import Company, Invoice, Issue
from apagent.validation.arithmetic import check_arithmetic
from apagent.validation.formal import check_formal


def validate_invoice(invoice: Invoice, company: Company) -> list[Issue]:
    """Run every offline validator. Order: formal first, then arithmetic."""
    return [*check_formal(invoice, company), *check_arithmetic(invoice)]


__all__ = ["validate_invoice"]
