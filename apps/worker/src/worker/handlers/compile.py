"""compile 잡 — 원문 청크를 LLM으로 위키 페이지로 컴파일해 업서트한다.

관련 태스크: P2-LLM-01 (COMP-01, COMP-03, COMP-04)
설계 근거: 03-04-PLAN.md > D-P7 (산출 단위와 상한), D-P8 (합집합 업서트), D-P9 (슬러그 소유권)
설계 근거: 02-CONTEXT.md > D-20 (LLM은 title만 내고 슬러그를 소유하지 않는다)
설계 근거: checklists.json > decisions.llm, decisions.structured_output

  parse ──> compile ──complete_job_and_chain()──> (끝)

⚠️ 멱등성: 페이지는 `(workspace_id, slug)` 업서트다. 같은 잡이 두 번 돌아도 행 수가
늘지 않으며, 슬러그를 **앱이** 소유하기 때문에 두 번째 실행이 `-2` 접미를 붙여 문서를
증식시키지 않는다 (D-P9).

소비자: `worker.handlers.HANDLERS`
"""

from __future__ import annotations

from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, Field

from nexuswiki_core.chunking import count_tokens
from nexuswiki_core.domain import UsageKind, WikiCategory, WikiConfidence
from nexuswiki_core.logging import get_logger
from nexuswiki_core.slug import slugify
from worker.db.service import ServiceDb, service_client
from worker.llm import LlmResult, complete_structured, openrouter_client, render_template
from worker.settings import WorkerSettings

__all__ = [
    "COMPILE_JOB_TYPE",
    "COMPILE_TARGET_TYPE",
    "CompileResult",
    "CompiledPage",
    "handle_compile",
    "run_compile",
]

COMPILE_JOB_TYPE: Final[str] = "compile"
COMPILE_TARGET_TYPE: Final[str] = "compile"

_logger = get_logger(__name__)


class CompiledPage(BaseModel):
    """LLM이 낸 페이지 하나.

    ⚠️ `slug` 필드를 **받되 쓰지 않는다.** `0006_seed_prompts.sql:72-78`의 프롬프트가
    모델에게 slug를 요구하지만 02-CONTEXT.md > D-20과 DOM-07은 LLM이 슬러그를 소유하지
    않는다고 못 박았다. `0006`은 이미 클라우드에 적용되어 수정할 수 없으므로 앞으로
    나아가는 방식으로 정정한다 — 필드는 받아 검증을 통과시키고, 권위 있는 슬러그는
    `slugify(title=...)`가 만든다 (D-P9). 필드를 지우면 모델 출력이 스키마를 어겨
    재시도가 3회 소진된다.
    """

    model_config = ConfigDict(extra="ignore")

    slug: str = ""
    title: str = Field(min_length=1)
    category: WikiCategory
    aliases: list[str] = Field(default_factory=list)
    confidence: WikiConfidence
    content: str = Field(min_length=1)


class CompileResult(BaseModel):
    """컴파일 한 번의 산출.

    빈 `pages`는 **유효한 결과이며 실패가 아니다** — `0006_seed_prompts.sql:109`가
    "자료에서 만들 문서가 없다면 `{"pages": []}`를 반환하세요"로 이미 규정했다.
    상한(`COMPILE_MAX_PAGES`)은 런타임 설정값이라 모델이 아니라 핸들러가 자른다.
    """

    model_config = ConfigDict(extra="ignore")

    pages: list[CompiledPage] = Field(default_factory=list)


