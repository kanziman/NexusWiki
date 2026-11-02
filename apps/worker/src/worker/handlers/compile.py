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

import hashlib
import re
from typing import Any, Final

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator

from nexuswiki_core.chunking import count_tokens
from nexuswiki_core.citations import strip_forged_anchors
from nexuswiki_core.domain import WikiCategory, WikiConfidence
from nexuswiki_core.logging import get_logger
from nexuswiki_core.router import (
    CompileRoute,
    RouteDecision,
    compile_fingerprint,
    decide_compile_route,
)
from nexuswiki_core.slug import slugify
from nexuswiki_core.tokenizer import TSV_TOKENIZER_VERSION, bigram, normalize
from nexuswiki_core.wiki_write_policy import WikiWriteRisk, classify_wiki_write
from worker.db.service import ServiceDb, service_client
from worker.llm import LlmResult, openrouter_client, render_template
from worker.llm_gateway import LlmCallContext, LlmGateway
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

# ⚠️ **전체 일치로만** 판정한다. 부분 일치는 템플릿 문법을 설명하는 정상 문서를 거부해
#    유료 재시도와 문서 유실을 낳는다 (ai-control-output-contract D3).
_PLACEHOLDER_ONLY = re.compile(
    r"(?:todo|tbd|tba|fixme|placeholder|n/?a|none|null|미정|내용\s*없음|\.{3,}|…+|\{\{\s*\w+\s*\}\})",
    re.IGNORECASE,
)


def _clean_text(value: str) -> str:
    """앵커를 지운 값을 돌려주고 빈 값과 placeholder를 거부한다.

    ⚠️ 입력에 앵커가 있으므로 모델이 제목과 본문에 베껴 쓸 수 있다. 제목에 남으면 슬러그가
    오염되고, 남은 앵커는 이후 Ask 컨텍스트에서 그 요청의 별칭으로 해소된다.
    오류 메시지에 값을 싣지 않는다. 요약이 `jobs.last_error`로 흐른다.
    """
    cleaned = strip_forged_anchors(value).strip()
    if not cleaned or _PLACEHOLDER_ONLY.fullmatch(cleaned):
        raise ValueError("blank_or_placeholder")
    return cleaned


