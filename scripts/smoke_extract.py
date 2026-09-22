"""Manual smoke test: one real extraction call against the configured model."""

import json
from pathlib import Path

from apagent.cache import JsonFileCache
from apagent.config import Settings
from apagent.extraction.extractor import InvoiceExtractor
from apagent.llm import get_chat_model
from apagent.validation import validate_invoice
from apagent.world import load_world

DEFAULT_PDF = Path("evals/datasets/golden/G005/invoice.pdf")


def main() -> None:
    settings = Settings()
    extractor = InvoiceExtractor.from_chat_model(
        get_chat_model(settings), settings.model, JsonFileCache(settings.cache_dir)
    )
    result = extractor.extract_from_pdf(DEFAULT_PDF.read_bytes())
    print(
        f"error={result.error} calls={result.llm_calls} "
        f"cache_hit={result.cache_hit} seconds={result.seconds:.1f}"
    )
    if result.invoice is None:
        return
    print(json.dumps(result.invoice.model_dump(mode="json"), indent=2, ensure_ascii=False))
    world = load_world(Path("evals/world.json"))
    for issue in validate_invoice(result.invoice, world.company):
        print(f"ISSUE {issue.code} [{issue.field}] {issue.message}")


if __name__ == "__main__":
    main()
