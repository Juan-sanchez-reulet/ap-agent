"""Spanish NIF/NIE/CIF checksum validation and EU VAT format checks (offline)."""

import re

DNI_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"
CIF_CONTROL_LETTERS = "JABCDEFGHI"

_DNI_RE = re.compile(r"^\d{8}[A-Z]$")
_NIE_RE = re.compile(r"^[XYZ]\d{7}[A-Z]$")
_CIF_RE = re.compile(r"^[ABCDEFGHJNPQRSUVW]\d{7}[0-9A-J]$")
_EU_VAT_RE = re.compile(
    r"^(AT|BE|BG|CY|CZ|DE|DK|EE|EL|FI|FR|HR|HU|IE|IT|LT|LU|LV|MT|NL|PL|PT|RO|SE|SI|SK)"
    r"[A-Z0-9]{2,13}$"
)


def normalize_tax_id(raw: str) -> str:
    value = re.sub(r"[\s.\-/]", "", raw).upper()
    if value.startswith("ES") and len(value) == 11:
        value = value[2:]
    return value


def _valid_dni(value: str) -> bool:
    return bool(_DNI_RE.match(value)) and DNI_LETTERS[int(value[:8]) % 23] == value[8]


def _valid_nie(value: str) -> bool:
    if not _NIE_RE.match(value):
        return False
    number = int(str("XYZ".index(value[0])) + value[1:8])
    return DNI_LETTERS[number % 23] == value[8]


def _cif_control_digit(digits: str) -> int:
    even = sum(int(digits[i]) for i in (1, 3, 5))
    odd = sum(sum(divmod(int(digits[i]) * 2, 10)) for i in (0, 2, 4, 6))
    return (10 - (even + odd) % 10) % 10


def _valid_cif(value: str) -> bool:
    if not _CIF_RE.match(value):
        return False
    digit = _cif_control_digit(value[1:8])
    as_digit, as_letter = str(digit), CIF_CONTROL_LETTERS[digit]
    control = value[8]
    if value[0] in "PQRSNW":
        return control == as_letter
    if value[0] in "ABEH":
        return control == as_digit
    return control in (as_digit, as_letter)


def is_valid_spanish_tax_id(raw: str) -> bool:
    value = normalize_tax_id(raw)
    return _valid_dni(value) or _valid_nie(value) or _valid_cif(value)


def is_valid_tax_id(raw: str) -> bool:
    """Spanish IDs are checksum-validated; other EU VAT numbers only format-checked."""
    value = normalize_tax_id(raw)
    if is_valid_spanish_tax_id(value):
        return True
    looks_spanish = bool(_DNI_RE.match(value) or _NIE_RE.match(value) or _CIF_RE.match(value))
    return not looks_spanish and bool(_EU_VAT_RE.match(value))
