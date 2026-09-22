"""Run the extraction + validation eval over a case directory.

Usage: uv run python -m evals.run --cases evals/datasets/golden
"""

import argparse
import json
import subprocess
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from apagent.cache import JsonFileCache
from apagent.config import Settings
from apagent.extraction.extractor import ExtractionResult, InvoiceExtractor
from apagent.llm import get_chat_model
from apagent.validation import validate_invoice
from apagent.world import load_world
from evals.datasets import load_cases
from evals.metrics import score_fields, score_issues
from evals.report import CaseResult, render_markdown, summarize


def _git_sha() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "nogit"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--world", type=Path, default=Path("evals/world.json"))
    parser.add_argument("--out", type=Path, default=Path("evals/results"))
    args = parser.parse_args()

    settings = Settings()
    world = load_world(args.world)
    extractor = InvoiceExtractor.from_chat_model(
        get_chat_model(settings), settings.model, JsonFileCache(settings.cache_dir)
    )

    results: list[CaseResult] = []
    for case in load_cases(args.cases):
        try:
            extraction = extractor.extract_from_pdf(case.pdf_path.read_bytes())
        except Exception as exc:  # network / quota errors must not abort the whole run
            extraction = ExtractionResult(None, None, f"LLM_ERROR: {exc}", 0, False, 0.0)
        predicted = (
            sorted({i.code for i in validate_invoice(extraction.invoice, world.company)})
            if extraction.invoice is not None
            else []
        )
        expected = sorted(set(case.expected.expected_issue_codes))
        measured = not (extraction.error or "").startswith("LLM_ERROR")
        results.append(
            CaseResult(
                case_id=case.expected.case_id,
                error=extraction.error,
                fields=score_fields(case.expected.invoice, extraction.invoice),
                issues=score_issues(set(expected), set(predicted)) if measured else {},
                predicted_codes=predicted,
                expected_codes=expected,
                llm_calls=extraction.llm_calls,
                cache_hit=extraction.cache_hit,
                seconds=extraction.seconds,
            )
        )
        print(
            f"{case.expected.case_id}: error={extraction.error} "
            f"predicted={predicted} expected={expected}"
        )

    summary = summarize(results, model=settings.model)
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H%M")
    run_dir = args.out / f"{stamp}-{_git_sha()}-{args.cases.name}"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "results.json").write_text(
        json.dumps(
            {"summary": summary, "cases": [asdict(r) for r in results]},
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )
    (run_dir / "report.md").write_text(render_markdown(summary, results), encoding="utf-8")
    print(f"\nReport: {run_dir / 'report.md'}")


if __name__ == "__main__":
    main()
