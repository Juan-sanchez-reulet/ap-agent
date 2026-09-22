from pathlib import Path

import pytest

from apagent.validation import validate_invoice
from apagent.world import load_world
from evals.datasets import EvalCase, load_cases

GOLDEN_DIR = Path("evals/datasets/golden")
CASES = load_cases(GOLDEN_DIR) if GOLDEN_DIR.exists() else []


@pytest.mark.skipif(not CASES, reason="no golden cases yet")
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.expected.case_id)
def test_expected_issues_match_validators(case: EvalCase) -> None:
    world = load_world(Path("evals/world.json"))
    codes = {issue.code for issue in validate_invoice(case.expected.invoice, world.company)}
    assert codes == set(case.expected.expected_issue_codes)


@pytest.mark.skipif(not CASES, reason="no golden cases yet")
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.expected.case_id)
def test_pdf_exists(case: EvalCase) -> None:
    assert case.pdf_path.is_file(), f"missing {case.pdf_path}"


def test_case_id_must_match_folder(tmp_path: Path) -> None:
    folder = tmp_path / "G999"
    folder.mkdir()
    (folder / "expected.json").write_text(
        '{"case_id": "G001", "description": "x", "source": "manual_template", '
        '"invoice": {}, "expected_issue_codes": []}',
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="G999"):
        load_cases(tmp_path)
