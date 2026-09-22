from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from apagent.domain import Invoice


class ExpectedCase(BaseModel):
    case_id: str
    description: str
    source: Literal["manual_template", "synthetic", "own_invoice"]
    invoice: Invoice
    expected_issue_codes: list[str]


@dataclass(frozen=True)
class EvalCase:
    expected: ExpectedCase
    pdf_path: Path


def load_cases(directory: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    for folder in sorted(p for p in directory.iterdir() if p.is_dir()):
        expected = ExpectedCase.model_validate_json(
            (folder / "expected.json").read_text(encoding="utf-8")
        )
        if expected.case_id != folder.name:
            raise ValueError(f"{folder.name}: case_id is {expected.case_id!r}")
        cases.append(EvalCase(expected=expected, pdf_path=folder / "invoice.pdf"))
    return cases
