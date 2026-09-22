from pathlib import Path
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableLambda

from apagent.cache import JsonFileCache
from apagent.extraction.extractor import InvoiceExtractor
from apagent.extraction.schema import ExtractedInvoice, ExtractedLine, ExtractedTaxLine
from tests.pdf_factory import make_blank_pdf, make_text_pdf

VALID = ExtractedInvoice(
    invoice_number="PC-2026-0412",
    issue_date="2026-09-02",
    issuer_tax_id="B46871232",
    lines=[ExtractedLine(description="Toner", quantity=2, unit_price=62, line_total=124)],
    tax_breakdown=[ExtractedTaxLine(base=124, rate=21, amount=26.04)],
    subtotal=124,
    vat_total=26.04,
    total=150.04,
)


class ScriptedLLM:
    """Returns (or raises) the scripted outputs in order and records the prompts."""

    def __init__(self, *outputs: Any) -> None:
        self.outputs = list(outputs)
        self.calls: list[list[BaseMessage]] = []

    def __call__(self, messages: list[BaseMessage]) -> Any:
        self.calls.append(messages)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


def _extractor(llm: ScriptedLLM, cache: JsonFileCache | None = None) -> InvoiceExtractor:
    return InvoiceExtractor(RunnableLambda(llm), model_name="fake", cache=cache)


def test_extracts_on_first_try() -> None:
    llm = ScriptedLLM(VALID)
    result = _extractor(llm).extract_from_text("invoice text")
    assert result.error is None
    assert result.invoice is not None and result.invoice.invoice_number == "PC-2026-0412"
    assert result.llm_calls == 1
    assert "Transcribe values exactly as printed" in str(llm.calls[0][0].content)


def test_retries_once_with_error_feedback() -> None:
    bad_date = VALID.model_copy(update={"issue_date": "02/09/2026"})
    llm = ScriptedLLM(bad_date, VALID)
    result = _extractor(llm).extract_from_text("invoice text")
    assert result.invoice is not None
    assert result.llm_calls == 2
    assert "previous answer was invalid" in str(llm.calls[1][-1].content)


def test_gives_up_after_two_invalid_answers() -> None:
    llm = ScriptedLLM(OutputParserException("bad json"), OutputParserException("bad json"))
    result = _extractor(llm).extract_from_text("invoice text")
    assert result.invoice is None
    assert result.error is not None and result.error.startswith("EXTRACTION_FAILED")
    assert result.llm_calls == 2


def test_cache_hit_skips_llm(tmp_path: Path) -> None:
    cache = JsonFileCache(tmp_path)
    first = _extractor(ScriptedLLM(VALID), cache).extract_from_text("same text")
    llm = ScriptedLLM()
    second = _extractor(llm, cache).extract_from_text("same text")
    assert first.invoice == second.invoice
    assert second.cache_hit and second.llm_calls == 0 and llm.calls == []


def test_dict_output_is_accepted() -> None:
    llm = ScriptedLLM(VALID.model_dump())
    assert _extractor(llm).extract_from_text("text").invoice is not None


def test_pdf_without_text_layer_is_reported() -> None:
    result = _extractor(ScriptedLLM()).extract_from_pdf(make_blank_pdf())
    assert result.error == "NO_TEXT_LAYER"


def test_unreadable_pdf_is_reported() -> None:
    result = _extractor(ScriptedLLM()).extract_from_pdf(b"not a pdf")
    assert result.error is not None and result.error.startswith("PDF_UNREADABLE")


def test_pdf_text_is_sent_to_llm() -> None:
    llm = ScriptedLLM(VALID)
    _extractor(llm).extract_from_pdf(make_text_pdf(["FACTURA PC-2026-0412", "Total 150,04 EUR"]))
    assert "PC-2026-0412" in str(llm.calls[0][-1].content)
