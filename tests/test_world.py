from pathlib import Path

from apagent.validation.tax_id import is_valid_spanish_tax_id, is_valid_tax_id
from apagent.world import load_world

WORLD_PATH = Path("evals/world.json")


def test_world_loads() -> None:
    world = load_world(WORLD_PATH)
    assert world.company.tax_id == "B46123451"
    assert len(world.vendors) == 9


def test_world_tax_ids_are_valid() -> None:
    world = load_world(WORLD_PATH)
    assert is_valid_spanish_tax_id(world.company.tax_id)
    for vendor in world.vendors:
        assert is_valid_tax_id(vendor.tax_id), vendor.id


def test_vendor_ids_unique_and_accounts_known() -> None:
    world = load_world(WORLD_PATH)
    ids = [v.id for v in world.vendors]
    assert len(ids) == len(set(ids))
    codes = {a.code for a in world.accounts}
    for vendor in world.vendors:
        assert vendor.default_account in codes, vendor.id


def test_vendor_lookup_by_tax_id() -> None:
    world = load_world(WORLD_PATH)
    vendor = world.vendor_by_tax_id("ES-B46871232")
    assert vendor is not None and vendor.id == "V001"
    assert world.vendor_by_tax_id("B00000000") is None
