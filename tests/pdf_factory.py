"""Build small PDFs for tests. Core fonts are latin-1: use 'EUR', not the euro sign."""

from fpdf import FPDF


def make_text_pdf(lines: list[str]) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in lines:
        pdf.cell(text=line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


def make_blank_pdf() -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.rect(10, 10, 50, 50)
    return bytes(pdf.output())
