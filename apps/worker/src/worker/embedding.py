"""고정 OpenRouter 공급자로 임베딩을 만든다.

관련 태스크: P2-EMB-01
설계 근거: 03-CONTEXT.md > D-04, D-05
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Final

import httpx

from worker.errors import EmbeddingProviderMismatch, ProviderError
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


def embedding_version(settings: WorkerSettings) -> str:
    return f"{settings.EMBEDDING_MODEL}@{settings.EMBEDDING_PROVIDER}-v1"


async def embed_texts(
    client: httpx.AsyncClient, *, settings: WorkerSettings, texts: list[str]
) -> EmbeddingResult:
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
        raise ProviderError(
            provider="openrouter", status_code=response.status_code, kind="embedding"
        )
    data = response.json()
    served = str(data.get("provider") or settings.EMBEDDING_PROVIDER)
    if served != settings.EMBEDDING_PROVIDER:
        raise EmbeddingProviderMismatch(
            provider="openrouter", requested=str(settings.EMBEDDING_PROVIDER), served=served
        )
    vectors = [item["embedding"] for item in data.get("data", [])]
    if any(len(v) != EMBEDDING_DIMENSIONS for v in vectors):
        raise ValueError("embedding_dimension_mismatch")
    usage = data.get("usage") or {}
    cost = math.ceil(float(usage.get("cost") or 0) * 1_000_000)
    return EmbeddingResult(
        vectors,
        int(usage.get("prompt_tokens") or 0),
        int(usage.get("completion_tokens") or 0),
        int(usage.get("total_tokens") or 0),
        cost,
        served,
        str(data.get("model") or settings.EMBEDDING_MODEL),
    )
