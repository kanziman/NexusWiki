"""Versioned, immutable retrieval tuning policy.

This module owns retrieval tuning rather than SQL so every result and benchmark
can identify the exact policy that made its ordering decision.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final

POLICY_VERSION: Final[str] = "hybrid-rrf-v1"
_FIRST_WAVE_CHANNELS: Final[tuple[str, ...]] = (
    "wiki_vector",
    "source_vector",
    "wiki_lexical",
    "source_lexical",
)


@dataclass(frozen=True, slots=True)
class RetrievalPolicy:
    """All retrieval limits and weights, frozen and stamped with a version."""

    version: str = POLICY_VERSION
    rrf_k: int = 60
    channel_weights: Mapping[str, float] = field(
        default_factory=lambda: MappingProxyType(dict.fromkeys(_FIRST_WAVE_CHANNELS, 1.0))
    )
    channel_overfetch: Mapping[str, int] = field(
        default_factory=lambda: MappingProxyType(dict.fromkeys(_FIRST_WAVE_CHANNELS, 20))
    )
    requested_k: int = 8
    vector_sql_max_candidates: int = 100
    lexical_sql_max_candidates: int = 100
    graph_enabled: bool = False
    graph_weight: float = 1.0
    graph_seed_limit: int = 10
    graph_depth: int = 2
    graph_fanout: int = 5
    graph_total_limit: int = 50

    def __post_init__(self) -> None:
        object.__setattr__(self, "channel_weights", MappingProxyType(dict(self.channel_weights)))
        object.__setattr__(
            self, "channel_overfetch", MappingProxyType(dict(self.channel_overfetch))
        )
        if not self.version:
            raise ValueError("version must be non-empty")
        if self.rrf_k < 0:
            raise ValueError("rrf_k must be non-negative")
        if self.requested_k <= 0:
            raise ValueError("requested_k must be positive")
        if self.vector_sql_max_candidates <= 0 or self.lexical_sql_max_candidates <= 0:
            raise ValueError("SQL candidate maxima must be positive")
        if any(limit <= 0 for limit in self.channel_overfetch.values()):
            raise ValueError("channel overfetch must be positive")
        if any(weight <= 0 for weight in self.channel_weights.values()):
            raise ValueError("channel weights must be positive")
        if (
            self.graph_seed_limit <= 0
            or self.graph_depth <= 0
            or self.graph_fanout <= 0
            or self.graph_total_limit <= 0
        ):
            raise ValueError("graph limits must be positive")

    @property
    def weights(self) -> Mapping[str, float]:
        return self.channel_weights

    @property
    def overfetch(self) -> Mapping[str, int]:
        return self.channel_overfetch


DEFAULT_RETRIEVAL_POLICY: Final[RetrievalPolicy] = RetrievalPolicy()
