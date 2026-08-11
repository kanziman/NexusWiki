"""service key로 PostgREST에 붙는 worker 전용 DB 경로.

관련 태스크: P2-JOB-01
설계 근거: 02-CONTEXT.md > D-06, D-08
설계 근거: checklists.json > decisions.db_access, decisions.db_transport

소비자: 02-07의 큐 루프(`claim_job` → 핸들러 → `complete_job`/`fail_job`/`release_job`)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

import httpx

from nexuswiki_core.domain import VerificationStatus
from worker.settings import WorkerSettings

__all__ = [
    "QUEUE_RPC_FUNCTIONS",
    "CATALOG_RPC_FUNCTIONS",
    "CONFLICT_RPC_FUNCTIONS",
    "RPC_HELPERS",
    "SERVICE_REQUEST_TIMEOUT_SECONDS",
    "TABLE_HELPERS",
    "ServiceDb",
    "service_client",
]

SERVICE_REQUEST_TIMEOUT_SECONDS: Final[float] = 10.0

# `ServiceDb`가 직접 테이블을 읽고 쓰는 헬퍼. 전부 workspace_id를 필수로 요구한다.
TABLE_HELPERS: Final[frozenset[str]] = frozenset(
    {
        "enqueue_job",
        "get_job",
        "list_jobs",
        # -- Phase 3 도메인 테이블 (03-04) --
        "get_raw_source",
        "update_raw_source_content",
        "upsert_source_chunks",
        "list_source_chunks",
        "delete_source_chunks_from",
        "get_default_prompt_template",
        "list_wiki_slugs",
        "get_wiki_page_by_slug",
        "upsert_wiki_page",
        "list_wiki_pages_for_source",
        "insert_usage_event",
        "get_workspace_budget_cap",
        "sum_usage_events_since",
        "list_wiki_links",
        "upsert_wiki_links",
        "delete_wiki_links_not_in",
        "resolve_red_links",
        "list_source_chunks_missing_embedding",
        "update_source_chunk_embedding",
        "list_wiki_embeddings",
        "upsert_wiki_embeddings",
        "delete_wiki_embeddings_from",
        "set_wiki_page_disputed",
    }
)

# 0003이 정의한 큐 함수(0007의 release_job · complete_job_and_chain 포함)만을 호출하는 헬퍼.
QUEUE_RPC_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {
        "claim_job",
        "complete_job",
        "complete_job_and_chain",
        "fail_job",
        "release_job",
        "dead_letter_job",
        "cancel_job",
        "reap_stale_jobs",
    }
)
CATALOG_RPC_FUNCTIONS: Final[frozenset[str]] = frozenset({"enum_check_values"})
LEXICAL_RPC_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"index_source_chunk_lexical", "index_wiki_page_lexical"}
)
CONFLICT_RPC_FUNCTIONS: Final[frozenset[str]] = frozenset({"find_similar_wiki_pages"})
RPC_HELPERS: Final[frozenset[str]] = (
    QUEUE_RPC_FUNCTIONS | CATALOG_RPC_FUNCTIONS | LEXICAL_RPC_FUNCTIONS | CONFLICT_RPC_FUNCTIONS
)

# PostgREST 업서트에 필요한 Prefer 조합. `resolution=merge-duplicates`가 없으면 충돌이
# 409로 돌아오고, at-least-once 큐에서 재처리는 정상 경로이므로 그 409는 곧 잡 실패다.
_UPSERT_PREFER: Final[str] = "return=representation,resolution=merge-duplicates"


def service_client(
    settings: WorkerSettings,
    *,
    timeout_seconds: float = SERVICE_REQUEST_TIMEOUT_SECONDS,
) -> httpx.AsyncClient:
    """`WorkerSettings`를 인자로 받아야만 service key 클라이언트를 만든다.

    모듈 전역 싱글턴을 두지 않는다 — 두는 순간 import 부작용으로 키를 읽으려 시도하게
    되어 D-06의 인과("막히는 것은 import가 아니라 키다")가 흐려진다.
    근거: 02-CONTEXT.md > D-08.

    ⚠️ 아래 `TypeError`는 방어선이 아니다. 실제로 막는 것은 `ApiSettings`에 이 필드가
    없다는 사실과 Railway가 api 서비스 env에 값을 주입하지 않는다는 사실이며, 이 검사는
    그 사실이 코드에 드러나는 표면일 뿐이다. 근거: 02-CONTEXT.md > D-06.
    """
    secret_key = getattr(settings, "SUPABASE_SECRET_KEY", None)
    if not isinstance(secret_key, str) or not secret_key:
        raise TypeError(
            "service_client는 SUPABASE_SECRET_KEY를 가진 WorkerSettings를 요구한다 — "
            f"{type(settings).__name__}에는 그 필드가 없다 (02-CONTEXT.md > D-06)"
        )

    return httpx.AsyncClient(
        base_url=f"{settings.SUPABASE_URL.rstrip('/')}/rest/v1",
        headers={
            "apikey": secret_key,
            "Authorization": f"Bearer {secret_key}",
            "Accept": "application/json",
        },
        timeout=httpx.Timeout(timeout_seconds),
    )


# ⚠️ `service_role`은 BYPASSRLS다. 아래 테이블 헬퍼에서 workspace_id 조건이 빠지면
#    0004의 격리 정책 전부가 무효가 되고, 오류 없이 다른 테넌트의 행이 돌아온다.
#    그래서 workspace_id는 keyword-only이며 **기본값을 갖지 않는다** — 기본값이 있으면
#    잊고 호출해도 통과한다. 근거: checklists.json > decisions.db_access.
class ServiceDb:
    """주입된 service key 클라이언트 위에서만 동작하는 worker용 헬퍼 묶음.

    공개 헬퍼는 둘 중 하나여야 한다. 테이블 헬퍼(`TABLE_HELPERS`)는 workspace_id를 필수로
    받고, 큐 RPC 헬퍼(`RPC_HELPERS`)는 `QUEUE_RPC_FUNCTIONS`에 있는 함수만 호출한다.
    `apps/worker/tests/test_service_client.py`가 이 분류를 단언하므로, 분류를 빠져나가는
    헬퍼를 추가하면 red가 된다. Phase 2는 `jobs` 하나였고, 03-04가 파이프라인이 실제로
    읽고 쓰는 도메인 테이블 5종(`raw_sources` · `source_chunks` · `prompt_templates` ·
    `wiki_pages` · `usage_events`)을 더했다.
    """

    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    # -- 테이블 헬퍼 ---------------------------------------------------------

    async def enqueue_job(
        self,
        *,
        workspace_id: str,
        job_type: str,
        payload: dict[str, Any],
        max_attempts: int = 1,
    ) -> dict[str, Any] | None:
        """잡 한 건을 인큐한다 (0007 섹션 8이 `service_role`에 준 INSERT 권한).

        ⚠️ 여기서 만든 행은 이 클라이언트가 **지울 수 없다**. `0007` 섹션 8의
        최소권한 매트릭스는 `jobs`에 어느 롤에도 DELETE를 주지 않으며(잡 이력이
        곧 감사 기록이다), 유일한 삭제 경로는 워크스페이스 삭제의 cascade다.
        인큐한 쪽이 정리 책임을 지려면 처분 가능한 워크스페이스를 써야 한다.

        ⚠️ `payload`에 `target_id`가 없으면 `jobs_dedup_idx`가 조용히 아무 일도
        하지 않는다 — 유니크 인덱스에서 NULL은 서로 다른 값이기 때문이다. 중복
        인큐는 23505로 돌아오므로 호출부가 "이미 큐에 있음"으로 처리해야 한다.
        """
        rows = await self._insert(
            "jobs",
            row={
                "workspace_id": workspace_id,
                "type": job_type,
                "payload": payload,
                "max_attempts": max_attempts,
            },
        )
        return rows[0] if rows else None

    async def get_job(self, job_id: str, *, workspace_id: str) -> dict[str, Any] | None:
        rows = await self._select(
            "jobs",
            params={"id": f"eq.{job_id}", "workspace_id": f"eq.{workspace_id}", "limit": "1"},
        )
        return rows[0] if rows else None

    async def list_jobs(
        self,
        *,
        workspace_id: str,
        statuses: Sequence[str] | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {
            "workspace_id": f"eq.{workspace_id}",
            "order": "created_at.desc",
            "limit": str(limit),
        }
        if statuses:
            params["status"] = f"in.({','.join(statuses)})"
        return await self._select("jobs", params=params)

    # -- Phase 3 도메인 테이블 헬퍼 (03-04) ------------------------------------
    #
    # ⚠️ 아래 전부가 쿼리 파라미터에 `workspace_id=eq.<값>`을 **명시적으로** 싣는다.
    #    복합 FK(`(id, workspace_id)`, `0002_search_schema.sql:45-49`)가 잡아 주는 것은
    #    삽입이지 조회가 아니다. `service_role`은 BYPASSRLS라 조회에서 workspace_id를
    #    빠뜨리면 오류 없이 다른 테넌트의 행이 돌아온다.

    async def get_raw_source(
        self, raw_source_id: str, *, workspace_id: str
    ) -> dict[str, Any] | None:
        rows = await self._select(
            "raw_sources",
            params={
                "id": f"eq.{raw_source_id}",
                "workspace_id": f"eq.{workspace_id}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    async def update_raw_source_content(
        self,
        raw_source_id: str,
        *,
        workspace_id: str,
        content: str,
        mime_type: str | None = None,
        byte_size: int | None = None,
    ) -> dict[str, Any] | None:
        """추출된 평문을 기록한다 (파일·URL 수집 경로 — 03-06이 소비한다).

        ⚠️ `raw_sources`에는 **UPDATE 정책이 없다**(`0004`). 즉 이 경로는 오직
        `service_role`만 지날 수 있으며, 사용자가 원문을 고칠 수 없다는 ING의 불변성이
        정책 부재로 강제된다. `0007` 섹션 8이 service_role에만 UPDATE를 준 이유다.
        """
        values: dict[str, Any] = {"content": content}
        if mime_type is not None:
            values["mime_type"] = mime_type
        if byte_size is not None:
            values["byte_size"] = byte_size
        rows = await self._update(
            "raw_sources",
            params={"id": f"eq.{raw_source_id}", "workspace_id": f"eq.{workspace_id}"},
            values=values,
        )
        return rows[0] if rows else None

    async def upsert_source_chunks(
        self, *, workspace_id: str, raw_source_id: str, rows: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """청크를 `(raw_source_id, chunk_index)`로 업서트한다.

        그 유니크 키(`source_chunks_source_index_key`)가 존재하는 이유가 정확히
        at-least-once다 — 같은 잡이 두 번 돌아도 행 수가 늘지 않는다.
        """
        if not rows:
            return []
        scope = {"workspace_id": workspace_id, "raw_source_id": raw_source_id}
        payload = [{**row, **scope} for row in rows]
        return await self._insert_many(
            "source_chunks",
            rows=payload,
            params={"on_conflict": "raw_source_id,chunk_index"},
            prefer=_UPSERT_PREFER,
        )

    async def index_source_chunk_lexical(
        self,
        *,
        workspace_id: str,
        source_chunk_id: str,
        bigrams: str,
        tokenizer_version: str,
    ) -> None:
        """서비스 역할만 호출 가능한 원문 청크 lexical writer RPC."""
        await self._rpc(
            "index_source_chunk_lexical",
            {
                "p_workspace_id": workspace_id,
                "p_source_chunk_id": source_chunk_id,
                "p_bigrams": bigrams,
                "p_tokenizer_version": tokenizer_version,
            },
        )

    async def index_wiki_page_lexical(
        self,
        *,
        workspace_id: str,
        wiki_id: str,
        bigrams: str,
        tokenizer_version: str,
    ) -> None:
        """서비스 역할만 호출 가능한 위키 페이지 lexical writer RPC."""
        await self._rpc(
            "index_wiki_page_lexical",
            {
                "p_workspace_id": workspace_id,
                "p_wiki_id": wiki_id,
                "p_bigrams": bigrams,
                "p_tokenizer_version": tokenizer_version,
            },
        )

    async def list_source_chunks(
        self, *, workspace_id: str, raw_source_id: str, limit: int = 1000
    ) -> list[dict[str, Any]]:
        return await self._select(
            "source_chunks",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "raw_source_id": f"eq.{raw_source_id}",
                "order": "chunk_index.asc",
                "limit": str(limit),
            },
        )

    async def delete_source_chunks_from(
        self, *, workspace_id: str, raw_source_id: str, from_index: int
    ) -> list[dict[str, Any]]:
        """`chunk_index >= from_index`인 잔여 행을 지운다 (COMP-07 축소 재처리).

        ⚠️ 이것이 없으면 원문이 짧아진 재처리 뒤에 **옛 청크가 그대로 남아** 검색에
        잡힌다. 업서트는 있는 행을 덮을 뿐 없어진 행을 지우지 않기 때문이며, 그 잔여
        행은 오류 없이 원문에 없는 내용을 인용 근거로 내놓는다.
        """
        return await self._delete(
            "source_chunks",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "raw_source_id": f"eq.{raw_source_id}",
                "chunk_index": f"gte.{from_index}",
            },
        )

    async def get_default_prompt_template(
        self, *, workspace_id: str, target_type: str
    ) -> dict[str, Any] | None:
        """워크스페이스 기본 템플릿을 먼저 보고 없으면 전역(`workspace_id is null`)으로 내려간다.

        `0001`의 부분 유니크 인덱스가 `target_type`당 기본을 하나로 강제하므로 두 조회
        모두 최대 1행이다.
        """
        rows = await self._select(
            "prompt_templates",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "target_type": f"eq.{target_type}",
                "is_default": "is.true",
                "limit": "1",
            },
        )
        if rows:
            return rows[0]
        rows = await self._select(
            "prompt_templates",
            params={
                "workspace_id": "is.null",
                "target_type": f"eq.{target_type}",
                "is_default": "is.true",
                "limit": "1",
            },
        )
        return rows[0] if rows else None

    async def list_wiki_slugs(self, *, workspace_id: str, limit: int = 1000) -> list[str]:
        rows = await self._select(
            "wiki_pages",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "select": "slug",
                "order": "slug.asc",
                "limit": str(limit),
            },
        )
        return [str(row["slug"]) for row in rows if row.get("slug")]

    async def get_wiki_page_by_slug(self, *, workspace_id: str, slug: str) -> dict[str, Any] | None:
        rows = await self._select(
            "wiki_pages",
            params={"workspace_id": f"eq.{workspace_id}", "slug": f"eq.{slug}", "limit": "1"},
        )
        return rows[0] if rows else None

    async def upsert_wiki_page(
        self, *, workspace_id: str, row: dict[str, Any]
    ) -> dict[str, Any] | None:
        """`(workspace_id, slug)`로 페이지를 업서트한다.

        ⚠️ 호출부는 `verification_status` · `explored` · `verified_by`를 **넣지 않는다**
        (T-03-28). 사람이 세운 검증 배지를 재컴파일이 지우면, 검증이라는 행위가 소스가
        갱신될 때마다 무효가 되어 제품이 약속한 "검증 가능한 지식 베이스"가 무너진다.
        """
        rows = await self._insert_many(
            "wiki_pages",
            rows=[{**row, "workspace_id": workspace_id}],
            params={"on_conflict": "workspace_id,slug"},
            prefer=_UPSERT_PREFER,
        )
        return rows[0] if rows else None

    async def list_wiki_pages_for_source(
        self, *, workspace_id: str, raw_source_id: str, limit: int = 1000
    ) -> list[dict[str, Any]]:
        """이 원문을 역참조로 담고 있는 페이지들 (`sources` jsonb 배열 포함 조회)."""
        return await self._select(
            "wiki_pages",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "sources": f'cs.["{raw_source_id}"]',
                "order": "slug.asc",
                "limit": str(limit),
            },
        )

    async def set_wiki_page_disputed(
        self, wiki_id: str, *, workspace_id: str
    ) -> dict[str, Any] | None:
        """Mark a page disputed after worker-owned contradiction detection.

        This service-role write intentionally does not set ``verified_by`` or
        ``verified_at``: it records an automated conflict judgement, not a
        human verification transition handled by QC-02's user endpoint.
        """
        rows = await self._update(
            "wiki_pages",
            params={"id": f"eq.{wiki_id}", "workspace_id": f"eq.{workspace_id}"},
            values={
                "disputed": True,
                "verification_status": VerificationStatus.DISPUTED.value,
            },
        )
        return rows[0] if rows else None

    async def insert_usage_event(
        self, *, workspace_id: str, row: dict[str, Any]
    ) -> dict[str, Any] | None:
        """LLM·임베딩 호출 한 건의 사용량을 남긴다 — 인큐 시점 상한(OPS-01)의 유일한 데이터원.

        ⚠️ `metadata`에 프롬프트나 응답 본문을 싣지 않는다. 이 테이블은 워크스페이스
        멤버가 SELECT할 수 있어(`usage_events_select_member`) 사용량 화면이 그대로 원문
        유출 경로가 된다. 근거: `0009_pipeline_ops.sql:137-138`.
        """
        rows = await self._insert_many("usage_events", rows=[{**row, "workspace_id": workspace_id}])
        return rows[0] if rows else None

    async def get_workspace_budget_cap(self, *, workspace_id: str) -> int | None:
        """Return the workspace's monthly cap, or ``None`` when it has no row."""
        rows = await self._select(
            "workspaces",
            params={
                "id": f"eq.{workspace_id}",
                "select": "monthly_budget_micros",
                "limit": "1",
            },
        )
        return int(rows[0]["monthly_budget_micros"]) if rows else None

    async def sum_usage_events_since(self, *, workspace_id: str, since: str) -> int:
        """Sum usage in a caller-defined UTC window, preserving SQL's ``coalesce(..., 0)``."""
        rows = await self._select(
            "usage_events",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "occurred_at": f"gte.{since}",
                "select": "cost_micros",
                "limit": "1000",
            },
        )
        return sum(int(row["cost_micros"]) for row in rows)

    async def list_source_chunks_missing_embedding(
        self, *, workspace_id: str, raw_source_id: str, embedding_version: str
    ) -> list[dict[str, Any]]:
        return await self._select(
            "source_chunks",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "raw_source_id": f"eq.{raw_source_id}",
                "or": f"(embedding.is.null,embedding_version.neq.{embedding_version})",
                "order": "chunk_index.asc",
            },
        )

    async def update_source_chunk_embedding(
        self, chunk_id: str, *, workspace_id: str, embedding: str, embedding_version: str
    ) -> dict[str, Any] | None:
        rows = await self._update(
            "source_chunks",
            params={"id": f"eq.{chunk_id}", "workspace_id": f"eq.{workspace_id}"},
            values={"embedding": embedding, "embedding_version": embedding_version},
        )
        return rows[0] if rows else None

    async def upsert_wiki_embeddings(
        self, *, workspace_id: str, rows: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        return await self._insert_many(
            "wiki_embeddings",
            rows=[{**r, "workspace_id": workspace_id} for r in rows],
            params={"on_conflict": "wiki_id,chunk_index"},
            prefer=_UPSERT_PREFER,
        )

    async def list_wiki_embeddings(
        self, *, workspace_id: str, wiki_id: str, embedding_version: str
    ) -> list[dict[str, Any]]:
        """현재 버전의 행만 읽어 재처리 OpenRouter 호출을 막는다."""
        return await self._select(
            "wiki_embeddings",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "wiki_id": f"eq.{wiki_id}",
                "embedding_version": f"eq.{embedding_version}",
                "select": "chunk_index,embedding_version",
            },
        )

    async def delete_wiki_embeddings_from(
        self, *, workspace_id: str, wiki_id: str, from_index: int
    ) -> list[dict[str, Any]]:
        return await self._delete(
            "wiki_embeddings",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "wiki_id": f"eq.{wiki_id}",
                "chunk_index": f"gte.{from_index}",
            },
        )

    async def list_wiki_links(
        self, *, workspace_id: str, from_wiki_id: str
    ) -> list[dict[str, Any]]:
        return await self._select(
            "wiki_links",
            params={"workspace_id": f"eq.{workspace_id}", "from_wiki_id": f"eq.{from_wiki_id}"},
        )

    async def upsert_wiki_links(
        self, *, workspace_id: str, rows: Sequence[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        if not rows:
            return []
        return await self._insert_many(
            "wiki_links",
            rows=[{**row, "workspace_id": workspace_id} for row in rows],
            params={"on_conflict": "from_wiki_id,target_slug"},
            prefer=_UPSERT_PREFER,
        )

    async def delete_wiki_links_not_in(
        self, *, workspace_id: str, from_wiki_id: str, target_slugs: Sequence[str]
    ) -> list[dict[str, Any]]:
        params = {"workspace_id": f"eq.{workspace_id}", "from_wiki_id": f"eq.{from_wiki_id}"}
        if target_slugs:
            params["target_slug"] = f"not.in.({','.join(target_slugs)})"
        return await self._delete("wiki_links", params=params)

    async def resolve_red_links(
        self, *, workspace_id: str, target_slug: str, to_wiki_id: str
    ) -> list[dict[str, Any]]:
        return await self._update(
            "wiki_links",
            params={
                "workspace_id": f"eq.{workspace_id}",
                "target_slug": f"eq.{target_slug}",
                "to_wiki_id": "is.null",
            },
            values={"to_wiki_id": to_wiki_id},
        )

    # -- 큐 RPC 헬퍼 ---------------------------------------------------------
    #
    # 큐 함수는 테이블이 아니라 0003이 정의한 계약을 호출한다. claim은 설계상 전역
    # 폴링이고(어느 워크스페이스의 잡이든 집어간다), 나머지 셋은 이미 점유한 잡의
    # id로만 동작한다. 그래서 여기에 workspace_id를 요구하면 쓰이지 않는 인자가 되어
    # 격리를 강제하는 척만 하게 된다. 이 셋이 도메인 행을 읽는 통로가 아니라는 사실이
    # 분류를 정당화하며, 그 사실은 `QUEUE_RPC_FUNCTIONS` 허용 목록이 고정한다.

    async def claim_job(
        self,
        *,
        worker_id: str,
        types: Sequence[str] | None = None,
    ) -> dict[str, Any] | None:
        return await self._rpc(
            "claim_job",
            {"p_worker_id": worker_id, "p_types": list(types) if types is not None else None},
        )

    async def complete_job(self, job_id: str) -> dict[str, Any] | None:
        return await self._rpc("complete_job", {"p_job_id": job_id})

    async def fail_job(
        self,
        job_id: str,
        *,
        error: str,
        backoff: str | None = None,
        max_backoff: str | None = None,
    ) -> dict[str, Any] | None:
        payload: dict[str, Any] = {"p_job_id": job_id, "p_error": error}
        if backoff is not None:
            payload["p_backoff"] = backoff
        if max_backoff is not None:
            payload["p_max_backoff"] = max_backoff
        return await self._rpc("fail_job", payload)

    async def release_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        """SIGTERM 시 잡을 큐로 반납한다 (attempts를 되돌린다).

        ⚠️ `worker_id`는 선택 인자가 아니다. `public.release_job`은
        `locked_by = p_worker_id` 술어로 락 소유자를 검사하며, 그 술어가 종료 중인
        워커가 살아 있는 다른 워커의 잡을 큐로 되돌리는 것을 막는 유일한 장치다.
        기본값을 주면 그 검사를 우회할 길이 생긴다.
        근거: 02-CONTEXT.md > D-18, `supabase/migrations/0007_*.sql` 섹션 4.
        """
        return await self._rpc("release_job", {"p_job_id": job_id, "p_worker_id": worker_id})

    async def dead_letter_job(
        self, job_id: str, *, worker_id: str, error: str
    ) -> dict[str, Any] | None:
        """락 소유자만 즉시 dead로 보낸다; worker_id는 우회할 수 없는 계약이다."""
        return await self._rpc(
            "dead_letter_job", {"p_job_id": job_id, "p_worker_id": worker_id, "p_error": error}
        )

    async def cancel_job(self, job_id: str, *, worker_id: str) -> dict[str, Any] | None:
        return await self._rpc("cancel_job", {"p_job_id": job_id, "p_worker_id": worker_id})

    async def reap_stale_jobs(self, *, timeout: str) -> list[dict[str, Any]]:  # noqa: ASYNC109
        return await self._rpc_rows("reap_stale_jobs", {"p_timeout": timeout})

    async def enum_check_values(self, table: str, column: str) -> list[str]:
        # text[] is a JSON array, not a jobs record; do not use _rpc normalization.
        response = await self._client.post(
            "/rpc/enum_check_values", json={"p_table": table, "p_column": column}
        )
        response.raise_for_status()
        result = response.json()
        return [str(value) for value in result] if isinstance(result, list) else []

    async def find_similar_wiki_pages(
        self,
        workspace_id: str,
        wiki_id: str,
        *,
        similarity_threshold: float = 0.88,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        return await self._rpc_rows(
            "find_similar_wiki_pages",
            {
                "p_workspace_id": workspace_id,
                "p_wiki_id": wiki_id,
                "p_similarity_threshold": similarity_threshold,
                "p_limit": limit,
            },
        )

    async def complete_job_and_chain(
        self,
        job_id: str,
        *,
        next_type: str | None = None,
        next_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """완료와 다음 잡 인큐를 **한 트랜잭션에** 넣는다 (`0007` 섹션 3).

        ⚠️ `complete_job()` 다음에 따로 인큐하면 그 틈에서 워커가 죽었을 때 앞 단계는
        succeeded인데 다음 단계가 없는 상태로 파이프라인이 **조용히** 멈춘다. 그 침묵이
        이 함수가 존재하는 유일한 이유이며, 체인 전이를 애플리케이션에서 두 번 왕복하는
        형태로 되돌리지 말 것.

        재호출은 `status = 'running'` 술어 덕분에 0행 no-op이고 다음 잡도 생기지 않는다 —
        at-least-once 큐에서 재호출은 정상 경로다.
        """
        params: dict[str, Any] = {"p_job_id": job_id}
        if next_type is not None:
            params["p_next_type"] = next_type
            params["p_next_payload"] = next_payload or {}
        return await self._rpc("complete_job_and_chain", params)

    # -- 내부 ----------------------------------------------------------------

    async def _insert(self, table: str, *, row: dict[str, Any]) -> list[dict[str, Any]]:
        # `Prefer: return=representation`이 없으면 PostgREST가 201 + 빈 본문을 주어
        # 방금 만든 행의 id를 알 수 없다. 인큐한 잡을 추적하려면 필수다.
        return await self._insert_many(table, rows=[row])

    async def _insert_many(
        self,
        table: str,
        *,
        rows: Sequence[dict[str, Any]],
        params: dict[str, str] | None = None,
        prefer: str = "return=representation",
    ) -> list[dict[str, Any]]:
        response = await self._client.post(
            f"/{table}",
            json=list(rows),
            params=params or {},
            headers={"Prefer": prefer},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    async def _update(
        self, table: str, *, params: dict[str, str], values: dict[str, Any]
    ) -> list[dict[str, Any]]:
        response = await self._client.patch(
            f"/{table}",
            json=values,
            params=params,
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    async def _delete(self, table: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._client.request(
            "DELETE",
            f"/{table}",
            params=params,
            headers={"Prefer": "return=representation"},
        )
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    async def _select(self, table: str, *, params: dict[str, str]) -> list[dict[str, Any]]:
        response = await self._client.get(f"/{table}", params=params)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, list) else [payload]

    async def _rpc(self, function: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        response = await self._client.post(f"/rpc/{function}", json=payload)
        response.raise_for_status()
        result = response.json()
        if isinstance(result, list):
            result = result[0] if result else None
        if not isinstance(result, dict):
            return None
        # ⚠️ `returns public.jobs` 함수(complete_job · fail_job)가 0행을 돌려주면
        #    PostgREST는 null이 아니라 **모든 필드가 null인 레코드**를 만들어 준다.
        #    0003의 큐 함수들은 `where ... and status = 'running'` 절 덕분에 재호출이
        #    정상적으로 0행이고(at-least-once라 재호출이 정상 경로다), 그것을 그대로
        #    돌려주면 호출부의 `if row:` 가 no-op을 성공으로 읽는다. 그 오독은 오류 없이
        #    "두 번 처리해서 두 번 다 성공했다"는 기록을 남긴다.
        #    `setof` 함수(claim_job · release_job)는 빈 배열로 오므로 위에서 이미 걸러진다.
        if all(value is None for value in result.values()):
            return None
        return result

    async def _rpc_rows(self, function: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
        response = await self._client.post(f"/rpc/{function}", json=payload)
        response.raise_for_status()
        result = response.json()
        return result if isinstance(result, list) else []
