"""Contract tests for data_map.json (Module 20b, Task 1 "Done when").

This validates the governance artifact itself: it must cover the whole data
lifecycle (not just the source document), and every store must carry an owner,
purpose, retention, and deletion decision. The required categories and keys are
hand-written here as the contract; the test asserts the file satisfies them.

Run:
    uv run pytest modules/20b-governance-privacy/py/test_data_map.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

DATA_MAP_PATH = Path(__file__).resolve().parent.parent / "data_map.json"

# Task 1 requires the map to reach past the source document into the derived and
# operational stores. Each must be represented at least once.
REQUIRED_CATEGORIES = {
    "app_db",
    "prompt",
    "provider",
    "embeddings",
    "cache",
    "logs",
    "tracing",
    "feedback",
    "tools",
    "derived",
    "backups",
}

REQUIRED_STORE_KEYS = {
    "id",
    "category",
    "data_class",
    "purpose",
    "owner",
    "access_control",
    "retention",
    "deletion_mechanism",
}

VALID_DATA_CLASSES = {"public", "internal", "confidential", "restricted"}


@pytest.fixture(scope="module")
def data_map() -> dict:
    with DATA_MAP_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def test_data_map_exists_and_parses(data_map: dict) -> None:
    assert isinstance(data_map["stores"], list)
    assert len(data_map["stores"]) >= len(REQUIRED_CATEGORIES)


def test_covers_full_lifecycle_categories(data_map: dict) -> None:
    categories = {store["category"] for store in data_map["stores"]}
    missing = REQUIRED_CATEGORIES - categories
    assert missing == set(), f"data map is missing lifecycle stores: {sorted(missing)}"


def test_every_store_has_governance_decisions(data_map: dict) -> None:
    for store in data_map["stores"]:
        missing = REQUIRED_STORE_KEYS - store.keys()
        assert missing == set(), f"{store.get('id')} missing keys: {sorted(missing)}"
        # Owner, purpose, retention, and deletion must be real decisions, not blanks.
        for key in ("owner", "purpose", "retention", "deletion_mechanism"):
            assert store[key].strip(), f"{store['id']} has empty {key}"
        assert store["data_class"] in VALID_DATA_CLASSES


def test_store_ids_are_unique(data_map: dict) -> None:
    ids = [store["id"] for store in data_map["stores"]]
    assert len(ids) == len(set(ids))


def test_declares_not_legal_advice(data_map: dict) -> None:
    assert data_map["not_legal_advice"] is True
