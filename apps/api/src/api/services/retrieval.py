"""Evidence-only retrieval tracer using requester-JWT RPCs."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID

import httpx

from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY, RetrievalPolicy
from nexuswiki_core.rrf import EvidenceHit, fuse_ranked_hits
from nexuswiki_core.tokenizer import bigram, normalize


class QueryEmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class RpcUserDb(Protocol):
    async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]: ...


class HttpQueryEmbeddingClient:
    """The API's only embedding capability: an authenticated private worker call."""

    def __init__(
        self,
        client: httpx.AsyncClient,
        *,
        url: str | None,
        token: str | None,
        timeout_seconds: float,
    ) -> None:
        self._client = client
        self._url = url
        self._token = token
        self._timeout_seconds = timeout_seconds

    async def embed(self, text: str) -> list[float]:
        if not self._url or not self._token:
            raise RuntimeError("query_embedding_unavailable")
        response = await self._client.post(
            f"{self._url.rstrip('/')}/internal/query-embedding",
            json={"text": text},
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=self._timeout_seconds,
        )
        if response.is_error:
            raise RuntimeError("query_embedding_unavailable")
        payload = response.json()
        vector = payload.get("vector") if isinstance(payload, dict) else None
        if (
            not isinstance(vector, list)
            or len(vector) != 1024
            or not all(isinstance(v, (int, float)) for v in vector)
        ):
            raise RuntimeError("query_embedding_unavailable")
        return [float(value) for value in vector]


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    evidence: list[EvidenceHit]
    meta: dict[str, Any]


class RetrievalService:
    """First tracer: source vector plus source lexical evidence only."""

    def __init__(
        self,
        embedding_client: QueryEmbeddingClient,
        *,
        policy: RetrievalPolicy = DEFAULT_RETRIEVAL_POLICY,
    ) -> None:
        self._embedding_client = embedding_client
        self._policy = policy

    async def retrieve(
        self, workspace_id: UUID, query: str, requested_k: int, user_db: RpcUserDb
    ) -> RetrievalResult:
        if not query or len(query) > 10_000:
            raise ValueError("invalid_query")
        if requested_k <= 0 or requested_k > self._policy.requested_k:
            raise ValueError("invalid_requested_k")
        started = time.perf_counter()
        normalized = normalize(query)
        query_bigrams = bigram(normalized)
        candidate_limit = min(
            self._policy.overfetch["source_vector"], self._policy.vector_sql_max_candidates
        )
        lexical_limit = min(
            self._policy.overfetch["source_lexical"], self._policy.lexical_sql_max_candidates
        )
        meta: dict[str, dict[str, Any]] = {}
        channel_hits: dict[str, list[EvidenceHit]] = {}

        try:
            vector = await self._embedding_client.embed(normalized)
        except asyncio.CancelledError:
            raise
        except Exception:
            meta["source_vector"] = _failed_meta(candidate_limit, "embedding_unavailable")
        else:
            hits, envelope = await self._source_vector(
                user_db, workspace_id, vector, candidate_limit
            )
            meta["source_vector"] = envelope
            if hits:
                channel_hits["source_vector"] = hits

        hits, envelope = await self._source_lexical(
            user_db, workspace_id, query_bigrams, lexical_limit
        )
        meta["source_lexical"] = envelope
        if hits:
            channel_hits["source_lexical"] = hits

        evidence = fuse_ranked_hits(channel_hits, policy=self._policy)[:requested_k]
        elapsed_ms = round((time.perf_counter() - started) * 1000, 3)
        return RetrievalResult(
            evidence=evidence,
            meta={
                "policy_version": self._policy.version,
                "requested_k": requested_k,
                "returned": len(evidence),
                "underfill": len(evidence) < requested_k,
                "elapsed_ms": elapsed_ms,
                **meta,
            },
        )

    async def _source_vector(
        self, db: RpcUserDb, workspace_id: UUID, vector: list[float], limit: int
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        return await _rpc_channel(
            db,
            "search_chunks",
            {"p_workspace_id": str(workspace_id), "p_query": vector, "p_k": limit},
            limit,
        )

    async def _source_lexical(
        self, db: RpcUserDb, workspace_id: UUID, query_bigrams: str, limit: int
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        return await _rpc_channel(
            db,
            "search_source_lexical",
            {"p_workspace_id": str(workspace_id), "p_bigrams": query_bigrams, "p_k": limit},
            limit,
        )


async def _rpc_channel(
    db: RpcUserDb, function: str, params: dict[str, object], requested: int
) -> tuple[list[EvidenceHit], dict[str, Any]]:
    started = time.perf_counter()
    try:
        rows = await db.rpc(function, params=params)
        if not isinstance(rows, list):
            raise ValueError("malformed")
        hits = [_source_hit(row, rank=index) for index, row in enumerate(rows, start=1)]
    except asyncio.CancelledError:
        raise
    except Exception:
        return [], _failed_meta(requested, "rpc_unavailable", started)
    return hits, {
        "status": "ok",
        "requested": requested,
        "returned": len(hits),
        "underfill": len(hits) < requested,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "error_code": None,
    }


def _source_hit(row: dict[str, object], *, rank: int) -> EvidenceHit:
    chunk_id = row.get("id")
    if not isinstance(chunk_id, str):
        raise ValueError("malformed")
    safe_metadata = {key: row[key] for key in ("raw_source_id", "chunk_index") if key in row}
    return EvidenceHit.source(chunk_id=chunk_id, rank=rank, metadata=safe_metadata)


def _failed_meta(requested: int, error_code: str, started: float | None = None) -> dict[str, Any]:
    elapsed = 0.0 if started is None else round((time.perf_counter() - started) * 1000, 3)
    return {
        "status": "failed",
        "requested": requested,
        "returned": 0,
        "underfill": True,
        "elapsed_ms": elapsed,
        "error_code": error_code,
    }
