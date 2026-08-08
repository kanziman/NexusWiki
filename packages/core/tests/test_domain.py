"""도메인 enum이 DB CHECK 제약과 글자 그대로 같은지 고정하는 회귀 테스트.

⚠️ 이 파일의 핵심은 마지막 두 테스트다 — 상수를 상수와 비교하는 것이 아니라
**마이그레이션 파일에서 CHECK 리터럴을 실제로 읽어** 대조한다. 파이썬 쪽에 값을
손으로 베껴 적기만 하면 나중에 마이그레이션이 값을 늘렸을 때 아무 테스트도 깨지지
않고, 워커는 DB가 거부하는 값을 조용히 만들어 낸다.
"""

import re
from pathlib import Path

from nexuswiki_core.domain import (
    DB_CHECK_ENUMS,
    EmbeddingScope,
    JobStatus,
    JobType,
    MemberRole,
    PromptTargetType,
    SourceType,
    UsageKind,
    VerificationStatus,
    WikiCategory,
    WikiConfidence,
)

# packages/core/tests/test_domain.py → parents[3] 가 저장소 루트다.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_MIGRATIONS_DIR = _REPO_ROOT / "supabase" / "migrations"

_TABLE_RE = re.compile(
    r"(?:create|alter)\s+table\s+(?:if\s+not\s+exists\s+)?public\.(\w+)", re.IGNORECASE
)
_CHECK_IN_RE = re.compile(r"check\s*\(\s*(\w+)\s+in\s*\(([^)]*)\)", re.IGNORECASE)
_LITERAL_RE = re.compile(r"'([^']*)'")


def _check_enums_from_migrations() -> dict[tuple[str, str], frozenset[str]]:
    """마이그레이션 전체를 파일명 순서로 읽어 `check (col in (...))` 리터럴을 모은다.

    같은 `(table, column)`이 여러 번 나오면 **뒤에 오는 파일이 이긴다** — 마이그레이션
    번호가 곧 적용 순서이므로 `0009`가 `0003`의 `jobs.status`를 덮는 것이 실제 DB 상태다.

    `kind` 처럼 이름이 겹치는 컬럼이 여러 테이블에 있으므로(`workspaces.kind` ·
    `usage_events.kind`) CHECK 하나하나를 **직전 `create/alter table` 문**에 귀속시킨다.
    """
    found: dict[tuple[str, str], frozenset[str]] = {}
    for path in sorted(_MIGRATIONS_DIR.glob("[0-9][0-9][0-9][0-9]_*.sql")):
        sql = path.read_text(encoding="utf-8")
        tables = [(match.start(), match.group(1)) for match in _TABLE_RE.finditer(sql)]
        for check in _CHECK_IN_RE.finditer(sql):
            table = None
            for position, name in tables:
                if position >= check.start():
                    break
                table = name
            if table is None:
                continue
            found[(table, check.group(1))] = frozenset(_LITERAL_RE.findall(check.group(2)))
    return found


def test_wiki_category_values() -> None:
    assert {member.value for member in WikiCategory} == {
        "concepts",
        "entities",
        "guides",
        "maps",
    }


def test_wiki_confidence_values() -> None:
    assert {member.value for member in WikiConfidence} == {"high", "medium", "low"}


def test_verification_status_values() -> None:
    assert {member.value for member in VerificationStatus} == {
        "verified",
        "partial",
        "unverified",
        "disputed",
    }


def test_source_type_values() -> None:
    assert {member.value for member in SourceType} == {
        "article",
        "paper",
        "book",
        "transcript",
        "clipping",
        "file",
        "text",
        "url",
    }


def test_job_status_includes_canceled_from_0009() -> None:
    # `0003`은 5값이었고 `0009`가 협조적 취소를 위해 canceled를 더했다 (03-02 D-P3).
    assert {member.value for member in JobStatus} == {
        "queued",
        "running",
        "succeeded",
        "failed",
        "dead",
        "canceled",
    }


def test_member_role_values() -> None:
    assert {member.value for member in MemberRole} == {"owner", "editor", "viewer"}


def test_prompt_target_type_values() -> None:
    assert {member.value for member in PromptTargetType} == {"compile", "ask"}


def test_usage_kind_values() -> None:
    assert {member.value for member in UsageKind} == {"llm", "embedding"}


def test_str_enum_members_compare_equal_to_plain_strings() -> None:
    # Pydantic이 직렬화한 값이 그대로 DB 값이 되려면 str의 하위 타입이어야 한다.
    assert isinstance(WikiCategory.CONCEPTS, str)
    assert WikiCategory.CONCEPTS == "concepts"
    assert JobStatus.CANCELED == "canceled"
    assert f"{SourceType.URL}" == "url"


def test_db_check_enums_has_exactly_the_eight_checked_columns() -> None:
    assert set(DB_CHECK_ENUMS) == {
        ("wiki_pages", "category"),
        ("wiki_pages", "confidence"),
        ("wiki_pages", "verification_status"),
        ("raw_sources", "source_type"),
        ("jobs", "status"),
        ("workspace_members", "role"),
        ("prompt_templates", "target_type"),
        ("usage_events", "kind"),
    }
    assert len(DB_CHECK_ENUMS) == 8


def test_jobs_type_is_absent_from_the_check_table() -> None:
    # ⚠️ `0003:31-36`이 이 컬럼에만 CHECK를 걸지 않기로 한 유일한 예외다.
    # 표에 넣으면 대조 대상이 없어 기동 가드가 무엇과 비교할지 알 수 없다.
    assert ("jobs", "type") not in DB_CHECK_ENUMS


def test_migration_parser_actually_finds_the_checks() -> None:
    # 파서가 아무것도 못 찾으면 아래 대조 테스트가 조용히 vacuous가 된다.
    parsed = _check_enums_from_migrations()

    assert _MIGRATIONS_DIR.is_dir()
    assert parsed[("jobs", "status")] == frozenset(
        {"queued", "running", "succeeded", "failed", "dead", "canceled"}
    ), "0009의 jobs.status 확장을 읽지 못했다 — 파서가 앞 파일에서 멈췄다"
    assert parsed[("workspaces", "kind")] == frozenset({"personal", "team"}), (
        "이름이 겹치는 kind 컬럼을 테이블별로 구분하지 못했다"
    )


def test_db_check_enums_match_the_migration_check_literals() -> None:
    parsed = _check_enums_from_migrations()

    for key, enum_type in DB_CHECK_ENUMS.items():
        assert key in parsed, f"{key}의 CHECK를 마이그레이션에서 찾지 못했다"
        assert {member.value for member in enum_type} == parsed[key], (
            f"{key}의 파이썬 enum과 DB CHECK 값이 어긋났다"
        )


def test_job_type_and_embedding_scope_have_no_db_counterpart() -> None:
    # 둘 다 DB CHECK가 없다. JobType은 워커 레지스트리가, EmbeddingScope는
    # jobs_dedup_idx의 target_id 접미 규약이 소유한다.
    assert {member.value for member in EmbeddingScope} == {"source", "wiki"}
    assert {"parse", "compile", "link_sync", "embed"} <= {member.value for member in JobType}
    for table_column in DB_CHECK_ENUMS:
        assert DB_CHECK_ENUMS[table_column] not in (JobType, EmbeddingScope)
