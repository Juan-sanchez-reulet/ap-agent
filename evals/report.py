from dataclasses import dataclass
from functools import reduce
from typing import Any

from evals.metrics import CRITICAL_FIELDS, DetectionCounts, FieldScore


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    error: str | None
    fields: list[FieldScore]
    issues: dict[str, DetectionCounts]
    predicted_codes: list[str]
    expected_codes: list[str]
    llm_calls: int
    cache_hit: bool
    seconds: float


def _counts_dict(counts: DetectionCounts) -> dict[str, Any]:
    return {
        "tp": counts.tp,
        "fp": counts.fp,
        "fn": counts.fn,
        "precision": counts.precision,
        "recall": counts.recall,
    }


def summarize(results: list[CaseResult], model: str) -> dict[str, Any]:
    n = len(results)
    field_accuracy = (
        {
            field: sum(s.correct for r in results for s in r.fields if s.field == field) / n
            for field in CRITICAL_FIELDS
        }
        if n
        else {}
    )
    per_code: dict[str, DetectionCounts] = {}
    for result in results:
        for code, counts in result.issues.items():
            per_code[code] = per_code.get(code, DetectionCounts()) + counts
    overall = reduce(lambda a, b: a + b, per_code.values(), DetectionCounts())
    return {
        "model": model,
        "cases": n,
        "extraction_errors": sum(r.error is not None for r in results),
        "field_accuracy": field_accuracy,
        "all_critical_fields_correct": (
            sum(all(s.correct for s in r.fields) for r in results) / n if n else 0.0
        ),
        "detection": {code: _counts_dict(c) for code, c in sorted(per_code.items())},
        "detection_overall": _counts_dict(overall),
        "llm_calls": sum(r.llm_calls for r in results),
        "seconds_total": round(sum(r.seconds for r in results), 1),
    }


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_markdown(summary: dict[str, Any], results: list[CaseResult]) -> str:
    out = [
        f"# Eval report — {summary['model']}",
        "",
        f"- Cases: {summary['cases']} · extraction errors: {summary['extraction_errors']}",
        f"- All critical fields correct: {_pct(summary['all_critical_fields_correct'])}",
        f"- Overall detection: precision {_pct(summary['detection_overall']['precision'])}, "
        f"recall {_pct(summary['detection_overall']['recall'])}",
        f"- LLM calls: {summary['llm_calls']} · time: {summary['seconds_total']} s",
        "",
        "## Extraction accuracy by field",
        "",
        "| Field | Accuracy |",
        "|---|---|",
        *[f"| {field} | {_pct(acc)} |" for field, acc in summary["field_accuracy"].items()],
        "",
        "## Exception detection by code",
        "",
        "| Code | TP | FP | FN | Precision | Recall |",
        "|---|---|---|---|---|---|",
        *[
            f"| {code} | {c['tp']} | {c['fp']} | {c['fn']} | {_pct(c['precision'])} | "
            f"{_pct(c['recall'])} |"
            for code, c in summary["detection"].items()
        ],
        "",
        "## Cases",
        "",
        "| Case | Error | Wrong fields | Expected codes | Predicted codes |",
        "|---|---|---|---|---|",
    ]
    for r in results:
        wrong = (
            ", ".join(f"{s.field} ({s.expected}→{s.actual})" for s in r.fields if not s.correct)
            or "—"
        )
        out.append(
            f"| {r.case_id} | {r.error or '—'} | {wrong} | "
            f"{', '.join(r.expected_codes) or '—'} | {', '.join(r.predicted_codes) or '—'} |"
        )
    return "\n".join(out) + "\n"
