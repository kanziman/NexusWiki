from dataclasses import FrozenInstanceError

import pytest

from nexuswiki_core.retrieval_policy import (
    DEFAULT_RETRIEVAL_POLICY,
    POLICY_VERSION,
    RetrievalPolicy,
)


def test_default_policy_is_immutable_and_starts_all_first_wave_channels_equally() -> None:
    policy = DEFAULT_RETRIEVAL_POLICY

    assert POLICY_VERSION == policy.version
    assert set(policy.channel_weights) == {
        "wiki_vector",
        "source_vector",
        "wiki_lexical",
        "source_lexical",
    }
    assert set(policy.channel_weights.values()) == {1.0}
    with pytest.raises(FrozenInstanceError):
        policy.rrf_k = 10  # type: ignore[misc]


@pytest.mark.parametrize("requested_k", [0, -1])
def test_policy_rejects_nonpositive_requested_k(requested_k: int) -> None:
    with pytest.raises(ValueError, match="requested_k"):
        RetrievalPolicy(requested_k=requested_k)


@pytest.mark.parametrize("overfetch", [0, -1])
def test_policy_rejects_nonpositive_channel_overfetch(overfetch: int) -> None:
    with pytest.raises(ValueError, match="overfetch"):
        RetrievalPolicy(channel_overfetch={"source_vector": overfetch})


def test_policy_has_versioned_separate_limits_and_graph_defaults_off() -> None:
    policy = DEFAULT_RETRIEVAL_POLICY

    assert policy.requested_k > 0
    assert policy.channel_overfetch
    assert policy.graph_enabled is False
    assert policy.graph_depth == 2
    assert policy.graph_fanout == 5
    assert policy.graph_total_limit == 50
