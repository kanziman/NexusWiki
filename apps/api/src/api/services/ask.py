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
from dataclasses import dataclass, replace
from typing import Any, Final, Protocol
from uuid import UUID

import httpx

from api.db.user import UserDb
from api.errors import DatabaseError, WorkspaceForbidden
from api.services.retrieval import RetrievalResult, RetrievalService
from nexuswiki_core.answer_contract import (
    build_fallback_answer,
    check_answer_contract,
    repair_instruction,
)
from nexuswiki_core.citations import (
    BROAD_ANCHOR_PATTERN,
    ISSUED_ANCHOR_PATTERN,
    neutralize_anchor_brackets,
    strip_forged_anchors,
)
from nexuswiki_core.context_budget import (
    DEFAULT_ASK_MAX_CONTEXT_TOKENS,
    AskContextBudgetResult,
    allocate_ask_context_budget,
    select_dual_evidence,
    truncate_text_to_tokens,
)
from nexuswiki_core.logging import get_logger
from nexuswiki_core.router import RouteDecision, decide_ask_route
from nexuswiki_core.rrf import EvidenceHit
from nexuswiki_core.sentences import split_sentences
from nexuswiki_core.trace import TraceRecorder, trace_headers

__all__ = [
    "NO_EVIDENCE_MESSAGE",
    "AskService",
    "AskTurnExporter",
    "CitationResolution",
    "HttpAskTurnExporter",
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

# 수리 호출에 되돌려 보내는 초안의 상한. 위반 답변이 재주입 비용을 키우면 안 된다.
_REPAIR_DRAFT_MAX_TOKENS: Final[int] = 2000
_MAX_RENDER_ROUNDS: Final[int] = 8

# 내보내기는 개발자용 사본이다. 답변 완료를 지연시키지 않도록 짧게 끊는다.
_TURN_EXPORT_TIMEOUT_SECONDS: Final[float] = 2.0

_logger = get_logger(__name__)

# 응답 뒤에 끝나는 내보내기 태스크. 강한 참조가 없으면 GC가 완료 전에 거둬 갈 수 있다.
_pending_turn_exports: set[asyncio.Task[None]] = set()


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
            headers={"Authorization": f"Bearer {self._token}", **trace_headers()},
            timeout=httpx.Timeout(connect=5.0, read=self._timeout_seconds, write=5.0, pool=5.0),
        )


class AskTurnExporter(Protocol):
    """종결된 턴을 외부 관측으로 내보내는 경계. 어떤 실패도 호출자에게 전달하지 않는다."""

    def export(
        self, *, workspace_id: str, control_report: Mapping[str, Any], persisted: bool
    ) -> None: ...


class HttpAskTurnExporter:
    """턴 보고서를 워커에 넘겨 내보내게 한다.

    ⚠️ API는 Langfuse 키를 갖지 않는다. 그 키로는 전 테넌트의 trace를 읽고 지울 수 있어서, API에
    두면 RLS 바깥의 교차 테넌트 능력이 생긴다 (design D8). 워커가 이미 키를 소유하므로 LLM 호출과
    같은 내부 토큰 경계로 넘긴다. 답변을 기다리게 하지 않으려고 응답과 분리해 보낸다.
    """

    def __init__(self, client: httpx.AsyncClient, *, url: str | None, token: str | None) -> None:
        self._client, self._url, self._token = client, url, token

    def export(
        self, *, workspace_id: str, control_report: Mapping[str, Any], persisted: bool
    ) -> None:
        if not self._url or not self._token:
            return
        task = asyncio.create_task(
            self._send(
                self._url,
                {
                    "workspace_id": workspace_id,
                    "control_report": dict(control_report),
                    "persisted": persisted,
                },
                # 태스크 안에서 읽어도 같은 값이지만, 호출 시점의 trace임을 코드로 드러낸다.
                {"Authorization": f"Bearer {self._token}", **trace_headers()},
            )
        )
        _pending_turn_exports.add(task)
        task.add_done_callback(_pending_turn_exports.discard)

    async def _send(self, url: str, body: dict[str, Any], headers: dict[str, str]) -> None:
        try:
            response = await self._client.post(
                f"{url.rstrip('/')}/internal/ask-turn-export",
                json=body,
                headers=headers,
                timeout=_TURN_EXPORT_TIMEOUT_SECONDS,
            )
        except Exception as exc:  # noqa: BLE001 - 답변과 무관한 사본이다. 태스크 밖으로 내지 않는다.
            # ⚠️ 예외 문구를 남기지 않는다. 내부 토큰이 담긴 요청 정보가 섞일 수 있다.
            _logger.warning("ask.turn_export_failed", error_type=type(exc).__name__)
            return
        if response.is_error:
            _logger.warning("ask.turn_export_rejected", status_code=response.status_code)


