"""Pure rank-only reciprocal-rank fusion for retrieval evidence."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Any

from nexuswiki_core.retrieval_policy import RetrievalPolicy


@dataclass(frozen=True, slots=True)
class EvidenceHit:
    """One channel's evidence candidate; ranks are intentionally 1-based."""

    kind: str
    evidence_id: str
    document_id: str
    rank: int
    metadata: Mapping[str, Any] = field(default_factory=dict)
    channels: tuple[str, ...] = ()
    contributions: Mapping[str, float] = field(default_factory=dict)
    rrf_score: float = 0.0

    def __post_init__(self) -> None:
        if self.kind not in {"wiki", "source"}:
            raise ValueError("kind must be wiki or source")
        if self.rank <= 0:
            raise ValueError("rank must be 1-based and positive")
        object.__setattr__(self, "metadata", MappingProxyType(dict(self.metadata)))
        object.__setattr__(self, "contributions", MappingProxyType(dict(self.contributions)))

    @property
    def canonical_id(self) -> str:
        return f"{self.kind}:{self.document_id if self.kind == 'wiki' else self.evidence_id}"

    @classmethod
    def source(
        cls, *, chunk_id: str, rank: int, metadata: Mapping[str, Any] | None = None
    ) -> EvidenceHit:
        return cls(
            kind="source",
            evidence_id=chunk_id,
            document_id=chunk_id,
            rank=rank,
            metadata=metadata or {},
        )

    @classmethod
    def wiki(
        cls,
        *,
        wiki_id: str,
        rank: int,
        embedding_chunk_id: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> EvidenceHit:
        values = dict(metadata or {})
        if embedding_chunk_id is not None:
            values["embedding_chunk_id"] = embedding_chunk_id
        return cls(
            kind="wiki",
            evidence_id=embedding_chunk_id or wiki_id,
            document_id=wiki_id,
            rank=rank,
            metadata=values,
        )


@dataclass(frozen=True, slots=True)
class ChannelMeta:
    status: str
    requested: int
    returned: int
    elapsed_ms: float
    error_code: str | None = None

    @property
    def underfill(self) -> bool:
        return self.returned < self.requested


def fuse_ranked_hits(
    channel_hits: Mapping[str, Sequence[EvidenceHit]], *, policy: RetrievalPolicy
) -> list[EvidenceHit]:
    """Fuse channel-ranked evidence using only rank, policy weight, and canonical ID."""
    combined: dict[str, EvidenceHit] = {}
    contribution_maps: dict[str, dict[str, float]] = {}
    for channel, hits in channel_hits.items():
        weight = policy.weights.get(channel)
        if weight is None:
            continue
        for hit in hits:
            contribution = weight / (policy.rrf_k + hit.rank)
            canonical_id = hit.canonical_id
            previous = combined.get(canonical_id)
            if previous is None:
                combined[canonical_id] = hit
                contribution_maps[canonical_id] = {channel: contribution}
            else:
                contribution_maps[canonical_id][channel] = (
                    contribution_maps[canonical_id].get(channel, 0.0) + contribution
                )

    fused = []
    for canonical_id, hit in combined.items():
        contributions = contribution_maps[canonical_id]
        fused.append(
            replace(
                hit,
                channels=tuple(sorted(contributions)),
                contributions=contributions,
                rrf_score=sum(contributions.values()),
            )
        )
    return sorted(fused, key=lambda hit: (-hit.rrf_score, hit.canonical_id))
