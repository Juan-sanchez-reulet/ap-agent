from datetime import date
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    BLOCKER = "blocker"
    WARNING = "warning"


class Issue(BaseModel):
    model_config = ConfigDict(frozen=True)

    code: str
    severity: Severity
    field: str | None = None
    message: str
    evidence: dict[str, str] = Field(default_factory=dict)


class LineItem(BaseModel):
    description: str
    quantity: Decimal
    unit_price: Decimal
    discount_pct: Decimal = Decimal("0")
    vat_rate: Decimal | None = None
    line_total: Decimal


class TaxLine(BaseModel):
    base: Decimal
    rate: Decimal
    amount: Decimal


class Invoice(BaseModel):
    invoice_number: str | None = None
    issue_date: date | None = None
    due_date: date | None = None
    issuer_name: str | None = None
    issuer_tax_id: str | None = None
    issuer_address: str | None = None
    issuer_iban: str | None = None
    recipient_name: str | None = None
    recipient_tax_id: str | None = None
    po_reference: str | None = None
    currency: str = "EUR"
    lines: list[LineItem] = Field(default_factory=list)
    tax_breakdown: list[TaxLine] = Field(default_factory=list)
    irpf_rate: Decimal | None = None
    irpf_amount: Decimal | None = None
    subtotal: Decimal | None = None
    vat_total: Decimal | None = None
    total: Decimal | None = None
    language: str | None = None


class Company(BaseModel):
    name: str
    tax_id: str
    address: str


class VendorType(StrEnum):
    COMPANY = "company"
    PROFESSIONAL = "professional"
    LANDLORD = "landlord"
    EU_COMPANY = "eu_company"


class Vendor(BaseModel):
    id: str
    name: str
    tax_id: str
    address: str
    iban: str
    vendor_type: VendorType
    requires_po: bool = False
    aliases: list[str] = Field(default_factory=list)
    default_account: str


class Account(BaseModel):
    code: str
    name: str
