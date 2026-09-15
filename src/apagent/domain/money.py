from decimal import ROUND_HALF_UP, Decimal

CENT = Decimal("0.01")


def to_money(value: Decimal | int | float | str) -> Decimal:
    """Convert to a Decimal rounded to cents (half up), avoiding float artefacts."""
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)