def _clean_aliases(values: list[str]) -> list[str]:
    cleaned = (strip_forged_anchors(value).strip() for value in values)
    return [value for value in cleaned if value]


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
    # 서버가 발급한 청크 별칭. 기존 워크스페이스 템플릿은 이 필드를 내지 않으므로 기본값이 있다.
    evidence: list[str] = Field(default_factory=list)

    _validate_text = field_validator("title", "content")(_clean_text)
    _validate_aliases = field_validator("aliases")(_clean_aliases)


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

    max_existing_slugs = int(getattr(settings, "COMPILE_MAX_EXISTING_SLUGS", 200))
    existing_slugs = (await db.list_wiki_slugs(workspace_id=workspace_id))[:max_existing_slugs]
    chunks = await db.list_source_chunks(workspace_id=workspace_id, raw_source_id=raw_source_id)
    # 지문은 앵커가 붙기 전의 본문으로 계산한다. 앵커 표기를 바꿔도 재컴파일 비용이 들지 않는다.
    plain_content = "\n\n".join(str(chunk.get("content") or "") for chunk in chunks)
    # 앵커는 서버가 매기고 근거 대조의 기준이 된다. 수집 시 본문의 앵커 문법을 지웠으므로
    # 원문이 앵커를 위조할 수 없다 (parse.py).
    anchored = [
        (
            f"s{index}",
            chunk,
            # 이미 저장된 청크도 있어 여기서 다시 지운다. 위조되면 근거 대조가 깨진다.
            f"[[src:s{index}]]\n{strip_forged_anchors(str(chunk.get('content') or ''))}",
        )
        for index, chunk in enumerate(chunks, start=1)
    ]
    source_content, truncated = _join_within_budget(
        [piece for _, _, piece in anchored],
        budget_tokens=settings.COMPILE_MAX_INPUT_TOKENS,
    )
    # ⚠️ 예산에서 잘려 모델이 보지 못한 청크는 발급된 것이 아니다.
    issued_chunks = {
        alias: str(chunk["id"])
        for alias, chunk, piece in anchored
        if chunk.get("id") and piece in source_content
    }
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

    # ⚠️ `raw_sources.content_hash`가 아니라 **실제로 컴파일할 본문**의 해시를 쓴다. 그 컬럼은
    #    수집 시점의 값이고 경로마다 규칙이 달라(URL은 주소 기준) 재처리로 본문이 바뀌어도
    #    그대로다. 그 값을 쓰면 바뀐 원문을 건너뛰어 위키가 조용히 낡는다.
    fingerprint = compile_fingerprint(
        content_hash=hashlib.sha256(plain_content.encode("utf-8")).hexdigest(),
        template_id=str(template.get("id") or ""),
        model=settings.LLM_MODEL,
    )
    route = await _decide_route(
        db,
        workspace_id=workspace_id,
        raw_source_id=raw_source_id,
        fingerprint=fingerprint,
        truncated=truncated,
    )
    if route.decision == CompileRoute.SKIP_UNCHANGED:
        _logger.info(
            "worker.compile_skipped_unchanged",
            raw_source_id=raw_source_id,
            fingerprint=fingerprint,
        )
        await db.complete_job_and_chain(
            job_id,
            next_type="link_sync",
            next_payload={
                "target_id": raw_source_id,
                "raw_source_id": raw_source_id,
                "compile_route": CompileRoute.SKIP_UNCHANGED.value,
            },
        )
        return

    max_output_tokens = int(getattr(settings, "COMPILE_MAX_OUTPUT_TOKENS", 4096))
    # ⚠️ 사용량은 게이트웨이가 공급자 응답 직후 시도마다 기록한다. 그래서 검증 실패나 뒤따르는
    #    업서트 실패가 이미 지불한 비용을 지우지 못한다 (T-03-27).
    result: LlmResult = await LlmGateway(db, llm_client, settings).complete_structured(
        LlmCallContext(
            workspace_id=workspace_id,
            job_id=job_id,
            call=COMPILE_JOB_TYPE,
            # 본문은 담지 않는다 — 0009:137-138.
            metadata={
                "raw_source_id": raw_source_id,
                "truncated_input": truncated,
                "fingerprint": fingerprint,
                "route": route.decision,
                "route_reason": route.reason,
            },
        ),
        system_prompt=str(template["system_prompt"]),
        user_prompt=user_prompt,
        schema_model=CompileResult,
        max_tokens=max_output_tokens,
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

    fabricated_evidence = 0
    risk_mode = str(getattr(settings, "AI_CONTROL_RISK_MODE", "shadow"))
    for slug, page in _assign_slugs(pages):
        chunk_ids, fabricated = _resolve_evidence(page.evidence, issued_chunks)
        fabricated_evidence += fabricated
        wiki_id = await _upsert_page(
            db,
            workspace_id=workspace_id,
            raw_source_id=raw_source_id,
            slug=slug,
            page=page,
            job_id=job_id,
            risk_mode=risk_mode,
            evidence_chunk_ids=chunk_ids,
        )
        if wiki_id is None:
            # 승인 대기로 보류됐다. 근거는 제안에 실려 있고 승인 때 반영된다.
            continue
        await db.replace_wiki_page_evidence(
            workspace_id=workspace_id,
            wiki_id=wiki_id,
            raw_source_id=raw_source_id,
            chunk_ids=chunk_ids,
        )
    if fabricated_evidence:
        _logger.warning(
            "worker.compile_fabricated_evidence",
            raw_source_id=raw_source_id,
            fabricated_evidence=fabricated_evidence,
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


async def _decide_route(
    db: ServiceDb,
    *,
    workspace_id: str,
    raw_source_id: str,
    fingerprint: str,
    truncated: bool,
) -> RouteDecision:
    """Router 결정을 구한다. 지문이 같고 기존 위키 페이지가 존재할 때만 SKIP_UNCHANGED로 단락한다.

    ⚠️ 관측용 조회가 실패해도 잡을 실패시키지 않는다. 조회 실패나 기존 페이지 부재 시에는
    LLM 호출을 생략하지 않고 STANDARD/TRUNCATED로 실행한다.
    """
    previous: str | None = None
    has_existing_pages = False
    try:
        previous = await db.latest_compile_fingerprint(
            workspace_id=workspace_id, raw_source_id=raw_source_id
        )
        if previous is not None and previous == fingerprint:
            list_pages = getattr(db, "list_wiki_pages_for_source", None)
            if callable(list_pages):
                pages = await list_pages(workspace_id=workspace_id, raw_source_id=raw_source_id)
                has_existing_pages = bool(pages)
    except Exception:  # noqa: BLE001 - 관측 조회 실패는 잡의 성패와 무관하다.
        _logger.warning("worker.compile_fingerprint_unavailable", raw_source_id=raw_source_id)
        has_existing_pages = False
    return decide_compile_route(
        fingerprint=fingerprint,
        previous_fingerprint=previous,
        truncated=truncated,
        has_existing_pages=has_existing_pages,
    )


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
    job_id: str = "",
    risk_mode: str = "off",
    evidence_chunk_ids: list[str] | None = None,
) -> str | None:
    """페이지를 쓰고 id를 돌려준다. 승인 대기로 보류하면 `None`이다."""
    existing = await db.get_wiki_page_by_slug(workspace_id=workspace_id, slug=slug)
    sources = _union_sources(existing, raw_source_id)
    # ⚠️ 입력에 앵커가 생겼으므로 모델이 본문에 베껴 쓸 수 있다. 그대로 저장하면 이후 Ask
    #    컨텍스트에서 그 요청이 발급한 별칭과 혼동된다.
    content = strip_forged_anchors(page.content)

    if existing is not None and risk_mode != "off":
        decision = classify_wiki_write(
            existing,
            new_content=content,
            raw_source_id=raw_source_id,
            published=await db.is_wiki_page_published(
                workspace_id=workspace_id, wiki_id=str(existing["id"])
            ),
            metadata_changed=(
                existing.get("title") != page.title
                or existing.get("category") != page.category.value
                or (existing.get("aliases") or []) != page.aliases
                or existing.get("confidence") != page.confidence.value
            ),
        )
        if decision.changed:
            if decision.risk == WikiWriteRisk.HIGH and risk_mode == "enforce":
                await db.upsert_wiki_write_proposal(
                    workspace_id=workspace_id,
                    wiki_id=str(existing["id"]),
                    raw_source_id=raw_source_id,
                    risk_reason=decision.reason,
                    title=page.title,
                    category=page.category.value,
                    aliases=page.aliases,
                    confidence=page.confidence.value,
                    content=content,
                    evidence_chunk_ids=evidence_chunk_ids or [],
                )
                _logger.info(
                    "worker.compile_write_held",
                    raw_source_id=raw_source_id,
                    risk_reason=decision.reason,
                )
                return None
            # ⚠️ 덮어쓰기 전에 남긴다. 순서를 바꾸면 실패 시 이전 본문이 사라진다.
            await db.insert_wiki_page_revision(
                workspace_id=workspace_id,
                row={
                    "wiki_id": str(existing["id"]),
                    "raw_source_id": raw_source_id,
                    "job_id": job_id,
                    "risk_level": decision.risk.value,
                    "reason": decision.reason,
                    "previous_title": str(existing.get("title") or ""),
                    "previous_content": str(existing.get("content") or ""),
                },
            )

    # ⚠️ `verification_status` · `explored` · `verified_by` · `disputed`를 **넣지 않는다**
    #    (T-03-28). 사람이 세운 검증 배지를 재컴파일이 지우면 검증이라는 행위가 소스가
    #    갱신될 때마다 무효가 되고, 제품이 약속한 "검증 가능한 지식 베이스"가 무너진다.
    #    새 페이지에는 DB 기본값(`unverified` / `false`)이 붙는다.
    stored = await db.upsert_wiki_page(
        workspace_id=workspace_id,
        row={
            "slug": slug,
            "title": page.title,
            "category": page.category.value,
            "content": content,
            "aliases": page.aliases,
            "confidence": page.confidence.value,
            "sources": sources,
        },
    )
    wiki_id = (stored or {}).get("id")
    if not isinstance(wiki_id, str):
        raise RuntimeError("wiki_pages 업서트가 lexical 색인에 필요한 id를 돌려주지 않았다")
    await db.index_wiki_page_lexical(
        workspace_id=workspace_id,
        wiki_id=wiki_id,
        bigrams=bigram(normalize(content)),
        tokenizer_version=TSV_TOKENIZER_VERSION,
    )
    return wiki_id


def _resolve_evidence(evidence: list[str], issued: dict[str, str]) -> tuple[list[str], int]:
    """발급된 별칭만 청크 id로 바꾸고 지어낸 수를 센다. 모델이 앵커 표기로 내도 받아 준다."""
    chunk_ids: list[str] = []
    fabricated = 0
    for raw in evidence:
        alias = raw.strip().removeprefix("[[").removesuffix("]]").removeprefix("src:")
        chunk_id = issued.get(alias)
        if chunk_id is None:
            fabricated += 1
        elif chunk_id not in chunk_ids:
            chunk_ids.append(chunk_id)
    return chunk_ids, fabricated


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
