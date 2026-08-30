"""Ask 서비스 — 인용 앵커 발급/해소와 워커 스트리밍 릴레이.

관련 태스크: 05-01-PLAN.md Task 2
설계 근거: 05-CONTEXT.md > D-01, D-02, D-03, D-08

`apps.api.services.retrieval`의 DI 형태(주입된 HTTP 클라이언트, 프로즌 dataclass 결과)를
그대로 따른다. 앵커 발급 맵은 이 요청/스트림의 수명 동안만 존재하고 절대 영속화하지
않는다(D-02).

⚠️ 이 모듈은 `worker.llm.render_template()`을 재사용할 수 **없다** — api와 worker는
별도로 배포되는 프로세스이고(01-CONTEXT.md > D-01) 서로의 모듈을 import하지 않는다.
그래서 동일한 단일-스캔 치환 로직을 `_render()`로 독립 복제한다.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import AsyncIterator, Mapping
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass
from typing import Any, Final, Protocol
from uuid import UUID

import httpx

from api.db.user import UserDb
from api.errors import DatabaseError, WorkspaceForbidden
from api.services.retrieval import RetrievalService
from nexuswiki_core.citations import BROAD_ANCHOR_PATTERN, ISSUED_ANCHOR_PATTERN
from nexuswiki_core.rrf import EvidenceHit
from nexuswiki_core.sentences import split_sentences

__all__ = [
    "NO_EVIDENCE_MESSAGE",
    "AskService",
    "CitationResolution",
    "HttpLlmStreamClient",
    "LlmStreamClient",
    "build_issuance_map",
    "resolve_citations",
]

# CITE-04가 요구하는 정확한 문구.
NO_EVIDENCE_MESSAGE: Final[str] = "근거를 찾지 못했습니다."

_PROMPT_TARGET_TYPE: Final[str] = "ask"

# `worker.llm`의 `_PLACEHOLDER`와 동일 — `{{변수}}` 이중 중괄호.
_PLACEHOLDER: Final[re.Pattern[str]] = re.compile(r"\{\{([A-Za-z0-9_]+)\}\}")

# 워커 스트림의 비-2xx 상태를 SSE `citations` 이벤트의 기계 판독 토큰으로 매핑한다.
# 05-04-PLAN.md의 예산 게이트(402)가 이 매핑에 API 쪽 추가 변경 없이 얹힌다.
_ERROR_TOKENS: Final[dict[int, str]] = {
    401: "internal_unauthorized",
    402: "budget_exceeded",
    429: "rate_limited",
    502: "llm_unavailable",
    504: "llm_unavailable",
}


class UpstreamChatStream(Protocol):
    """`HttpLlmStreamClient.stream()`이 여는 컨텍스트가 넘겨주는 최소 표면."""

    status_code: int

    def aiter_lines(self) -> AsyncIterator[str]: ...


class LlmStreamClient(Protocol):
    """`RetrievalService`의 `QueryEmbeddingClient` Protocol과 같은 DI 형태."""

    def stream(
        self, *, workspace_id: str, messages: list[dict[str, str]]
    ) -> AbstractAsyncContextManager[UpstreamChatStream]: ...


class HttpLlmStreamClient:
    """The API's only LLM capability: an authenticated private worker call.

    Task 1의 `/internal/llm-chat` 계약과 정확히 일치한다: POST body
    `{"workspace_id": str, "messages": [...]}}`, 헤더 `Authorization: Bearer <token>`,
    응답 본문은 OpenRouter 원문 SSE 바이트.
    """

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        url: str | None,
        token: str | None,
        timeout_seconds: float,
    ) -> None:
        self._client, self._url, self._token, self._timeout_seconds = (
            client,
            url,
            token,
            timeout_seconds,
        )

    def stream(
        self, *, workspace_id: str, messages: list[dict[str, str]]
    ) -> AbstractAsyncContextManager[httpx.Response]:
        if not self._url or not self._token:
            raise RuntimeError("llm_stream_unavailable")
        # ⚠️ `app.state.http_client`의 전역 2.0초 타임아웃을 재사용하지 않는다
        #    (`api.main:33` — PostgREST 왕복용으로 맞춘 값이다). 호출 단위로 재정의한다.
        return self._client.stream(
            "POST",
            f"{self._url.rstrip('/')}/internal/llm-chat",
            json={"workspace_id": workspace_id, "messages": messages},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=httpx.Timeout(connect=5.0, read=self._timeout_seconds, write=5.0, pool=5.0),
        )


def build_issuance_map(evidence: list[EvidenceHit]) -> dict[str, tuple[str, str]]:
    """`RetrievalService.retrieve()`의 evidence를 반환 순서로 나열해 별칭을 매긴다(D-02).

    실제 id는 모델에게 절대 노출되지 않는다 — 별칭만 노출된다. `kind`는 wiki
    (`document_id`)와 source(`evidence_id`, 즉 chunk id)를 구분한다
    (`packages/core/src/nexuswiki_core/rrf.py`의 `EvidenceHit` 형태).
    """
    wiki_n = source_n = 0
    issuance: dict[str, tuple[str, str]] = {}
    for hit in evidence:
        if hit.kind == "wiki":
            wiki_n += 1
            issuance[f"w{wiki_n}"] = ("wiki", hit.document_id)
        else:
            source_n += 1
            issuance[f"s{source_n}"] = ("source", hit.evidence_id)
    return issuance


@dataclass(frozen=True, slots=True)
class CitationResolution:
    resolved: list[dict[str, str]]
    fabricated_anchor_count: int
    cited_anchor_count: int
    dual_citation_rate: float
    unsourced_sentence_ratio: float
    rendered_text: str


def resolve_citations(
    full_text: str, issuance: Mapping[str, tuple[str, str]]
) -> CitationResolution:
    """CITE-01/02/03의 완전한 구현. CITE-05의 두 비율 지표는 05-03-PLAN.md가 이 함수에 더한다.

    파싱된 앵커 ∩ 발급된 앵커(CITE-02) — 원문 검색 결과와 절대 교집합을 취하지 않는다.
    발급되지 않은 파싱 앵커는 조작으로 간주해 카운트하고(CITE-03) 렌더된 텍스트에서 지운다.
    """
    parsed_tokens = {m.group(1) for m in ISSUED_ANCHOR_PATTERN.finditer(full_text)}
    parsed_aliases = {token.split(":", 1)[1] for token in parsed_tokens}
    resolved_aliases = parsed_aliases & issuance.keys()
    fabricated_aliases = parsed_aliases - issuance.keys()

    def _strip_fabricated(match: re.Match[str]) -> str:
        span = match.group(0)
        issued_match = ISSUED_ANCHOR_PATTERN.fullmatch(span)
        if issued_match:
            alias = issued_match.group(1).split(":", 1)[1]
            if alias in resolved_aliases:
                return span  # 실제로 발급된 앵커 — 그대로 둔다. 조작이 아니다.
        return ""  # 조작이거나(파싱은 됐지만 미발급) 애초에 우리가 발급하지 않는 모양이다.

    rendered_text = BROAD_ANCHOR_PATTERN.sub(_strip_fabricated, full_text)
    sentences = split_sentences(full_text)
    dual_cited_count = sum(
        1
        for sentence in sentences
        if any(token.startswith("wiki:") for token in ISSUED_ANCHOR_PATTERN.findall(sentence))
        and any(token.startswith("src:") for token in ISSUED_ANCHOR_PATTERN.findall(sentence))
    )
    unsourced_count = sum(
        1 for sentence in sentences if not ISSUED_ANCHOR_PATTERN.findall(sentence)
    )
    sentence_count = len(sentences)

    return CitationResolution(
        resolved=[
            {"alias": alias, "kind": issuance[alias][0], "id": issuance[alias][1]}
            for alias in sorted(resolved_aliases)
        ],
        fabricated_anchor_count=len(fabricated_aliases),
        cited_anchor_count=len(resolved_aliases),
        dual_citation_rate=dual_cited_count / sentence_count if sentence_count else 0.0,
        unsourced_sentence_ratio=unsourced_count / sentence_count if sentence_count else 0.0,
        rendered_text=rendered_text,
    )


def _render(template: str, values: Mapping[str, str]) -> str:
    """`worker.llm.render_template()`과 동일한 단일 스캔 치환의 독립 복제.

    ⚠️ `str.format`을 쓰지 않는다 — 컨텍스트 블록에 그대로 들어오는 마크다운/코드/JSON의
    단일 중괄호가 format을 깨뜨린다. api와 worker는 별도 프로세스라 이 로직을 각자
    독립적으로 강제해야 T-03-19(프롬프트 인젝션) 완화가 두 프로세스 모두에서 성립한다.
    """
    matched = _PLACEHOLDER.findall(template)
    if template.count("{{") != len(matched):
        raise ValueError("템플릿에 형식을 벗어난 `{{`가 있다")

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            raise ValueError(f"플레이스홀더 {{{{{key}}}}}에 대응하는 값이 없다")
        return values[key]

    return _PLACEHOLDER.sub(substitute, template)


async def _fetch_evidence_content(
    user_db: UserDb, *, workspace_id: UUID, evidence: list[EvidenceHit]
) -> dict[str, str]:
    """evidence가 가리키는 실제 본문을 배치로 페치한다 (id -> content).

    ⚠️ `UserDb.select()`의 공용 필터는 eq 전용이라 다건 조회(`in.(...)`)를 표현할 수 없다.
    `jobs.py::_usage_rows_since`가 이미 세운 좁은 seam을 그대로 미러링한다 — `UserDb`에
    새 메서드를 얹지 않고 `db._client`/`_base_url`/`_headers`/`_payload`를 직접 쓴다.
    `in.(...)` 필터는 `RetrievalService.retrieve()`가 이미 돌려준(서버가 통제하는)
    `document_id`/`evidence_id` 값으로만 구성되고, 요청은 여전히 요청자 JWT +
    `workspace_id=eq.<value>`를 함께 실어 RLS가 테넌트 경계를 유지한다.
    """
    wiki_ids = sorted({hit.document_id for hit in evidence if hit.kind == "wiki"})
    source_ids = sorted({hit.evidence_id for hit in evidence if hit.kind == "source"})
    content: dict[str, str] = {}
    if wiki_ids:
        response = await user_db._client.get(  # noqa: SLF001 - 제한적 in-filter seam
            f"{user_db._base_url}/wiki_pages",
            params={
                "id": f"in.({','.join(wiki_ids)})",
                "workspace_id": f"eq.{workspace_id}",
                "select": "id,content",
            },
            headers=user_db._headers,  # noqa: SLF001
        )
        rows = user_db._payload(response)  # noqa: SLF001
        for row in rows if isinstance(rows, list) else [rows]:
            content[str(row["id"])] = str(row.get("content") or "")
    if source_ids:
        response = await user_db._client.get(  # noqa: SLF001 - 제한적 in-filter seam
            f"{user_db._base_url}/source_chunks",
            params={
                "id": f"in.({','.join(source_ids)})",
                "workspace_id": f"eq.{workspace_id}",
                "select": "id,content",
            },
            headers=user_db._headers,  # noqa: SLF001
        )
        rows = user_db._payload(response)  # noqa: SLF001
        for row in rows if isinstance(rows, list) else [rows]:
            content[str(row["id"])] = str(row.get("content") or "")
    return content


async def _select_default_ask_template(
    user_db: UserDb, *, workspace_id: UUID
) -> dict[str, Any] | None:
    """`worker.db.service.get_default_prompt_template()`의 요청자-JWT 버전.

    워크스페이스 기본을 먼저 보고 없으면 전역(`workspace_id is null`)으로 내려간다.
    `UserDb.select()`가 eq 전용이라 두 번째 조회에서 `workspace_id is.null`을 직접 표현할
    수 없다 — 대신 `workspace_id`를 필터에서 빼고, RLS가 이미 가시 범위를(전역 또는
    멤버 워크스페이스) 좁혀 둔 결과에서 `workspace_id is None`인 행만 클라이언트 쪽에서
    고른다. `0001`의 부분 유니크 인덱스가 `target_type`당 기본을 하나로 강제하므로
    이 필터링은 최대 1행만 남긴다.
    """
    rows = await user_db.select(
        "prompt_templates",
        match={
            "workspace_id": str(workspace_id),
            "target_type": _PROMPT_TARGET_TYPE,
            "is_default": "true",
        },
        limit=1,
    )
    if rows:
        return rows[0]
    rows = await user_db.select(
        "prompt_templates",
        match={"target_type": _PROMPT_TARGET_TYPE, "is_default": "true"},
    )
    for row in rows:
        if row.get("workspace_id") is None:
            return row
    return None


async def _select_ask_template(
    user_db: UserDb, *, workspace_id: UUID, template_id: str | None
) -> dict[str, Any] | None:
    """API-02: 보이는 요청 템플릿만 쓰고, 아니면 기존 기본값 체인으로 내려간다.

    RLS가 가시성 밖 행을 빈 목록으로 돌리므로 id가 없거나 다른 워크스페이스에 속한
    경우를 구별하지 않는다. 둘 다 기본 템플릿으로 조용히 폴백해 id 열거를 막는다.
    """
    if template_id is not None:
        rows = await user_db.select(
            "prompt_templates",
            match={"id": template_id, "target_type": _PROMPT_TARGET_TYPE},
            limit=1,
        )
        if len(rows) == 1:
            return rows[0]
    return await _select_default_ask_template(user_db, workspace_id=workspace_id)


def _context_blocks(
    evidence: list[EvidenceHit],
    issuance: Mapping[str, tuple[str, str]],
    content_by_id: Mapping[str, str],
) -> tuple[str, str]:
    """이슈 발급 순서 그대로 위키/원문 컨텍스트 블록을 조립한다.

    별칭 번호는 `build_issuance_map()`이 이미 매긴 것을 그대로 조회한다 — 별도의
    카운터를 다시 세지 않는다. 둘이 어긋나면 프롬프트에 실리는 별칭과 실제 발급
    맵이 어긋나 CITE-01 전체가 무너진다.
    """
    alias_by_key = {(kind, real_id): alias for alias, (kind, real_id) in issuance.items()}
    wiki_blocks: list[str] = []
    source_blocks: list[str] = []
    for hit in evidence:
        if hit.kind == "wiki":
            alias = alias_by_key[("wiki", hit.document_id)]
            title = hit.metadata.get("title") or hit.document_id
            content = content_by_id.get(hit.document_id, "")
            wiki_blocks.append(f"[[wiki:{alias}]] {title}\n{content}")
        else:
            alias = alias_by_key[("source", hit.evidence_id)]
            raw_source_id = hit.metadata.get("raw_source_id") or ""
            chunk_index = hit.metadata.get("chunk_index")
            content = content_by_id.get(hit.evidence_id, "")
            source_blocks.append(f"[[src:{alias}]] ({raw_source_id} {chunk_index})\n{content}")
    return "\n\n".join(wiki_blocks), "\n\n".join(source_blocks)


def _error_token(status_code: int) -> str:
    return _ERROR_TOKENS.get(status_code, "llm_unavailable")


class AskService:
    """소스-of-truth: `POST /workspaces/{id}/ask`가 스트리밍하는 이벤트 시퀀스를 만든다.

    `ask()`는 `(event_name, payload)` 튜플을 내보내는 프레이밍-비관여 제너레이터다 —
    실제 `event: ...\\ndata: ...\\n\\n` 렌더링은 라우터의 `_format_sse()`가 맡는다
    (Test 5/6이 이벤트 **이름**과 순서를 단언하므로, 프레이밍은 서비스와 분리되어야
    독립적으로 테스트 가능하다).
    """

    def __init__(self, retrieval_service: RetrievalService, llm_client: LlmStreamClient) -> None:
        self._retrieval_service = retrieval_service
        self._llm_client = llm_client

    async def _finalize_turn(
        self,
        *,
        user_db: UserDb,
        workspace_id: UUID,
        thread_id: UUID,
        client_turn_id: UUID,
        answer_text: str,
        citations: dict[str, Any],
        status: str,
    ) -> UUID | None:
        """citations 조립 후 done 전에 한 논리 턴을 저장한다. 실패하면 done을 보내지 않는다."""
        stored_citations = {
            "text": citations.get("text") or "",
            "resolved": citations.get("resolved") or [],
        }
        try:
            rows = await user_db.rpc(
                "finalize_ask_turn",
                params={
                    "p_workspace_id": str(workspace_id),
                    "p_thread_id": str(thread_id),
                    "p_client_turn_id": str(client_turn_id),
                    "p_answer_text": answer_text,
                    "p_citations": stored_citations,
                    "p_status": status,
                },
            )
        except (WorkspaceForbidden, DatabaseError):
            return None
        if not rows or not rows[0].get("thread_id"):
            return None
        return UUID(str(rows[0]["thread_id"]))

    async def _yield_done_if_finalized(
        self,
        *,
        user_db: UserDb,
        workspace_id: UUID,
        thread_id: UUID,
        client_turn_id: UUID,
        answer_text: str,
        citations: dict[str, Any],
        status: str,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        persisted = await self._finalize_turn(
            user_db=user_db,
            workspace_id=workspace_id,
            thread_id=thread_id,
            client_turn_id=client_turn_id,
            answer_text=answer_text,
            citations=citations,
            status=status,
        )
        if persisted is None:
            return
        yield "done", {"thread_id": str(persisted)}

    async def ask(
        self,
        *,
        workspace_id: UUID,
        query: str,
        requested_k: int,
        template_id: str | None,
        user_db: UserDb,
        thread_id: UUID,
        client_turn_id: UUID,
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        result = await self._retrieval_service.retrieve(workspace_id, query, requested_k, user_db)
        if not result.evidence:
            # CITE-04 — 근거가 하나도 없으면 provider 호출을 아예 하지 않는다.
            yield "meta", {"thread_id": str(thread_id), "no_evidence": True}
            no_evidence_citations = {
                "text": NO_EVIDENCE_MESSAGE,
                "resolved": [],
                "cited_anchor_count": 0,
                "fabricated_anchor_count": 0,
                "dual_citation_rate": 0.0,
                "unsourced_sentence_ratio": 0.0,
            }
            yield "citations", no_evidence_citations
            async for event in self._yield_done_if_finalized(
                user_db=user_db,
                workspace_id=workspace_id,
                thread_id=thread_id,
                client_turn_id=client_turn_id,
                answer_text=NO_EVIDENCE_MESSAGE,
                citations=no_evidence_citations,
                status="no-evidence",
            ):
                yield event
            return

        issuance = build_issuance_map(result.evidence)
        content_by_id = await _fetch_evidence_content(
            user_db, workspace_id=workspace_id, evidence=result.evidence
        )
        template = await _select_ask_template(
            user_db, workspace_id=workspace_id, template_id=template_id
        )
        if template is None:
            # 0006 시드가 적용되지 않았다는 뜻 — 진행할 프롬프트 자체가 없다.
            yield "meta", {"thread_id": str(thread_id), "template_id": None}
            error_citations = {
                "error": "ask_template_unavailable",
                "resolved": [],
                "cited_anchor_count": 0,
                "fabricated_anchor_count": 0,
                "dual_citation_rate": 0.0,
                "unsourced_sentence_ratio": 0.0,
            }
            yield "citations", error_citations
            async for event in self._yield_done_if_finalized(
                user_db=user_db,
                workspace_id=workspace_id,
                thread_id=thread_id,
                client_turn_id=client_turn_id,
                answer_text="",
                citations=error_citations,
                status="error",
            ):
                yield event
            return

        wiki_context, source_context = _context_blocks(result.evidence, issuance, content_by_id)
        user_prompt = _render(
            str(template["template"]),
            {"question": query, "wiki_context": wiki_context, "source_context": source_context},
        )

        yield (
            "meta",
            {
                "thread_id": str(thread_id),
                "template_id": template["id"],
                "template_name": template["name"],
                "evidence_count": len(result.evidence),
                "policy_version": result.meta.get("policy_version"),
            },
        )

        accumulated: list[str] = []
        try:
            async with self._llm_client.stream(
                workspace_id=str(workspace_id),
                messages=[
                    {"role": "system", "content": str(template["system_prompt"])},
                    {"role": "user", "content": user_prompt},
                ],
            ) as upstream:
                if upstream.status_code >= 400:
                    error_citations = {
                        "error": _error_token(upstream.status_code),
                        "resolved": [],
                        "cited_anchor_count": 0,
                        "fabricated_anchor_count": 0,
                        "dual_citation_rate": 0.0,
                        "unsourced_sentence_ratio": 0.0,
                    }
                    yield "citations", error_citations
                    async for event in self._yield_done_if_finalized(
                        user_db=user_db,
                        workspace_id=workspace_id,
                        thread_id=thread_id,
                        client_turn_id=client_turn_id,
                        answer_text="",
                        citations=error_citations,
                        status="error",
                    ):
                        yield event
                    return
                async for line in upstream.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    payload = json.loads(line[len("data: ") :])
                    choices = payload.get("choices") or []
                    delta_text = ""
                    if choices:
                        delta_text = (choices[0].get("delta") or {}).get("content") or ""
                    if delta_text:
                        accumulated.append(delta_text)
                        yield "delta", {"text": delta_text}
        except asyncio.CancelledError:
            raise
        except (RuntimeError, httpx.HTTPError):
            # 설정 부재(RuntimeError) 또는 전송 계층 실패 — 둘 다 provider 미가용으로 다룬다.
            error_citations = {
                "error": "llm_unavailable",
                "resolved": [],
                "cited_anchor_count": 0,
                "fabricated_anchor_count": 0,
                "dual_citation_rate": 0.0,
                "unsourced_sentence_ratio": 0.0,
            }
            yield "citations", error_citations
            async for event in self._yield_done_if_finalized(
                user_db=user_db,
                workspace_id=workspace_id,
                thread_id=thread_id,
                client_turn_id=client_turn_id,
                answer_text="",
                citations=error_citations,
                status="error",
            ):
                yield event
            return

        full_text = "".join(accumulated)
        resolution = resolve_citations(full_text, issuance)
        success_citations = {
            "text": resolution.rendered_text,
            "resolved": resolution.resolved,
            "cited_anchor_count": resolution.cited_anchor_count,
            "fabricated_anchor_count": resolution.fabricated_anchor_count,
            "dual_citation_rate": resolution.dual_citation_rate,
            "unsourced_sentence_ratio": resolution.unsourced_sentence_ratio,
        }
        yield "citations", success_citations
        async for event in self._yield_done_if_finalized(
            user_db=user_db,
            workspace_id=workspace_id,
            thread_id=thread_id,
            client_turn_id=client_turn_id,
            answer_text=resolution.rendered_text,
            citations=success_citations,
            status="resolved",
        ):
            yield event
