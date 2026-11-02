"""고정 OpenRouter 공급자로 임베딩을 만든다.

관련 태스크: P2-EMB-01
설계 근거: 03-CONTEXT.md > D-04, D-05
"""

from __future__ import annotations

import math
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Final

import httpx

from worker.errors import EmbeddingProviderMismatch, ProviderCreditExhausted, ProviderError
from worker.settings import WorkerSettings

EMBEDDING_DIMENSIONS: Final[int] = 1024


@dataclass(frozen=True)
class EmbeddingResult:
    vectors: list[list[float]]
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_micros: int
    provider: str
    model: str


@dataclass(frozen=True)
class EmbeddingUsage:
    """공급자 응답 하나의 사용량. 공급자 일치나 차원 검증과 무관하게 이미 지불한 값이다."""

    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_micros: int
    provider: str
    model: str


def embedding_version(settings: WorkerSettings) -> str:
    return f"{settings.EMBEDDING_MODEL}@{settings.EMBEDDING_PROVIDER}-v1"


async def embed_texts(
    client: httpx.AsyncClient,
    *,
    settings: WorkerSettings,
    texts: list[str],
    on_usage: Callable[[EmbeddingUsage], Awaitable[None]] | None = None,
) -> EmbeddingResult:
    """⚠️ `on_usage`는 검증보다 먼저 부른다. 공급자나 차원이 맞지 않아 결과를 버려도 비용은
    청구되므로, 뒤로 미루면 그 금액이 월 상한에서 빠진다 (ai-control-flow-accounting D4).
    """
    if not texts:
        return EmbeddingResult(
            [], 0, 0, 0, 0, str(settings.EMBEDDING_PROVIDER), str(settings.EMBEDDING_MODEL)
        )
    body = {
        "model": settings.EMBEDDING_MODEL,
        "input": texts,
        "encoding_format": "float",
        "provider": {
            "order": [settings.EMBEDDING_PROVIDER],
            "allow_fallbacks": False,
            "data_collection": "deny",
        },
    }
    response = await client.post("/embeddings", json=body)
    if response.is_error:
        if response.status_code == 402:
            raise ProviderCreditExhausted(provider="openrouter", kind="embedding")
        raise ProviderError(
            provider="openrouter", status_code=response.status_code, kind="embedding"
        )
    data: dict[str, Any] = response.json()
    served = str(data.get("provider") or settings.EMBEDDING_PROVIDER)
    usage = data.get("usage") or {}
    reported = EmbeddingUsage(
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
        int(usage.get("total_tokens") or 0),
        math.ceil(float(usage.get("cost") or 0) * 1_000_000),
        served,
        str(data.get("model") or settings.EMBEDDING_MODEL),
    )
    if on_usage is not None:
        await on_usage(reported)
    # OpenRouter 요청 slug(`deepinfra/fp32`)와 응답 표시명(`DeepInfra`)은 형식이 다르다.
    requested_host = str(settings.EMBEDDING_PROVIDER).split("/", 1)[0].casefold()
    if served.casefold() != requested_host:
        raise EmbeddingProviderMismatch(
            provider="openrouter", requested=str(settings.EMBEDDING_PROVIDER), served=served
        )
    vectors = [item["embedding"] for item in data.get("data", [])]
    if any(len(v) != EMBEDDING_DIMENSIONS for v in vectors):
        raise ValueError("embedding_dimension_mismatch")
    return EmbeddingResult(
        vectors,
        reported.prompt_tokens,
        reported.completion_tokens,
        reported.total_tokens,
        reported.cost_micros,
        reported.provider,
        reported.model,
    )