async def handle_compile(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    """`JobHandler` 계약 진입점 — 자기 수명 동안만 두 클라이언트를 연다."""
    settings = WorkerSettings()
    async with service_client(settings) as db_client, openrouter_client(settings) as llm_client:
        await run_compile(
            ServiceDb(db_client),
            llm_client,
            settings=settings,
            job_id=job_id,
            workspace_id=workspace_id,
            payload=payload,
        )


async def run_compile(
    db: ServiceDb,
    llm_client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    job_id: str,
    workspace_id: str,
    payload: dict[str, Any],
) -> None:
    raw_source_id = str(payload.get("raw_source_id") or payload.get("target_id") or "")
    if not raw_source_id:
        raise ValueError("compile 잡 payload에 raw_source_id가 없다")

    source = await db.get_raw_source(raw_source_id, workspace_id=workspace_id)
    if source is None:
        raise LookupError(f"raw_source를 찾을 수 없다: {raw_source_id}")

    template = await db.get_default_prompt_template(
        workspace_id=workspace_id, target_type=COMPILE_TARGET_TYPE
    )
    if template is None:
        raise LookupError("compile 기본 프롬프트 템플릿이 없다 — 0006 시드가 적용되지 않았다")

    existing_slugs = await db.list_wiki_slugs(workspace_id=workspace_id)
    chunks = await db.list_source_chunks(workspace_id=workspace_id, raw_source_id=raw_source_id)
    source_content, truncated = _join_within_budget(
        [str(chunk.get("content") or "") for chunk in chunks],
        budget_tokens=settings.COMPILE_MAX_INPUT_TOKENS,
    )
    if truncated:
        _logger.warning(
            "worker.compile_input_truncated",
            raw_source_id=raw_source_id,
            chunk_count=len(chunks),
            budget_tokens=settings.COMPILE_MAX_INPUT_TOKENS,
        )

    # ⚠️ 소스 본문은 **`{{source_content}}` 자리에만** 들어간다. system 프롬프트는 치환
    #    없이 그대로 쓴다 — 수집한 텍스트가 system 지시에 섞이면 소스가 곧 명령이 된다
    #    (T-03-19). `render_template`이 단일 스캔이라 본문 안의 `{{...}}`도 리터럴로 남는다.
    user_prompt = render_template(
        str(template["template"]),
        {
            "source_title": str(source.get("title") or ""),
            "source_type": str(source.get("source_type") or ""),
            "existing_slugs": "\n".join(f"- {slug}" for slug in existing_slugs) or "(없음)",
            "source_content": source_content,
        },
    )

    result: LlmResult = await complete_structured(
        llm_client,
        settings=settings,
        system_prompt=str(template["system_prompt"]),
        user_prompt=user_prompt,
        schema_model=CompileResult,
    )

    # ⚠️ 사용량은 페이지 업서트보다 **먼저** 기록한다. 업서트가 실패해 잡이 재시도되면
    #    이미 지불한 LLM 비용은 돌아오지 않으므로, 그 지출이 상한 계산에 빠지면 상한이
    #    조용히 새어 나간다 (T-03-27).
    await db.insert_usage_event(
        workspace_id=workspace_id,
        row={
            "job_id": job_id,
            "kind": UsageKind.LLM.value,
            "provider": result.provider,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "cost_micros": result.cost_micros,
            # 본문은 담지 않는다 — 0009:137-138.
            "metadata": {"raw_source_id": raw_source_id, "truncated_input": truncated},
        },
    )

    compiled = result.payload
    if not isinstance(compiled, CompileResult):  # pragma: no cover - 스키마가 이미 보장한다
        raise TypeError(f"CompileResult가 아닌 {type(compiled).__name__}가 돌아왔다")
    pages = compiled.pages[: settings.COMPILE_MAX_PAGES]
    if len(compiled.pages) > settings.COMPILE_MAX_PAGES:
        _logger.warning(
            "worker.compile_pages_truncated",
            raw_source_id=raw_source_id,
            produced=len(compiled.pages),
            kept=settings.COMPILE_MAX_PAGES,
        )

    if not pages:
        # 실패가 아니다 (0006:109). 그러나 조용히 넘어가지도 않는다 — 컴파일이 아무것도
        # 만들지 않는 상태가 반복되면 그것은 프롬프트나 추출의 문제라는 신호다.
        _logger.warning("worker.compile_produced_no_pages", raw_source_id=raw_source_id)

    for slug, page in _assign_slugs(pages):
        await _upsert_page(
            db,
            workspace_id=workspace_id,
            raw_source_id=raw_source_id,
            slug=slug,
            page=page,
        )

    _logger.info(
        "worker.compile_completed",
        raw_source_id=raw_source_id,
        page_count=len(pages),
        cost_micros=result.cost_micros,
        model=result.model,
    )

    # ⚠️ 여기서 체인이 끝난다 — tracer 범위에서 `compile`이 마지막 단계이기 때문이다.
    #    03-09(COMP-05)가 이 호출에
    #      next_type="link_sync",
    #      next_payload={"target_id": raw_source_id, "raw_source_id": raw_source_id},
    #    를 더해 체인을 잇는다. 인자 두 개를 더하는 자리이며, `complete_job_and_chain`
    #    이라는 전이 기구 자체는 `parse → compile`이 이미 실제로 증명했다.
    await db.complete_job_and_chain(
        job_id,
        next_type="link_sync",
        next_payload={"target_id": raw_source_id, "raw_source_id": raw_source_id},
    )


# -- 내부 ----------------------------------------------------------------------


def _join_within_budget(pieces: list[str], *, budget_tokens: int) -> tuple[str, bool]:
    """청크를 순서대로 이어 붙이되 토큰 예산에서 멈춘다.

    ⚠️ 잘림은 **관측되어야 한다.** 조용히 자르면 긴 소스의 뒷부분이 위키에 영원히
    반영되지 않으면서 컴파일은 성공으로 기록된다.
    """
    joined: list[str] = []
    used = 0
    for piece in pieces:
        cost = count_tokens(piece)
        if joined and used + cost > budget_tokens:
            return "\n\n".join(joined), True
        joined.append(piece)
        used += cost
    return "\n\n".join(joined), False


def _assign_slugs(pages: list[CompiledPage]) -> list[tuple[str, CompiledPage]]:
    """title에서 결정적 슬러그를 배정하고 **슬러그 기준으로 정렬**한다 (D-P9).

    ⚠️ `taken`에 워크스페이스의 **기존 슬러그를 넣지 않는다.** 기존 슬러그는 충돌
    대상이 아니라 **업서트 대상**이고, 넣으면 재컴파일마다 `-2`, `-3`이 붙어 같은 주제의
    문서가 증식한다. 넣는 것은 이번 배치에서 이미 쓴 슬러그뿐이며, 그래야 한 배치 안의
    동명 페이지 둘이 서로를 덮지 않는다.

    정렬하는 이유: 업서트 순서가 결정적이어야 같은 입력이 같은 순서의 `wiki_links`
    해소를 만든다 (03-09가 소비한다).
    """
    batch: set[str] = set()
    assigned: list[tuple[str, CompiledPage]] = []
    for page in pages:
        slug = slugify(title=page.title, taken=batch)
        batch.add(slug)
        assigned.append((slug, page))
    return sorted(assigned, key=lambda item: item[0])


async def _upsert_page(
    db: ServiceDb,
    *,
    workspace_id: str,
    raw_source_id: str,
    slug: str,
    page: CompiledPage,
) -> None:
    existing = await db.get_wiki_page_by_slug(workspace_id=workspace_id, slug=slug)
    sources = _union_sources(existing, raw_source_id)

    # ⚠️ `verification_status` · `explored` · `verified_by` · `disputed`를 **넣지 않는다**
    #    (T-03-28). 사람이 세운 검증 배지를 재컴파일이 지우면 검증이라는 행위가 소스가
    #    갱신될 때마다 무효가 되고, 제품이 약속한 "검증 가능한 지식 베이스"가 무너진다.
    #    새 페이지에는 DB 기본값(`unverified` / `false`)이 붙는다.
    await db.upsert_wiki_page(
        workspace_id=workspace_id,
        row={
            "slug": slug,
            "title": page.title,
            "category": page.category.value,
            "content": page.content,
            "aliases": page.aliases,
            "confidence": page.confidence.value,
            "sources": sources,
        },
    )


def _union_sources(existing: dict[str, Any] | None, raw_source_id: str) -> list[str]:
    """기존 역참조와 이번 소스의 합집합 (D-P8).

    ⚠️ 통째로 덮어쓰면 같은 페이지를 함께 만든 **다른 소스의 역참조**가 사라져 이중
    Citation의 위키→원문 경로가 끊긴다. 합집합만이 `sources`를 사실로 유지한다.
    순서를 고정해 같은 입력이 같은 배열을 만든다.
    """
    previous = (existing or {}).get("sources")
    values = [str(item) for item in previous] if isinstance(previous, list) else []
    if raw_source_id not in values:
        values.append(raw_source_id)
    return sorted(set(values))
