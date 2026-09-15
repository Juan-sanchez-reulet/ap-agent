import pytest
from hypothesis import given
from hypothesis import strategies as st

from apagent.validation.tax_id import (
    DNI_LETTERS,
    is_valid_spanish_tax_id,
    is_valid_tax_id,
    normalize_tax_id,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("B46871232", "B46871232"),
        ("b-46871232", "B46871232"),
        ("ES B46 871 232", "B46871232"),
        ("ESB46871232", "B46871232"),
        ("DE123456789", "DE123456789"),
    ],
)
def test_normalize_tax_id(raw: str, expected: str) -> None:
    assert normalize_tax_id(raw) == expected


@pytest.mark.parametrize(
    "value",
    [
        "12345678Z",  # DNI
        "48291735S",  # DNI
        "X1234567L",  # NIE
        "B46871232",  # CIF, digit control
        "B46123451",
        "P1234567D",  # CIF, letter control required for P
        "ESB46871232",
    ],
)
def test_valid_spanish_tax_ids(value: str) -> None:
    assert is_valid_spanish_tax_id(value)


@pytest.mark.parametrize(
    "value",
    [
        "12345678A",  # wrong DNI letter
        "X1234567A",  # wrong NIE letter
        "B46871233",  # wrong CIF control digit
        "B29444339",  # wrong CIF control digit (used in golden case G007)
        "P12345674",  # P requires a letter control
        "B4687123",  # too short
        "",
    ],
)
def test_invalid_spanish_tax_ids(value: str) -> None:
    assert not is_valid_spanish_tax_id(value)


def test_eu_vat_numbers_accepted_by_format_only() -> None:
    assert is_valid_tax_id("DE123456789")
    assert is_valid_tax_id("FRAB123456789")
    assert not is_valid_tax_id("ZZ123456")
    assert not is_valid_tax_id("B46871233")


@given(st.integers(min_value=0, max_value=99_999_999))
def test_any_dni_with_correct_letter_is_valid(number: int) -> None:
    letter = DNI_LETTERS[number % 23]
    assert is_valid_spanish_tax_id(f"{number:08d}{letter}")
    wrong = DNI_LETTERS[(number + 1) % 23]
    assert not is_valid_spanish_tax_id(f"{number:08d}{wrong}")
