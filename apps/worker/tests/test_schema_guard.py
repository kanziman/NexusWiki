"""Worker startup enum/CHECK contract regression tests."""

import pytest

from nexuswiki_core.domain import DB_CHECK_ENUMS
from worker.schema_guard import SchemaContractError, assert_enums_match_db


class FakeCatalog:
    def __init__(self, values: dict[tuple[str, str], list[str]]) -> None:
        self.values = values
        self.calls: list[tuple[str, str]] = []

    async def enum_check_values(self, table: str, column: str) -> list[str]:
        self.calls.append((table, column))
        return self.values[(table, column)]


@pytest.mark.asyncio
async def test_schema_guard_checks_every_declared_db_enum() -> None:
    values = {key: [member.value for member in enum] for key, enum in DB_CHECK_ENUMS.items()}
    db = FakeCatalog(values)
    await assert_enums_match_db(db)
    assert set(db.calls) == set(DB_CHECK_ENUMS)
    assert ("jobs", "type") not in db.calls


@pytest.mark.asyncio
async def test_schema_guard_names_both_sides_of_a_mismatch() -> None:
    values = {key: [member.value for member in enum] for key, enum in DB_CHECK_ENUMS.items()}
    values[("wiki_pages", "category")] = ["concepts", "unexpected"]
    with pytest.raises(SchemaContractError, match="wiki_pages.category") as excinfo:
        await assert_enums_match_db(FakeCatalog(values))
    assert "entities" in str(excinfo.value)
    assert "unexpected" in str(excinfo.value)


@pytest.mark.asyncio
async def test_schema_guard_rejects_a_missing_check() -> None:
    values = {key: [member.value for member in enum] for key, enum in DB_CHECK_ENUMS.items()}
    values[("wiki_pages", "category")] = []
    with pytest.raises(SchemaContractError, match="wiki_pages.category"):
        await assert_enums_match_db(FakeCatalog(values))
