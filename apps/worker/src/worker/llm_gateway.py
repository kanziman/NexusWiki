"""모든 LLM·임베딩 공급자 호출이 지나는 단일 경계.

관련 이슈: #161, #162
설계 근거: openspec/changes/ai-control-flow-accounting/design.md > D4
계약: openspec/changes/ai-control-flow-accounting/specs/usage-guardrails/spec.md

공급자가 사용량을 보고하는 즉시, 응답 검증보다 **먼저** `usage_events`에 기록한다. 이후의 검증
실패나 업서트 실패가 이미 지불한 비용을 지우지 못하게 하기 위해서다. 월 상한은 이 합계로
판정하므로 기록 누락은 곧 상한이 늦게 걸린다는 뜻이다.

공통 정책 주입과 데이터 수집 거부는 요청을 조립하는 `worker.llm`이 맡는다.
핸들러가 공급자 함수를 직접 부르면 `test_llm_gateway.py`의 구조
테스트가 실패한다.

소비자: `worker.handlers.compile`, `worker.handlers.conflict`, `worker.handlers.embed`,
`worker.__main__`
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
from pydantic import BaseModel

from nexuswiki_core.domain import UsageKind
from nexuswiki_core.llm_policy import LLM_POLICY_VERSION
from nexuswiki_core.observability import export_generation
from nexuswiki_core.trace import current_trace_id
from worker import embedding as embedding_provider
from worker import llm as llm_provider
from worker.embedding import EmbeddingResult, EmbeddingUsage
from worker.llm import AttemptUsage, LlmResult
from worker.settings import WorkerSettings

__all__ = [
    "LlmCallContext",
    "LlmGateway",
    "UsageSink",
    "open_answer_stream",
    "record_stream_usage",
]


class UsageSink(Protocol):
    """`ServiceDb`에서 이 경계가 쓰는 표면."""

    async def insert_usage_event(
        self, *, workspace_id: str, row: dict[str, Any]
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class LlmCallContext:
    """호출 하나의 귀속 정보.

    ⚠️ `metadata`에 프롬프트나 응답 본문을 싣지 않는다. `usage_events`는 멤버가 SELECT할 수
    있으므로 본문을 실으면 사용량 화면이 원문 유출 경로가 된다 (`0009:137-138`).
    """

    workspace_id: str
    call: str
    job_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class LlmGateway:
    """공급자 호출과 사용량 기록을 묶는다. 호출 수명 동안만 존재하는 얇은 객체다."""

    def __init__(
        self, sink: UsageSink, client: httpx.AsyncClient, settings: WorkerSettings
    ) -> None:
        self._sink = sink
        self._client = client
        self._settings = settings

    async def complete_structured(
        self,
        context: LlmCallContext,
        *,
        system_prompt: str,
        user_prompt: str,
        schema_model: type[BaseModel],
        max_tokens: int | None = None,
    ) -> LlmResult:
        """구조화 출력 호출. 재시도마다 그 시도의 사용량을 따로 기록한다."""

        async def record_attempt(attempt: AttemptUsage) -> None:
            attempt_meta: dict[str, Any] = {
                "attempt": attempt.attempt,
                # ⚠️ 품질 집계(0036)가 이 키로 측정된 호출을 판별한다. 빼면 모두 미측정으로 보인다.
                "policy_version": LLM_POLICY_VERSION,
            }
            if max_tokens is not None:
                attempt_meta["max_tokens"] = max_tokens
            if attempt.fence_stripped:
                attempt_meta["fence_stripped"] = True
            if attempt.violation is not None:
                attempt_meta["violation"] = attempt.violation
            if attempt.exhausted:
                attempt_meta["exhausted"] = True
            await _record(
                self._sink,
                context,
                kind=UsageKind.LLM,
                provider=attempt.provider,
                model=attempt.model,
                prompt_tokens=attempt.prompt_tokens,
                completion_tokens=attempt.completion_tokens,
                total_tokens=attempt.total_tokens,
                cost_micros=attempt.cost_micros,
                duration_ms=attempt.duration_ms,
                metadata=attempt_meta,
            )

        extra_kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            extra_kwargs["max_tokens"] = max_tokens
        return await llm_provider.complete_structured(
            self._client,
            settings=self._settings,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema_model=schema_model,
            on_attempt=record_attempt,
            **extra_kwargs,
        )

    async def embed_texts(self, context: LlmCallContext, *, texts: list[str]) -> EmbeddingResult:
        """임베딩 호출. 입력이 비어 공급자를 부르지 않았으면 콜백이 불리지 않아 기록도 없다."""
        started = time.perf_counter()

        async def record_usage(usage: EmbeddingUsage) -> None:
            await _record(
                self._sink,
                context,
                kind=UsageKind.EMBEDDING,
                provider=usage.provider,
                model=usage.model,
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                total_tokens=usage.total_tokens,
                cost_micros=usage.cost_micros,
                duration_ms=_elapsed_ms(started),
                metadata={},
            )

        return await embedding_provider.embed_texts(
            self._client, settings=self._settings, texts=texts, on_usage=record_usage
        )


def open_answer_stream(
    client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    messages: list[dict[str, str]],
    max_tokens: int | None = None,
    on_generation: Callable[[str], Awaitable[None]] | None = None,
    evidence_research: bool = False,
) -> AsyncIterator[bytes]:
    """Ask 답변 스트림을 연다.

    스트림 수명은 내부 리스너가 소유하고 종료 시점도 그쪽만 알기 때문에, 사용량은 끝난 뒤
    `record_stream_usage`로 남긴다.
    """
    if max_tokens is None and on_generation is None and not evidence_research:
        return llm_provider.stream_chat(client, settings=settings, messages=messages)
    return llm_provider.stream_chat(
        client,
        settings=settings,
        messages=messages,
        max_tokens=max_tokens,
        on_generation=on_generation,
        **({"evidence_research": True} if evidence_research else {}),
    )


async def record_stream_usage(
    sink: UsageSink,
    context: LlmCallContext,
    *,
    usage: Mapping[str, Any],
    duration_ms: int,
    incomplete: bool,
    ask_call_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    """스트림 한 건의 사용량을 남긴다.

    ⚠️ `incomplete`면 공급자가 최종 사용량을 보내기 전에 끝난 호출이라 비용이 실제보다 작거나
    0일 수 있다. 숨기지 않고 표시해 Control Room에서 건수를 볼 수 있게 한다.
    """
    await _record(
        sink,
        context,
        kind=UsageKind.LLM,
        provider=str(usage.get("provider") or llm_provider.PROVIDER_NAME),
        model=str(usage.get("model") or "unknown"),
        prompt_tokens=llm_provider.token_count(usage.get("prompt_tokens")),
        completion_tokens=llm_provider.token_count(usage.get("completion_tokens")),
        total_tokens=llm_provider.token_count(usage.get("total_tokens")),
        cost_micros=llm_provider.cost_micros(usage),
        duration_ms=duration_ms,
        metadata={
            "policy_version": LLM_POLICY_VERSION,
            **({"incomplete": True} if incomplete else {}),
        },
        ask_call_id=ask_call_id,
        trace_id=trace_id,
    )


async def _record(
    sink: UsageSink,
    context: LlmCallContext,
    *,
    kind: UsageKind,
    provider: str,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cost_micros: int,
    duration_ms: int,
    metadata: Mapping[str, Any],
    ask_call_id: str | None = None,
    trace_id: str | None = None,
) -> None:
    await sink.insert_usage_event(
        workspace_id=context.workspace_id,
        row={
            **({"ask_call_id": ask_call_id} if ask_call_id is not None else {}),
            "job_id": context.job_id,
            "trace_id": trace_id or current_trace_id(),
            "kind": kind.value,
            "provider": provider,
            "model": model,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "cost_micros": cost_micros,
            "duration_ms": duration_ms,
            "metadata": {"call": context.call, **context.metadata, **metadata},
        },
    )
    # 기록이 끝난 뒤에 내보낸다. 내보내기는 예외를 던지지 않아 사용량과 재시도 흐름에 닿지 않는다.
    export_generation(
        name=context.call,
        as_type="embedding" if kind is UsageKind.EMBEDDING else "generation",
        workspace_id=context.workspace_id,
        model=model,
        provider=provider,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        cost_micros=cost_micros,
        duration_ms=duration_ms,
        metadata={"call": context.call, **context.metadata, **metadata},
    )


def _elapsed_ms(started: float) -> int:
    return round((time.perf_counter() - started) * 1000)
