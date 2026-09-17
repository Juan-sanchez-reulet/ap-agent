from dataclasses import dataclass
from io import BytesIO

import pdfplumber

MIN_TEXT_CHARS = 20


class PdfReadError(Exception):
    """The bytes could not be parsed as a PDF."""


@dataclass(frozen=True)
class PdfText:
    page_count: int
    text: str

    @property
    def has_text_layer(self) -> bool:
        return len(self.text.strip()) >= MIN_TEXT_CHARS


def read_pdf_text(data: bytes) -> PdfText:
    try:
        with pdfplumber.open(BytesIO(data)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages]
    except Exception as exc:  # pdfminer raises several unrelated exception types
        raise PdfReadError(str(exc)) from exc
    return PdfText(page_count=len(pages), text="\n\n".join(pages).strip())
