"""DB CHECK 제약과 짝을 이루는 도메인 열거값과 그 대조표.

관련 태스크: P2-JOB-01, P3-COMP-01
설계 근거: 03-CONTEXT.md > D-01
설계 근거: supabase/migrations/0001_core_schema.sql · 0009_pipeline_ops.sql

이 파일의 값은 애플리케이션이 정하는 것이 아니라 **DB가 이미 정해 둔 것을 옮긴 것**이다.
어긋나면 워커가 만든 행이 삽입 시점에 23514로 거부되는데, 그 실패는 잡 재시도가 전부
소진된 뒤 `dead`로만 드러나 원인을 되짚기 어렵다. 그래서 `DB_CHECK_ENUMS`가 존재한다 —
COMP-02의 기동 가드가 `public.enum_check_values(table, column)`(`0009` §7)이 돌려주는
집합과 이 표를 대조해 **기동 시점에** 끊는다.

모든 열거를 `enum.StrEnum`으로 둔다. `str`의 하위 타입이라 Pydantic이 직렬화한 값이
변환 없이 그대로 DB 값이 된다.

소비자: `worker.handlers.compile` · `worker.startup` (COMP-02) · `api.routers.sources`
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final

__all__ = [
    "DB_CHECK_ENUMS",
    "EmbeddingScope",
    "JobStatus",
    "JobType",
    "MemberRole",
    "PromptTargetType",
    "SourceType",
    "UsageKind",
    "VerificationStatus",
    "WikiCategory",
    "WikiConfidence",
]


class WikiCategory(StrEnum):
    """`wiki_pages.category` — `0001_core_schema.sql:138`."""

    CONCEPTS = "concepts"
    ENTITIES = "entities"
    GUIDES = "guides"
    MAPS = "maps"


class WikiConfidence(StrEnum):
    """`wiki_pages.confidence` — `0001_core_schema.sql:145-146`."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class VerificationStatus(StrEnum):
    """`wiki_pages.verification_status` — `0001_core_schema.sql:147-148`."""

    VERIFIED = "verified"
    PARTIAL = "partial"
    UNVERIFIED = "unverified"
    DISPUTED = "disputed"


class SourceType(StrEnum):
    """`raw_sources.source_type` — `0001_core_schema.sql:96-98`."""

    ARTICLE = "article"
    PAPER = "paper"
    BOOK = "book"
    TRANSCRIPT = "transcript"
    CLIPPING = "clipping"
    FILE = "file"
    TEXT = "text"
    URL = "url"


class JobStatus(StrEnum):
    """`jobs.status` — `0003_jobs.sql:40`에서 5값, `0009_pipeline_ops.sql:71`이 6값으로 확장.

    ⚠️ `canceled`는 `0009`가 더한 값이다. 5값만 아는 코드는 취소된 잡을 미지의 상태로
    만나며, 그 분기가 없으면 워커 루프가 취소를 실패로 오인해 재시도한다.
    """

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DEAD = "dead"
    CANCELED = "canceled"


class MemberRole(StrEnum):
    """`workspace_members.role` — `0001_core_schema.sql:56`.

    값의 순서가 곧 권한의 서열이며 `public.has_workspace_role(uuid, text)`
    (`0004_rls_policies.sql`)가 같은 서열을 SQL에서 판정한다.
    """

    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


class PromptTargetType(StrEnum):
    """`prompt_templates.target_type` — `0001_core_schema.sql:185`."""

    COMPILE = "compile"
    ASK = "ask"


class UsageKind(StrEnum):
    """`usage_events.kind` — `0009_pipeline_ops.sql:117`."""

    LLM = "llm"
    EMBEDDING = "embedding"


class JobType(StrEnum):
    """`jobs.type` — ⚠️ **DB에 CHECK가 없는 유일한 열거다.**

    `0003_jobs.sql:31-36`이 의도적으로 CHECK를 걸지 않았다. 잡 종류의 실물 열거는
    DB가 아니라 워커 레지스트리(`worker.handlers.HANDLERS`)가 소유하며, 미등록 type은
    그 레지스트리가 즉시 dead-letter로 보낸다. 그래서 이 열거는 `DB_CHECK_ENUMS`에
    **넣지 않는다** — 넣으면 대조할 상대가 없어 기동 가드가 무엇과 비교할지 알 수 없고,
    DB 쪽에 CHECK를 만들어 맞추려는 순간 잡 종류 하나를 더할 때마다 마이그레이션이 필요해진다.

    이 클래스는 오타 방지용 상수 모음이지 DB 계약이 아니다.
    """

    PARSE = "parse"
    COMPILE = "compile"
    LINK_SYNC = "link_sync"
    EMBED = "embed"
    NOOP = "noop"


class EmbeddingScope(StrEnum):
    """임베딩 대상이 원문 청크인지 위키 페이지인지 — DB CHECK가 없다.

    `jobs_dedup_idx`(`0007` §2)가 `payload ->> 'target_id'`로 중복 인큐를 막으므로,
    같은 UUID에 대한 원문 임베딩과 위키 임베딩이 서로를 중복으로 오인하지 않도록
    이 값을 `target_id` 접미로 붙인다 (`{uuid}:source` / `{uuid}:wiki`).
    """

    SOURCE = "source"
    WIKI = "wiki"


DB_CHECK_ENUMS: Final[dict[tuple[str, str], type[StrEnum]]] = {
    ("wiki_pages", "category"): WikiCategory,
    ("wiki_pages", "confidence"): WikiConfidence,
    ("wiki_pages", "verification_status"): VerificationStatus,
    ("raw_sources", "source_type"): SourceType,
    ("jobs", "status"): JobStatus,
    ("workspace_members", "role"): MemberRole,
    ("prompt_templates", "target_type"): PromptTargetType,
    ("usage_events", "kind"): UsageKind,
}
"""`(table, column)` → 그 컬럼의 CHECK 열거와 같아야 하는 StrEnum.

⚠️ `("jobs", "type")`은 여기 **없다** — 이유는 `JobType` docstring에 있다.
⚠️ `("workspaces", "kind")`도 없다. CHECK는 있지만(`0001:35`) 워크스페이스 종류를
   읽거나 쓰는 애플리케이션 경로가 아직 없어, 소비자 없는 대조 항목을 만들지 않는다.
   그 경로가 생기면 여기 한 줄을 더하고 `WorkspaceKind`를 정의한다.
"""
