"""Worker startup Python enum ↔ PostgreSQL CHECK contract guard.

관련 태스크: P2-LLM-01
설계 근거: 03-08-PLAN.md, supabase/migrations/0001_core_schema.sql
"""

from __future__ import annotations

from typing import Protocol

from nexuswiki_core.domain import DB_CHECK_ENUMS
from nexuswiki_core.logging import get_logger

_logger = get_logger(__name__)


class CatalogDb(Protocol):
    async def enum_check_values(self, table: str, column: str) -> list[str]: ...


class SchemaContractError(RuntimeError):
    """The application enum no longer matches the database CHECK constraint."""


async def assert_enums_match_db(db: CatalogDb, *, mapping: dict = DB_CHECK_ENUMS) -> None:
    """Fail startup before enum drift spends LLM cost and hits a 23514 INSERT."""
    for (table, column), enum in mapping.items():
        expected = {member.value for member in enum}
        actual = set(await db.enum_check_values(table, column))
        if expected != actual:
            raise SchemaContractError(
                f"schema enum mismatch for {table}.{column}: "
                f"only_python={sorted(expected - actual)}, only_db={sorted(actual - expected)}"
            )
    _logger.info("worker.schema_contract_ok", enum_count=len(mapping))
