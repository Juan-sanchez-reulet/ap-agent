import pytest

from apagent.extraction.pdf import PdfReadError, read_pdf_text
from tests.pdf_factory import make_blank_pdf, make_text_pdf


def test_reads_text_layer() -> None:
    result = read_pdf_text(make_text_pdf(["FACTURA Nº PC-2026-0412", "Total: 258,94 EUR"]))
    assert result.page_count == 1
    assert "PC-2026-0412" in result.text
    assert result.has_text_layer


def test_blank_pdf_has_no_text_layer() -> None:
    result = read_pdf_text(make_blank_pdf())
    assert result.page_count == 1
    assert not result.has_text_layer


def test_non_pdf_raises() -> None:
    with pytest.raises(PdfReadError):
        read_pdf_text(b"this is not a pdf")
