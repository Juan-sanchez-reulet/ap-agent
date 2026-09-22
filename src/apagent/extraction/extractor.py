"""PDF/text -> Invoice using a structured-output chat model, with retry and cache."""

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.runnables import Runnable
from pydantic import ValidationError

from apagent.cache import JsonFileCache
from apagent.domain import Invoice
from apagent.extraction.pdf import PdfReadError, read_pdf_text
from apagent.extraction.schema import ConversionError, ExtractedInvoice, to_invoice

PROMPT_VERSION = "extract-v1"

SYSTEM_PROMPT = """You extract data from supplier invoices for an accounts-payable system.

Rules:
- Transcribe values exactly as printed. Never correct, recompute or infer amounts, tax IDs \
or dates. If the invoice's arithmetic or tax ID is wrong, copy the wrong value.
- If a field is not on the document, return null. Do not guess.
- Dates: convert to YYYY-MM-DD.
- Amounts: plain numbers with a dot as decimal separator (1.633,50 -> 1633.50), no symbols.
- Tax IDs and IBANs: copy as printed, without spaces.
- The issuer is the company sending the invoice; the recipient is the company being billed.
- tax_breakdown: one entry per VAT rate with taxable base, rate (e.g. 21) and VAT amount.
- irpf_rate / irpf_amount: withholding ("retención IRPF") as positive numbers, or null.
- language: ISO 639-1 code of the document language."""


@dataclass(frozen=True)
class ExtractionResult:
    invoice: Invoice | None
    raw: ExtractedInvoice | None
    error: str | None
    llm_calls: int
    cache_hit: bool
    seconds: float


class InvoiceExtractor:
    def __init__(
        self,
        structured_llm: Runnable[Any, Any],
        model_name: str,
        cache: JsonFileCache | None = None,
        max_attempts: int = 2,
    ) -> None:
        self.structured_llm = structured_llm
        self.model_name = model_name
        self.cache = cache
        self.max_attempts = max_attempts

    @classmethod
    def from_chat_model(
        cls, llm: BaseChatModel, model_name: str, cache: JsonFileCache | None = None
    ) -> "InvoiceExtractor":
        return cls(llm.with_structured_output(ExtractedInvoice), model_name, cache)

    def extract_from_pdf(self, data: bytes) -> ExtractionResult:
        try:
            pdf = read_pdf_text(data)
        except PdfReadError as exc:
            return ExtractionResult(None, None, f"PDF_UNREADABLE: {exc}", 0, False, 0.0)
        if not pdf.has_text_layer:
            return ExtractionResult(None, None, "NO_TEXT_LAYER", 0, False, 0.0)
        return self.extract_from_text(pdf.text)

    def extract_from_text(self, text: str) -> ExtractionResult:
        start = perf_counter()
        key = JsonFileCache.make_key(model=self.model_name, prompt=PROMPT_VERSION, text=text)
        if self.cache is not None and (cached := self.cache.get(key)) is not None:
            raw = ExtractedInvoice.model_validate(cached)
            return ExtractionResult(to_invoice(raw), raw, None, 0, True, perf_counter() - start)

        base: list[BaseMessage] = [
            SystemMessage(SYSTEM_PROMPT),
            HumanMessage(f"Invoice text:\n\n{text}"),
        ]
        messages = base
        last_error = ""
        for attempt in range(1, self.max_attempts + 1):
            try:
                output = self.structured_llm.invoke(messages)
                raw = (
                    output
                    if isinstance(output, ExtractedInvoice)
                    else ExtractedInvoice.model_validate(output)
                )
                invoice = to_invoice(raw)
            except (OutputParserException, ValidationError, ConversionError) as exc:
                last_error = str(exc)
                messages = [
                    *base,
                    HumanMessage(
                        f"Your previous answer was invalid: {last_error}. "
                        "Return a corrected answer."
                    ),
                ]
                continue
            if self.cache is not None:
                self.cache.set(key, raw.model_dump(mode="json"))
            return ExtractionResult(invoice, raw, None, attempt, False, perf_counter() - start)

        return ExtractionResult(
            None,
            None,
            f"EXTRACTION_FAILED: {last_error}",
            self.max_attempts,
            False,
            perf_counter() - start,
        )
