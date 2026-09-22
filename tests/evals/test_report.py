from evals.metrics import DetectionCounts, FieldScore
from evals.report import CaseResult, render_markdown, summarize


def _case(case_id: str, correct: bool, tp: int = 0, fn: int = 0) -> CaseResult:
    return CaseResult(
        case_id=case_id,
        error=None if correct else "EXTRACTION_FAILED: x",
        fields=[FieldScore("total", "1.00", "1.00" if correct else None, correct)],
        issues={"TOTAL_MISMATCH": DetectionCounts(tp=tp, fn=fn)} if tp or fn else {},
        predicted_codes=["TOTAL_MISMATCH"] if tp else [],
        expected_codes=["TOTAL_MISMATCH"] if tp or fn else [],
        llm_calls=1,
        cache_hit=False,
        seconds=2.0,
    )


def test_summarize_aggregates() -> None:
    summary = summarize([_case("G001", True, tp=1), _case("G002", False, fn=1)], model="m")
    assert summary["cases"] == 2
    assert summary["extraction_errors"] == 1
    assert summary["field_accuracy"]["total"] == 0.5
    assert summary["all_critical_fields_correct"] == 0.5
    assert summary["detection"]["TOTAL_MISMATCH"] == {
        "tp": 1,
        "fp": 0,
        "fn": 1,
        "precision": 1.0,
        "recall": 0.5,
    }
    assert summary["detection_overall"]["recall"] == 0.5


def test_render_markdown_contains_tables() -> None:
    results = [_case("G001", True, tp=1)]
    markdown = render_markdown(summarize(results, model="m"), results)
    assert "| total | 100.0% |" in markdown
    assert "| TOTAL_MISMATCH | 1 | 0 | 0 | 100.0% | 100.0% |" in markdown
    assert "G001" in markdown