async def drain_turn_exports(timeout_seconds: float = _TURN_EXPORT_TIMEOUT_SECONDS) -> None:
    """HTTP 클라이언트를 닫기 전에 남은 내보내기를 기다린다. 못 끝낸 건수는 로그로 남긴다."""
    if not _pending_turn_exports:
        return
    _, unfinished = await asyncio.wait(set(_pending_turn_exports), timeout=timeout_seconds)
    if unfinished:
        _logger.warning("ask.turn_exports_abandoned", count=len(unfinished))


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
    # 지운 자리에서 미발급 앵커가 재조립될 수 있다. 횟수를 제한해 비용이 입력 크기에 묶이게 한다.
    for _ in range(_MAX_RENDER_ROUNDS):
        stripped = BROAD_ANCHOR_PATTERN.sub(_strip_fabricated, rendered_text)
        if stripped == rendered_text:
            break
        rendered_text = stripped
    else:
        # 상한까지 안정되지 않은 깊은 중첩이다. 믿을 앵커를 가릴 수 없으므로 인용으로 치지 않아
        # 인용 계약 위반으로 수리나 근거 목록으로 끝나게 한다.
        rendered_text = neutralize_anchor_brackets(rendered_text)
        resolved_aliases = set()
    # ⚠️ 지표는 위조를 지운 뒤의 텍스트로 잰다. 원문으로 재면 위조 앵커만 달린 문장이
    #    이중 인용으로 계산되어 품질 지표가 조용히 부풀려진다 (design D6).
    sentences = split_sentences(rendered_text)
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
) -> tuple[dict[str, str], list[EvidenceHit]]:
    """evidence가 가리키는 실제 본문을 배치로 페치하고 위키 메타데이터(slug·title)를 보강한다.

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
    wiki_meta: dict[str, dict[str, str]] = {}
    if wiki_ids:
        response = await user_db._client.get(  # noqa: SLF001 - 제한적 in-filter seam
            f"{user_db._base_url}/wiki_pages",
            params={
                "id": f"in.({','.join(wiki_ids)})",
                "workspace_id": f"eq.{workspace_id}",
                "select": "id,slug,title,content",
            },
            headers=user_db._headers,  # noqa: SLF001
        )
        rows = user_db._payload(response)  # noqa: SLF001
        for row in rows if isinstance(rows, list) else [rows]:
            doc_id = str(row["id"])
            content[doc_id] = str(row.get("content") or "")
            meta_row: dict[str, str] = {}
            if isinstance(row.get("slug"), str) and row["slug"]:
                meta_row["slug"] = row["slug"]
            if isinstance(row.get("title"), str) and row["title"]:
                meta_row["title"] = row["title"]
            if meta_row:
                wiki_meta[doc_id] = meta_row
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

    enriched: list[EvidenceHit] = []
    for hit in evidence:
        if hit.kind == "wiki" and hit.document_id in wiki_meta:
            enriched.append(replace(hit, metadata={**wiki_meta[hit.document_id], **hit.metadata}))
        else:
            enriched.append(hit)
    return content, enriched


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
            # ⚠️ 이미 저장된 제목과 본문에 앵커가 남아 있을 수 있다. 그대로 실으면 모델이 베껴 쓴
            #    앵커가 이 요청의 별칭으로 해소된다.
            title = strip_forged_anchors(str(hit.metadata.get("title") or hit.document_id))
            content = strip_forged_anchors(content_by_id.get(hit.document_id, ""))
            wiki_blocks.append(f"[[wiki:{alias}]] {title}\n{content}")
        else:
            alias = alias_by_key[("source", hit.evidence_id)]
            raw_source_id = hit.metadata.get("raw_source_id") or ""
            chunk_index = hit.metadata.get("chunk_index")
            content = strip_forged_anchors(content_by_id.get(hit.evidence_id, ""))
            source_blocks.append(f"[[src:{alias}]] ({raw_source_id} {chunk_index})\n{content}")
    return "\n\n".join(wiki_blocks), "\n\n".join(source_blocks)


def _error_token(status_code: int) -> str:
    return _ERROR_TOKENS.get(status_code, "llm_unavailable")


class _AnswerStreamFailed(RuntimeError):
    """HTTP 200으로 시작한 답변 스트림이 도중에 실패했다.

    `AskService.ask`의 기존 공급자 미가용 분기로 수렴시키려고 `RuntimeError`를 상속한다.
    """


def _delta_text(line: str) -> str:
    """SSE `data:` 한 줄에서 답변 조각을 꺼낸다. 실패 프레임이면 예외를 던진다.

    ⚠️ OpenRouter는 스트림 중간 오류를 HTTP 200 안의 이벤트로 보낸다(최상위 `error` +
    `finish_reason: "error"`). 이를 놓치면 잘린 답변이 정상 답변으로 저장된다. 공급자
    메시지는 예외에 담지 않는다. 깨진 프레임을 그대로 올려 보내면 어떤 분기도 잡지 못해
    턴이 `streaming`에 영원히 남는다 (design D6).
    """
    try:
        payload = json.loads(line[len("data: ") :])
    except ValueError:
        raise _AnswerStreamFailed("malformed_frame") from None
    if not isinstance(payload, dict) or payload.get("error") is not None:
        raise _AnswerStreamFailed("provider_error_frame")
    # ⚠️ 파싱은 되지만 형태가 틀린 프레임도 실패다. 그대로 두면 속성 접근이나 뒤의 `join`에서
    #    `AttributeError`와 `TypeError`가 나고, 어떤 분기도 잡지 못해 턴이 `streaming`에 남는다.
    # ⚠️ `x or []`로 기본값을 주지 않는다. `0`이나 `""` 같은 틀린 값이 빈 값으로 바뀌어 타입 검사를
    #    건너뛰고, 잘린 답변이 해결된 답변으로 저장된다. 부재와 `null`만 "내용 없음"이다.
    choices = payload.get("choices")
    if choices is None:
        return ""
    if not isinstance(choices, list):
        raise _AnswerStreamFailed("malformed_frame")
    if not choices:
        return ""
    choice = choices[0]
    if not isinstance(choice, dict):
        raise _AnswerStreamFailed("malformed_frame")
    if choice.get("finish_reason") == "error":
        raise _AnswerStreamFailed("provider_error_frame")
    delta = choice.get("delta")
    if delta is None:
        return ""
    if not isinstance(delta, dict):
        raise _AnswerStreamFailed("malformed_frame")
    content = delta.get("content")
    if content is None:
        return ""
    if not isinstance(content, str):
        raise _AnswerStreamFailed("malformed_frame")
    return content


def _error_citations(token: str) -> dict[str, Any]:
    return {
        "error": token,
        "resolved": [],
        "cited_anchor_count": 0,
        "fabricated_anchor_count": 0,
        "dual_citation_rate": 0.0,
        "unsourced_sentence_ratio": 0.0,
    }


def _control_report(
    *,
    recorder: TraceRecorder,
    route: RouteDecision | None,
    budget: AskContextBudgetResult | None,
    quality: Mapping[str, Any] | None,
    retrieval_meta: Mapping[str, Any],
    evidence: list[EvidenceHit],
    citations: Mapping[str, Any],
    outcome: str,
) -> dict[str, Any]:
    """턴에 함께 저장할 통제 보고서.

    ⚠️ 허용 필드로만 조립한다. 검색 메타의 `raw_hit_ids`나 답변 텍스트가 섞이면 복원 경로와
    Control Room이 본문 유출 경로가 된다.

    검색이 실패한 턴에는 결정이 없어 `route`가 `None`이다. 집계 RPC는 결정이 없는 행을 거른다.
    """
    return {
        "version": 1,
        "outcome": outcome,
        "route": route.as_report() if route is not None else None,
        "budget": budget.as_report() if budget is not None else None,
        "quality": dict(quality) if quality is not None else None,
        "total_ms": recorder.total_ms(),
        "spans": recorder.spans(),
        "evidence": {
            "wiki": sum(1 for hit in evidence if hit.kind == "wiki"),
            "source": sum(1 for hit in evidence if hit.kind == "source"),
        },
        "retrieval": {
            "policy_version": retrieval_meta.get("policy_version"),
            "missing_channels": _missing_channels(retrieval_meta),
        },
        "citation": {
            key: citations.get(key, 0)
            for key in (
                "cited_anchor_count",
                "fabricated_anchor_count",
                "dual_citation_rate",
                "unsourced_sentence_ratio",
            )
        },
    }


def _missing_channels(retrieval_meta: Mapping[str, Any]) -> list[str]:
    """이번 요청에서 실패한 검색 채널 이름.

    ⚠️ `failed`만 고른다. 정책으로 꺼 둔 그래프(`disabled`)까지 넣으면 모든 답변에
    부분 검색 안내가 떠서 안내가 의미를 잃는다.
    """
    return sorted(
        name
        for name, channel in retrieval_meta.items()
        if isinstance(channel, Mapping) and channel.get("status") == "failed"
    )


class AskService:
    """소스-of-truth: `POST /workspaces/{id}/ask`가 스트리밍하는 이벤트 시퀀스를 만든다.

    `ask()`는 `(event_name, payload)` 튜플을 내보내는 프레이밍-비관여 제너레이터다 —
    실제 `event: ...\\ndata: ...\\n\\n` 렌더링은 라우터의 `_format_sse()`가 맡는다
    (Test 5/6이 이벤트 **이름**과 순서를 단언하므로, 프레이밍은 서비스와 분리되어야
    독립적으로 테스트 가능하다).
    """

    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_client: LlmStreamClient,
        turn_exporter: AskTurnExporter | None = None,
        *,
        max_context_tokens: int = DEFAULT_ASK_MAX_CONTEXT_TOKENS,
        quality_mode: str = "enforce",
    ) -> None:
        self._quality_mode = quality_mode
        self._retrieval_service = retrieval_service
        self._llm_client = llm_client
        self._turn_exporter = turn_exporter
        self._max_context_tokens = max_context_tokens

    async def _repair_answer(
        self,
        *,
        workspace_id: UUID,
        system_prompt: str,
        user_prompt: str,
        draft: str,
        violations: tuple[str, ...],
        issuance: Mapping[str, tuple[str, str]],
    ) -> str | None:
        """위반을 되먹여 1회 다시 묻는다. 어떤 실패든 `None`이며 호출부가 Fallback으로 끝낸다.

        비용은 같은 내부 경계를 지나므로 일반 호출과 똑같이 예약·기록된다.
        """
        collected: list[str] = []
        try:
            async with self._llm_client.stream(
                workspace_id=str(workspace_id),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                    {
                        "role": "assistant",
                        "content": truncate_text_to_tokens(draft, _REPAIR_DRAFT_MAX_TOKENS)[0]
                        or "(빈 답변)",
                    },
                    {"role": "user", "content": repair_instruction(violations, list(issuance))},
                ],
            ) as upstream:
                if upstream.status_code >= 400:
                    return None
                async for line in upstream.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    collected.append(_delta_text(line))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - 수리는 부가 경로다. 실패가 턴 종결을 막으면 안 된다.
            # ⚠️ 여기서 놓치면 `citations`와 `done` 없이 끊겨 턴이 `streaming`에 영구히 남는다.
            _logger.warning("ask.repair_failed", error_type=type(exc).__name__)
            return None
        return "".join(collected)

    def _export_turn(
        self, *, workspace_id: UUID, control_report: Mapping[str, Any], persisted: bool
    ) -> None:
        if self._turn_exporter is not None:
            self._turn_exporter.export(
                workspace_id=str(workspace_id), control_report=control_report, persisted=persisted
            )

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
        control_report: dict[str, Any],
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
                    "p_control_report": control_report,
                },
            )
        except (WorkspaceForbidden, DatabaseError, httpx.HTTPError) as exc:
            # ⚠️ 전송 실패도 여기서 받는다. 예외가 스트림 밖으로 나가면 내보내기도 기록도 없이
            #    끊긴다.
            _logger.warning("ask.finalize_failed", error_type=type(exc).__name__)
            self._export_turn(
                workspace_id=workspace_id, control_report=control_report, persisted=False
            )
            return None
        persisted = bool(rows and rows[0].get("thread_id"))
        self._export_turn(
            workspace_id=workspace_id, control_report=control_report, persisted=persisted
        )
        if not persisted:
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
        control_report: dict[str, Any],
    ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
        persisted = await self._finalize_turn(
            user_db=user_db,
            workspace_id=workspace_id,
            thread_id=thread_id,
            client_turn_id=client_turn_id,
            answer_text=answer_text,
            citations=citations,
            status=status,
            control_report=control_report,
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
        recorder = TraceRecorder()
        recorder.start("retrieval")
        result: RetrievalResult | None = None
        route: RouteDecision | None = None
        budget: AskContextBudgetResult | None = None
        quality: dict[str, Any] | None = None

        def report(citations: Mapping[str, Any], outcome: str) -> dict[str, Any]:
            return _control_report(
                recorder=recorder,
                route=route,
                budget=budget,
                quality=quality,
                retrieval_meta=result.meta if result is not None else {},
                evidence=(
                    list(budget.included_evidence)
                    if budget is not None
                    else (result.evidence if result is not None else [])
                ),
                citations=citations,
                outcome=outcome,
            )

        async def fail_preparation(
            exc: Exception, token: str
        ) -> AsyncIterator[tuple[str, dict[str, Any]]]:
            """라우터가 턴을 시작한 뒤의 실패다. HTTP 오류로 바꿀 수 없으니 오류 턴으로 닫는다.

            ⚠️ 이 처리가 없으면 턴이 `streaming`에 영원히 남고 클라이언트는 끊긴 스트림만 본다.
            예외 문구는 로그에 남기지 않는다. 요청 정보나 본문 조각이 섞일 수 있다.

            ⚠️ DB·전송 실패는 운영 중 일어날 수 있지만 그 밖의 예외는 코드 결함이므로 오류 수준으로
            남긴다. 로그 키에 `token`을 쓰지 않는다. `REDACTED_KEYS`에 걸려 분류가 지워진다.
            """
            log = (
                _logger.warning
                if isinstance(exc, DatabaseError | WorkspaceForbidden | httpx.HTTPError)
                else _logger.error
            )
            log(
                "ask.preparation_failed",
                error_type=type(exc).__name__,
                sqlstate=getattr(exc, "sqlstate", None),
                failure=token,
            )
            citations = _error_citations(token)
            yield (
                "meta",
                {
                    "thread_id": str(thread_id),
                    "missing_channels": _missing_channels(result.meta) if result else [],
                },
            )
            yield "citations", citations
            async for event in self._yield_done_if_finalized(
                user_db=user_db,
                workspace_id=workspace_id,
                thread_id=thread_id,
                client_turn_id=client_turn_id,
                answer_text="",
                citations=citations,
                status="error",
                control_report=report(citations, "error"),
            ):
                yield event

        try:
            result = await self._retrieval_service.retrieve(
                workspace_id, query, requested_k, user_db
            )
            # 조립 단계의 쿼터가 볼 수 있도록 여기서 위키와 원문을 함께 고른다. 후보가 없는
            # 구현(테스트 대역)은 검색 결과를 그대로 쓴다.
            if result.candidates:
                result = replace(
                    result,
                    evidence=select_dual_evidence(result.candidates, requested_k=requested_k),
                )
            # ⚠️ 기록만 한다. 아래의 근거 0건 단락 외에는 이 결정으로 분기하지 않는다 (design D7).
            route = decide_ask_route(query, result.evidence)
        except Exception as exc:  # noqa: BLE001 - 턴을 종결하는 것이 이 분기의 목적이다.
            async for event in fail_preparation(exc, "retrieval_unavailable"):
                yield event
            return
        missing_channels = _missing_channels(result.meta)

        if not result.evidence:
            # CITE-04 — 근거가 하나도 없으면 provider 호출을 아예 하지 않는다.
            yield (
                "meta",
                {
                    "thread_id": str(thread_id),
                    "no_evidence": True,
                    "missing_channels": missing_channels,
                },
            )
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
                control_report=report(no_evidence_citations, "no-evidence"),
            ):
                yield event
            return

        recorder.start("context")
        try:
            content_by_id, enriched_evidence = await _fetch_evidence_content(
                user_db, workspace_id=workspace_id, evidence=result.evidence
            )
            # 벡터 채널만 히트한 위키 문서의 slug·title이 wiki_pages 조회로 보강되면
            # LOOKUP 판정도 보강된 메타데이터로 다시 계산한다.
            route = decide_ask_route(query, enriched_evidence)
            budget = allocate_ask_context_budget(
                enriched_evidence,
                content_by_id,
                max_context_tokens=self._max_context_tokens,
            )
            included_evidence = list(budget.included_evidence)
            issuance = build_issuance_map(included_evidence)
            template = await _select_ask_template(
                user_db, workspace_id=workspace_id, template_id=template_id
            )
            if template is not None:
                wiki_context, source_context = _context_blocks(
                    included_evidence, issuance, budget.content_by_id
                )
                user_prompt = _render(
                    str(template["template"]),
                    {
                        "question": query,
                        "wiki_context": wiki_context,
                        "source_context": source_context,
                    },
                )
                template_meta = {
                    "template_id": template["id"],
                    "template_name": template["name"],
                }
                system_prompt = str(template["system_prompt"])
        except Exception as exc:  # noqa: BLE001 - 턴을 종결하는 것이 이 분기의 목적이다.
            async for event in fail_preparation(exc, "context_unavailable"):
                yield event
            return

        if template is None:
            # 0006 시드가 적용되지 않았다는 뜻 — 진행할 프롬프트 자체가 없다.
            yield "meta", {"thread_id": str(thread_id), "template_id": None}
            error_citations = _error_citations("ask_template_unavailable")
            yield "citations", error_citations
            async for event in self._yield_done_if_finalized(
                user_db=user_db,
                workspace_id=workspace_id,
                thread_id=thread_id,
                client_turn_id=client_turn_id,
                answer_text="",
                citations=error_citations,
                status="error",
                control_report=report(error_citations, "error"),
            ):
                yield event
            return

        yield (
            "meta",
            {
                "thread_id": str(thread_id),
                **template_meta,
                "evidence_count": len(result.evidence),
                "policy_version": result.meta.get("policy_version"),
                "missing_channels": missing_channels,
            },
        )

        accumulated: list[str] = []
        recorder.start("llm_stream")
        try:
            async with self._llm_client.stream(
                workspace_id=str(workspace_id),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            ) as upstream:
                if upstream.status_code >= 400:
                    error_citations = _error_citations(_error_token(upstream.status_code))
                    yield "citations", error_citations
                    async for event in self._yield_done_if_finalized(
                        user_db=user_db,
                        workspace_id=workspace_id,
                        thread_id=thread_id,
                        client_turn_id=client_turn_id,
                        answer_text="",
                        citations=error_citations,
                        status="error",
                        control_report=report(error_citations, "error"),
                    ):
                        yield event
                    return
                async for line in upstream.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    delta_text = _delta_text(line)
                    if delta_text:
                        accumulated.append(delta_text)
                        yield "delta", {"text": delta_text}
        except asyncio.CancelledError:
            raise
        except (RuntimeError, httpx.HTTPError):
            # 설정 부재·스트림 도중 실패(RuntimeError) 또는 전송 계층 실패 — 모두 provider
            # 미가용으로 다룬다. 이미 보낸 델타는 저장하지 않고 오류 상태가 대체한다.
            error_citations = _error_citations("llm_unavailable")
            yield "citations", error_citations
            async for event in self._yield_done_if_finalized(
                user_db=user_db,
                workspace_id=workspace_id,
                thread_id=thread_id,
                client_turn_id=client_turn_id,
                answer_text="",
                citations=error_citations,
                status="error",
                control_report=report(error_citations, "error"),
            ):
                yield event
            return

        recorder.start("citation")
        full_text = "".join(accumulated)
        resolution = resolve_citations(full_text, issuance)
        violations: tuple[str, ...] = ()
        if self._quality_mode != "off":
            violations = check_answer_contract(
                resolution.rendered_text,
                cited_anchor_count=resolution.cited_anchor_count,
                fabricated_anchor_count=resolution.fabricated_anchor_count,
            )
        terminal_status = "resolved"
        repair_attempted = False
        repaired = False
        if violations and self._quality_mode == "enforce":
            # ⚠️ 델타를 보내지 않고 모아서 아래 `citations.text`로 교체한다. SSE 순서는 그대로다
            #    (ai-control-output-contract D6).
            recorder.start("repair")
            repair_attempted = True
            repaired_text = await self._repair_answer(
                workspace_id=workspace_id,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                draft=resolution.rendered_text,
                violations=violations,
                issuance=issuance,
            )
            repaired_resolution = (
                resolve_citations(repaired_text, issuance) if repaired_text else None
            )
            if repaired_resolution is not None and not check_answer_contract(
                repaired_resolution.rendered_text,
                cited_anchor_count=repaired_resolution.cited_anchor_count,
                fabricated_anchor_count=repaired_resolution.fabricated_anchor_count,
            ):
                resolution = repaired_resolution
                repaired = True
            else:
                # 수리도 실패하면 모델 없이 끝낸다. 앵커는 발급 맵에서만 나온다.
                resolution = resolve_citations(
                    build_fallback_answer(included_evidence, issuance, budget.content_by_id),
                    issuance,
                )
                terminal_status = "fallback"
        quality = {
            "mode": self._quality_mode,
            "violations": list(violations),
            "repair_attempted": repair_attempted,
            "repaired": repaired,
            "fallback": terminal_status == "fallback",
        }
        success_citations = {
            "text": resolution.rendered_text,
            "resolved": resolution.resolved,
            "cited_anchor_count": resolution.cited_anchor_count,
            "fabricated_anchor_count": resolution.fabricated_anchor_count,
            "dual_citation_rate": resolution.dual_citation_rate,
            "unsourced_sentence_ratio": resolution.unsourced_sentence_ratio,
        }
        if terminal_status == "fallback":
            success_citations["fallback"] = True
        yield "citations", success_citations
        async for event in self._yield_done_if_finalized(
            user_db=user_db,
            workspace_id=workspace_id,
            thread_id=thread_id,
            client_turn_id=client_turn_id,
            answer_text=resolution.rendered_text,
            citations=success_citations,
            status=terminal_status,
            control_report=report(success_citations, terminal_status),
        ):
            yield event
