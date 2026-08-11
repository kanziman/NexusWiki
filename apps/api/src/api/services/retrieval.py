"""Evidence-only, failure-tolerant hybrid retrieval using requester-JWT RPCs."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from typing import Any, Protocol
from uuid import UUID

import httpx

from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY, RetrievalPolicy
from nexuswiki_core.rrf import EvidenceHit, fuse_ranked_hits
from nexuswiki_core.tokenizer import TSV_TOKENIZER_VERSION, bigram, normalize


class QueryEmbeddingClient(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class RpcUserDb(Protocol):
    async def rpc(
        self, function: str, *, params: Mapping[str, object]
    ) -> list[dict[str, object]]: ...


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
        self._client, self._url, self._token, self._timeout_seconds = (
            client,
            url,
            token,
            timeout_seconds,
        )

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
        if not _valid_vector(vector):
            raise RuntimeError("query_embedding_unavailable")
        return [float(value) for value in vector]


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    evidence: list[EvidenceHit]
    meta: dict[str, Any]


class RetrievalService:
    """Four concurrent first-wave channels followed by optional bounded graph re-fusion."""

    def __init__(
        self,
        embedding_client: QueryEmbeddingClient,
        *,
        policy: RetrievalPolicy = DEFAULT_RETRIEVAL_POLICY,
    ) -> None:
        self._embedding_client, self._policy = embedding_client, policy

    async def retrieve(
        self, workspace_id: UUID, query: str, requested_k: int, user_db: RpcUserDb
    ) -> RetrievalResult:
        if (
            not query
            or len(query) > 10_000
            or requested_k <= 0
            or requested_k > self._policy.requested_k
        ):
            raise ValueError("invalid_query")
        started = time.perf_counter()
        normalized, query_bigrams = normalize(query), bigram(normalize(query))
        limits = {
            name: min(self._policy.overfetch[name], self._sql_max(name))
            for name in self._policy.overfetch
        }
        meta: dict[str, dict[str, Any]] = {}
        channel_hits: dict[str, list[EvidenceHit]] = {}

        try:
            vector = await self._embedding_client.embed(normalized)
            if not _valid_vector(vector):
                raise ValueError("invalid_vector")
        except asyncio.CancelledError:
            raise
        except Exception:
            for name in ("wiki_vector", "source_vector"):
                meta[name] = _failed_meta(limits[name], "embedding_unavailable")
            coroutines: dict[str, Awaitable[tuple[list[EvidenceHit], dict[str, Any]]]] = {
                "wiki_lexical": self._wiki_lexical(
                    user_db, workspace_id, query_bigrams, limits["wiki_lexical"]
                ),
                "source_lexical": self._source_lexical(
                    user_db, workspace_id, query_bigrams, limits["source_lexical"]
                ),
            }
        else:
            coroutines = {
                "wiki_vector": self._wiki_vector(
                    user_db, workspace_id, vector, limits["wiki_vector"]
                ),
                "source_vector": self._source_vector(
                    user_db, workspace_id, vector, limits["source_vector"]
                ),
                "wiki_lexical": self._wiki_lexical(
                    user_db, workspace_id, query_bigrams, limits["wiki_lexical"]
                ),
                "source_lexical": self._source_lexical(
                    user_db, workspace_id, query_bigrams, limits["source_lexical"]
                ),
            }

        outcomes = await asyncio.gather(*coroutines.values(), return_exceptions=True)
        for name, outcome in zip(coroutines, outcomes, strict=True):
            if isinstance(outcome, asyncio.CancelledError):
                raise outcome
            if isinstance(outcome, BaseException):
                meta[name] = _failed_meta(limits[name], "rpc_unavailable")
                continue
            hits, envelope = outcome
            meta[name] = envelope
            if hits:
                channel_hits[name] = hits

        first_wave = fuse_ranked_hits(channel_hits, policy=self._policy)
        _set_contributions(meta, first_wave)
        evidence = first_wave
        if self._policy.graph_enabled:
            graph_hits, graph_meta = await self._graph(user_db, workspace_id, first_wave)
            meta["graph"] = graph_meta
            if graph_hits:
                evidence = fuse_ranked_hits(
                    {**channel_hits, "graph": graph_hits}, policy=self._graph_policy()
                )
                _set_contributions(meta, evidence)
        else:
            meta["graph"] = _disabled_meta(self._policy.graph_total_limit)

        evidence = evidence[:requested_k]
        return RetrievalResult(
            evidence=evidence,
            meta={
                "policy_version": self._policy.version,
                "requested_k": requested_k,
                "returned": len(evidence),
                "underfill": len(evidence) < requested_k,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                **meta,
            },
        )

    def _sql_max(self, name: str) -> int:
        return (
            self._policy.vector_sql_max_candidates
            if name.endswith("vector")
            else self._policy.lexical_sql_max_candidates
        )

    def _graph_policy(self) -> RetrievalPolicy:
        return replace(
            self._policy,
            channel_weights={**self._policy.weights, "graph": self._policy.graph_weight},
        )

    async def _source_vector(
        self, db: RpcUserDb, workspace_id: UUID, vector: list[float], limit: int
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        return await _rpc_channel(
            db,
            "search_chunks",
            {"p_workspace_id": str(workspace_id), "p_query": vector, "p_k": limit},
            limit,
            _source_hit,
        )

    async def _wiki_vector(
        self, db: RpcUserDb, workspace_id: UUID, vector: list[float], limit: int
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        return await _rpc_channel(
            db,
            "search_wiki_embeddings",
            {"p_workspace_id": str(workspace_id), "p_query": vector, "p_k": limit},
            limit,
            _wiki_vector_hit,
        )

    async def _source_lexical(
        self, db: RpcUserDb, workspace_id: UUID, bigrams: str, limit: int
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        return await _rpc_channel(
            db,
            "search_source_lexical",
            _lexical_params(workspace_id, bigrams, limit),
            limit,
            _source_hit,
        )

    async def _wiki_lexical(
        self, db: RpcUserDb, workspace_id: UUID, bigrams: str, limit: int
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        return await _rpc_channel(
            db,
            "search_wiki_lexical",
            _lexical_params(workspace_id, bigrams, limit),
            limit,
            _wiki_lexical_hit,
        )

    async def _graph(
        self, db: RpcUserDb, workspace_id: UUID, first_wave: list[EvidenceHit]
    ) -> tuple[list[EvidenceHit], dict[str, Any]]:
        seeds = [hit.document_id for hit in first_wave if hit.kind == "wiki"][
            : self._policy.graph_seed_limit
        ]
        if not seeds:
            return [], _ok_graph_meta(self._policy.graph_total_limit, [], 0.0)
        started = time.perf_counter()
        try:
            rows = await db.rpc(
                "expand_wiki_graph",
                params={
                    "p_workspace_id": str(workspace_id),
                    "p_seed_wiki_ids": seeds,
                    "p_fanout": self._policy.graph_fanout,
                    "p_total_limit": self._policy.graph_total_limit,
                },
            )
            if not isinstance(rows, list):
                raise ValueError("malformed")
            seed_rank = {seed: index for index, seed in enumerate(seeds, start=1)}
            ranked = [_graph_row(row, seed_rank) for row in rows]
            ranked.sort()
            hits = [
                EvidenceHit.wiki(wiki_id=wiki_id, rank=index, metadata={"graph_depth": depth})
                for index, (_, depth, wiki_id) in enumerate(ranked, start=1)
            ]
        except asyncio.CancelledError:
            raise
        except Exception:
            return [], _failed_meta(self._policy.graph_total_limit, "rpc_unavailable", started)
        return hits, _ok_graph_meta(self._policy.graph_total_limit, hits, started)


def _lexical_params(workspace_id: UUID, bigrams: str, limit: int) -> dict[str, object]:
    return {
        "p_workspace_id": str(workspace_id),
        "p_bigrams": bigrams,
        "p_tokenizer_version": TSV_TOKENIZER_VERSION,
        "p_k": limit,
    }


async def _rpc_channel(
    db: RpcUserDb,
    function: str,
    params: Mapping[str, object],
    requested: int,
    make_hit: Callable[[Mapping[str, object], int], EvidenceHit],
) -> tuple[list[EvidenceHit], dict[str, Any]]:
    started = time.perf_counter()
    try:
        rows = await db.rpc(function, params=params)
        if not isinstance(rows, list):
            raise ValueError("malformed")
        hits = [make_hit(row, index) for index, row in enumerate(rows, start=1)]
    except asyncio.CancelledError:
        raise
    except Exception:
        return [], _failed_meta(requested, "rpc_unavailable", started)
    return hits, {
        **_ok_meta(requested, hits, started),
        "raw_hit_ids": [hit.evidence_id for hit in hits],
        "contribution": 0,
    }


def _source_hit(row: Mapping[str, object], rank: int) -> EvidenceHit:
    chunk_id = row.get("id")
    if not isinstance(chunk_id, str):
        raise ValueError("malformed")
    return EvidenceHit.source(
        chunk_id=chunk_id,
        rank=rank,
        metadata={key: row[key] for key in ("raw_source_id", "chunk_index") if key in row},
    )


def _wiki_vector_hit(row: Mapping[str, object], rank: int) -> EvidenceHit:
    wiki_id, chunk_id = row.get("wiki_id"), row.get("id")
    if not isinstance(wiki_id, str) or not isinstance(chunk_id, str):
        raise ValueError("malformed")
    return EvidenceHit.wiki(
        wiki_id=wiki_id,
        embedding_chunk_id=chunk_id,
        rank=rank,
        metadata={key: row[key] for key in ("chunk_index",) if key in row},
    )


def _wiki_lexical_hit(row: Mapping[str, object], rank: int) -> EvidenceHit:
    wiki_id = row.get("id")
    if not isinstance(wiki_id, str):
        raise ValueError("malformed")
    return EvidenceHit.wiki(
        wiki_id=wiki_id,
        rank=rank,
        metadata={key: row[key] for key in ("slug", "title") if key in row},
    )


def _graph_row(row: Mapping[str, object], seed_rank: Mapping[str, int]) -> tuple[int, int, str]:
    wiki_id, depth = row.get("wiki_id"), row.get("depth")
    if not isinstance(wiki_id, str) or not isinstance(depth, int) or not 0 <= depth <= 2:
        raise ValueError("malformed")
    return seed_rank.get(wiki_id, len(seed_rank) + 1), depth, wiki_id


def _valid_vector(vector: object) -> bool:
    return (
        isinstance(vector, list)
        and len(vector) == 1024
        and all(isinstance(value, (int, float)) for value in vector)
    )


def _ok_meta(requested: int, hits: list[EvidenceHit], started: float) -> dict[str, Any]:
    return {
        "status": "ok",
        "requested": requested,
        "returned": len(hits),
        "underfill": len(hits) < requested,
        "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
        "error_code": None,
    }


def _failed_meta(requested: int, error_code: str, started: float | None = None) -> dict[str, Any]:
    elapsed = 0.0 if started is None else round((time.perf_counter() - started) * 1000, 3)
    return {
        "status": "failed",
        "requested": requested,
        "returned": 0,
        "underfill": True,
        "elapsed_ms": elapsed,
        "error_code": error_code,
        "raw_hit_ids": [],
        "contribution": 0,
    }


def _disabled_meta(requested: int) -> dict[str, Any]:
    return {
        "status": "disabled",
        "requested": requested,
        "returned": 0,
        "underfill": True,
        "elapsed_ms": 0.0,
        "error_code": None,
        "raw_hit_ids": [],
        "contribution": 0,
    }


def _ok_graph_meta(requested: int, hits: list[EvidenceHit], started: float) -> dict[str, Any]:
    return {
        **_ok_meta(requested, hits, started),
        "raw_hit_ids": [hit.document_id for hit in hits],
        "contribution": 0,
    }


def _set_contributions(meta: Mapping[str, dict[str, Any]], evidence: list[EvidenceHit]) -> None:
    for name, channel in meta.items():
        channel["contribution"] = sum(1 for hit in evidence if name in hit.contributions)
