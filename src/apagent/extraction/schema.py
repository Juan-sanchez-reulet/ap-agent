"""LLM-facing extraction schema (primitive types only) and conversion to the domain model."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from apagent.domain import Invoice, LineItem, TaxLine, to_money


class ConversionError(ValueError):
    """Extracted data could not be converted into a domain Invoice."""


class ExtractedLine(BaseModel):
    description: str | None = Field(default=None, description="Line description as printed")
    quantity: float | None = Field(default=None, description="Quantity as printed")
    unit_price: float | None = Field(default=None, description="Unit price before VAT")
    discount_pct: float | None = Field(default=None, description="Discount %, e.g. 10 for 10%")
    vat_rate: float | None = Field(default=None, description="VAT % for this line, e.g. 21")
    line_total: float | None = Field(default=None, description="Line amount before VAT")


class ExtractedTaxLine(BaseModel):
    base: float | None = Field(default=None, description="Taxable base for this VAT rate")
    rate: float | None = Field(default=None, description="VAT %, e.g. 21")
    amount: float | None = Field(default=None, description="VAT amount for this rate")


class ExtractedInvoice(BaseModel):
    invoice_number: str | None = Field(default=None, description="Invoice number as printed")
    issue_date: str | None = Field(default=None, description="Issue date as YYYY-MM-DD")
    due_date: str | None = Field(default=None, description="Due date as YYYY-MM-DD")
    issuer_name: str | None = Field(default=None, description="Legal name of the sender")
    issuer_tax_id: str | None = Field(default=None, description="Sender NIF/CIF/VAT number")
    issuer_address: str | None = None
    issuer_iban: str | None = Field(default=None, description="Sender IBAN, without spaces")
    recipient_name: str | None = Field(default=None, description="Legal name of the billed party")
    recipient_tax_id: str | None = Field(default=None, description="Billed party NIF/CIF/VAT")
    po_reference: str | None = Field(default=None, description="Purchase order reference")
    currency: str | None = Field(default=None, description="ISO 4217 code, e.g. EUR")
    lines: list[ExtractedLine] = Field(default_factory=list)
    tax_breakdown: list[ExtractedTaxLine] = Field(default_factory=list)
    irpf_rate: float | None = Field(default=None, description="IRPF withholding %, positive")
    irpf_amount: float | None = Field(default=None, description="IRPF withholding, positive")
    subtotal: float | None = Field(default=None, description="Total taxable base before VAT")
    vat_total: float | None = Field(default=None, description="Total VAT amount")
    total: float | None = Field(default=None, description="Amount payable as printed")
    language: str | None = Field(default=None, description="ISO 639-1 code, e.g. es")


def _text(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    return value.strip()


def _date(value: str | None, field: str) -> date | None:
    text = _text(value)
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ConversionError(f"{field}: {text!r} is not a YYYY-MM-DD date") from exc


def _money(value: float | None) -> Decimal | None:
    return None if value is None else to_money(value)


def _rate(value: float | None) -> Decimal | None:
    return None if value is None else Decimal(str(value))


def _line(line: ExtractedLine, index: int) -> LineItem:
    if line.line_total is None:
        raise ConversionError(f"lines[{index}].line_total is missing")
    line_total = to_money(line.line_total)
    quantity = Decimal(str(line.quantity)) if line.quantity is not None else Decimal(1)
    unit_price = to_money(line.unit_price) if line.unit_price is not None else line_total
    return LineItem(
        description=_text(line.description) or "",
        quantity=quantity,
        unit_price=unit_price,
        discount_pct=(
            Decimal(str(line.discount_pct)) if line.discount_pct is not None else Decimal(0)
        ),
        vat_rate=_rate(line.vat_rate),
        line_total=line_total,
    )


def _tax_line(tax: ExtractedTaxLine, index: int) -> TaxLine:
    if tax.base is None or tax.rate is None or tax.amount is None:
        raise ConversionError(f"tax_breakdown[{index}] needs base, rate and amount")
    return TaxLine(
        base=to_money(tax.base), rate=Decimal(str(tax.rate)), amount=to_money(tax.amount)
    )


def to_invoice(extracted: ExtractedInvoice) -> Invoice:
    return Invoice(
        invoice_number=_text(extracted.invoice_number),
        issue_date=_date(extracted.issue_date, "issue_date"),
        due_date=_date(extracted.due_date, "due_date"),
        issuer_name=_text(extracted.issuer_name),
        issuer_tax_id=_text(extracted.issuer_tax_id),
        issuer_address=_text(extracted.issuer_address),
        issuer_iban=_text(extracted.issuer_iban),
        recipient_name=_text(extracted.recipient_name),
        recipient_tax_id=_text(extracted.recipient_tax_id),
        po_reference=_text(extracted.po_reference),
        currency=_text(extracted.currency) or "EUR",
        lines=[_line(line, i) for i, line in enumerate(extracted.lines)],
        tax_breakdown=[_tax_line(tax, i) for i, tax in enumerate(extracted.tax_breakdown)],
        irpf_rate=_rate(extracted.irpf_rate),
        irpf_amount=_money(extracted.irpf_amount),
        subtotal=_money(extracted.subtotal),
        vat_total=_money(extracted.vat_total),
        total=_money(extracted.total),
        language=_text(extracted.language),
    )
