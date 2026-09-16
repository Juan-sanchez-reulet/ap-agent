"""The fictional company's master data: single source for FakeErp, seeds and evals."""

from pathlib import Path

from pydantic import BaseModel

from apagent.domain import Account, Company, Vendor
from apagent.validation.tax_id import normalize_tax_id


class World(BaseModel):
    company: Company
    vendors: list[Vendor]
    accounts: list[Account]

    def vendor_by_tax_id(self, tax_id: str) -> Vendor | None:
        wanted = normalize_tax_id(tax_id)
        return next((v for v in self.vendors if normalize_tax_id(v.tax_id) == wanted), None)


def load_world(path: Path) -> World:
    return World.model_validate_json(path.read_text(encoding="utf-8"))
