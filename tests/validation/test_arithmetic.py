from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from apagent.domain import Invoice, LineItem, TaxLine, to_money
from apagent.validation.arithmetic import check_arithmetic


def _invoice(**overrides: object) -> Invoice:
    data: dict[str, object] = {
        "lines": [
            LineItem(
                description="Paper",
                quantity=Decimal(20),
                unit_price=Decimal("4.50"),
                line_total=Decimal("90.00"),
            ),
            LineItem(
                description="Toner",
                quantity=Decimal(2),
                unit_price=Decimal("62.00"),
                line_total=Decimal("124.00"),
            ),
        ],
        "tax_breakdown": [
            TaxLine(base=Decimal("214.00"), rate=Decimal(21), amount=Decimal("44.94"))
        ],
        "subtotal": Decimal("214.00"),
        "vat_total": Decimal("44.94"),
        "total": Decimal("258.94"),
    }
    data.update(overrides)
    return Invoice.model_validate(data)


def _codes(invoice: Invoice) -> list[str]:
    return [issue.code for issue in check_arithmetic(invoice)]


def test_consistent_invoice_has_no_issues() -> None:
    assert _codes(_invoice()) == []


def test_line_total_mismatch() -> None:
    lines = [
        LineItem(
            description="Transport",
            quantity=Decimal(3),
            unit_price=Decimal("145.00"),
            line_total=Decimal("445.00"),
        )
    ]
    invoice = _invoice(
        lines=lines,
        tax_breakdown=[TaxLine(base=Decimal("445.00"), rate=Decimal(21), amount=Decimal("93.45"))],
        subtotal=Decimal("445.00"),
        vat_total=Decimal("93.45"),
        total=Decimal("538.45"),
    )
    issues = check_arithmetic(invoice)
    assert [i.code for i in issues] == ["LINE_TOTAL_MISMATCH"]
    assert issues[0].field == "lines[0].line_total"
    assert issues[0].evidence == {"expected": "435.00", "found": "445.00"}


def test_line_discount_is_applied() -> None:
    lines = [
        LineItem(
            description="Chair",
            quantity=Decimal(2),
            unit_price=Decimal("100.00"),
            discount_pct=Decimal(10),
            line_total=Decimal("180.00"),
        )
    ]
    invoice = _invoice(
        lines=lines,
        tax_breakdown=[TaxLine(base=Decimal("180.00"), rate=Decimal(21), amount=Decimal("37.80"))],
        subtotal=Decimal("180.00"),
        vat_total=Decimal("37.80"),
        total=Decimal("217.80"),
    )
    assert _codes(invoice) == []


def test_subtotal_mismatch_against_lines() -> None:
    invoice = _invoice(
        subtotal=Decimal("200.00"),
        tax_breakdown=[TaxLine(base=Decimal("200.00"), rate=Decimal(21), amount=Decimal("42.00"))],
        vat_total=Decimal("42.00"),
        total=Decimal("242.00"),
    )
    assert _codes(invoice) == ["SUBTOTAL_MISMATCH"]


def test_vat_amount_mismatch() -> None:
    invoice = _invoice(
        tax_breakdown=[TaxLine(base=Decimal("214.00"), rate=Decimal(21), amount=Decimal("40.00"))],
        vat_total=Decimal("40.00"),
        total=Decimal("254.00"),
    )
    assert _codes(invoice) == ["VAT_AMOUNT_MISMATCH"]


def test_vat_total_differs_from_breakdown() -> None:
    invoice = _invoice(vat_total=Decimal("50.00"), total=Decimal("264.00"))
    assert _codes(invoice) == ["VAT_AMOUNT_MISMATCH"]


def test_total_mismatch() -> None:
    assert _codes(_invoice(total=Decimal("268.94"))) == ["TOTAL_MISMATCH"]


def test_irpf_is_subtracted_and_checked() -> None:
    lines = [
        LineItem(
            description="Consulting",
            quantity=Decimal(1),
            unit_price=Decimal("800.00"),
            line_total=Decimal("800.00"),
        )
    ]
    base: dict[str, object] = {
        "lines": lines,
        "tax_breakdown": [
            TaxLine(base=Decimal("800.00"), rate=Decimal(21), amount=Decimal("168.00"))
        ],
        "subtotal": Decimal("800.00"),
        "vat_total": Decimal("168.00"),
        "irpf_rate": Decimal(15),
    }
    assert _codes(_invoice(**base, irpf_amount=Decimal("120.00"), total=Decimal("848.00"))) == []
    assert _codes(_invoice(**base, irpf_amount=Decimal("100.00"), total=Decimal("868.00"))) == [
        "IRPF_AMOUNT_MISMATCH"
    ]


def test_missing_amounts_are_not_reported_as_mismatches() -> None:
    invoice = Invoice(lines=[], tax_breakdown=[], subtotal=None, vat_total=None, total=None)
    assert _codes(invoice) == []


prices = st.decimals(min_value=Decimal("0.01"), max_value=Decimal("9999.99"), places=2)
quantities = st.integers(min_value=1, max_value=500)


@given(
    st.lists(st.tuples(quantities, prices), min_size=1, max_size=15),
    st.sampled_from([0, 4, 10, 21]),
)
def test_any_correctly_computed_invoice_has_no_issues(
    raw_lines: list[tuple[int, Decimal]], rate: int
) -> None:
    lines = [
        LineItem(
            description=f"item {i}",
            quantity=Decimal(q),
            unit_price=p,
            line_total=to_money(Decimal(q) * p),
        )
        for i, (q, p) in enumerate(raw_lines)
    ]
    subtotal = sum((line.line_total for line in lines), Decimal(0))
    vat = to_money(subtotal * rate / 100)
    invoice = Invoice(
        lines=lines,
        tax_breakdown=[TaxLine(base=subtotal, rate=Decimal(rate), amount=vat)],
        subtotal=subtotal,
        vat_total=vat,
        total=subtotal + vat,
    )
    assert check_arithmetic(invoice) == []
