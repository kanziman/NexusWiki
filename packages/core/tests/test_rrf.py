from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY
from nexuswiki_core.rrf import EvidenceHit, fuse_ranked_hits


def _source(chunk_id: str, *, rank: int, distance: float = 0.0) -> EvidenceHit:
    return EvidenceHit.source(chunk_id=chunk_id, rank=rank, metadata={"distance": distance})


def test_rrf_uses_one_based_rank_formula_and_accumulates_contributions() -> None:
    fused = fuse_ranked_hits(
        {
            "source_vector": [_source("chunk-a", rank=1)],
            "source_lexical": [_source("chunk-a", rank=2)],
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )

    hit = fused[0]
    assert hit.canonical_id == "source:chunk-a"
    assert hit.channels == ("source_lexical", "source_vector")
    assert hit.contributions == {
        "source_vector": 1 / (DEFAULT_RETRIEVAL_POLICY.rrf_k + 1),
        "source_lexical": 1 / (DEFAULT_RETRIEVAL_POLICY.rrf_k + 2),
    }
    assert hit.rrf_score == sum(hit.contributions.values())


def test_rrf_dedupes_wiki_by_page_and_keeps_selected_embedding_chunk() -> None:
    fused = fuse_ranked_hits(
        {
            "wiki_vector": [
                EvidenceHit.wiki(wiki_id="wiki-a", rank=1, embedding_chunk_id="chunk-1"),
                EvidenceHit.wiki(wiki_id="wiki-a", rank=2, embedding_chunk_id="chunk-2"),
            ]
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )

    assert len(fused) == 1
    assert fused[0].canonical_id == "wiki:wiki-a"
    assert fused[0].metadata["embedding_chunk_id"] == "chunk-1"


def test_raw_distance_cannot_change_rank_only_fusion_order() -> None:
    first = fuse_ranked_hits(
        {
            "source_vector": [
                _source("a", rank=1, distance=0.99),
                _source("b", rank=2, distance=0.01),
            ]
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )
    second = fuse_ranked_hits(
        {
            "source_vector": [
                _source("a", rank=1, distance=0.01),
                _source("b", rank=2, distance=0.99),
            ]
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )

    assert [hit.canonical_id for hit in first] == [hit.canonical_id for hit in second]


def test_rrf_breaks_equal_scores_by_canonical_id() -> None:
    fused = fuse_ranked_hits(
        {"source_vector": [_source("z", rank=1), _source("a", rank=1)]},
        policy=DEFAULT_RETRIEVAL_POLICY,
    )

    assert [hit.canonical_id for hit in fused] == ["source:a", "source:z"]


def test_rrf_merges_channel_metadata_without_overwriting_first_hit_keys() -> None:
    fused = fuse_ranked_hits(
        {
            "wiki_vector": [
                EvidenceHit.wiki(
                    wiki_id="wiki-a",
                    rank=1,
                    embedding_chunk_id="chunk-1",
                    metadata={"chunk_index": 0},
                )
            ],
            "wiki_lexical": [
                EvidenceHit.wiki(
                    wiki_id="wiki-a",
                    rank=2,
                    embedding_chunk_id="chunk-2",
                    metadata={"slug": "overview", "title": "개요 문서", "chunk_index": 99},
                )
            ],
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )

    assert len(fused) == 1
    assert fused[0].metadata["embedding_chunk_id"] == "chunk-1"
    assert fused[0].metadata["chunk_index"] == 0
    assert fused[0].metadata["slug"] == "overview"
    assert fused[0].metadata["title"] == "개요 문서"


# --- #195 B: 같은 채널 안 반복은 최고 순위로 한 번만 기여한다 --------------------------------


def _wiki_chunk(rank: int, chunk: str, wiki_id: str = "wiki-a") -> EvidenceHit:
    return EvidenceHit.wiki(wiki_id=wiki_id, rank=rank, embedding_chunk_id=chunk)


def test_repeated_wiki_chunks_in_one_channel_count_once_at_best_rank() -> None:
    fused = fuse_ranked_hits(
        {"wiki_vector": [_wiki_chunk(1, "c1"), _wiki_chunk(2, "c2"), _wiki_chunk(3, "c3")]},
        policy=DEFAULT_RETRIEVAL_POLICY,
    )
    k = DEFAULT_RETRIEVAL_POLICY.rrf_k
    assert fused[0].contributions == {"wiki_vector": 1 / (k + 1)}
    assert fused[0].rrf_score == 1 / (k + 1)


def test_same_evidence_in_different_channels_is_summed() -> None:
    fused = fuse_ranked_hits(
        {
            "wiki_vector": [_wiki_chunk(1, "c1"), _wiki_chunk(2, "c2")],
            "wiki_lexical": [_wiki_chunk(3, "c9")],
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )
    k = DEFAULT_RETRIEVAL_POLICY.rrf_k
    assert fused[0].rrf_score == 1 / (k + 1) + 1 / (k + 3)


def test_best_rank_does_not_depend_on_input_order() -> None:
    fused = fuse_ranked_hits(
        {"wiki_vector": [_wiki_chunk(3, "c3"), _wiki_chunk(1, "c1")]},
        policy=DEFAULT_RETRIEVAL_POLICY,
    )
    assert fused[0].contributions == {"wiki_vector": 1 / (DEFAULT_RETRIEVAL_POLICY.rrf_k + 1)}


def test_single_chunk_source_is_no_longer_outranked_by_repetition_alone() -> None:
    """v1에서는 2·3위 위키 청크 둘의 합(1/62+1/63)이 1위 원문(1/61)보다 컸다."""
    fused = fuse_ranked_hits(
        {
            "wiki_vector": [_wiki_chunk(2, "c2"), _wiki_chunk(3, "c3")],
            "source_vector": [_source("chunk-s", rank=1)],
        },
        policy=DEFAULT_RETRIEVAL_POLICY,
    )
    assert fused[0].canonical_id == "source:chunk-s"


def test_sum_policy_reproduces_v1_behaviour() -> None:
    from dataclasses import replace

    v1 = replace(DEFAULT_RETRIEVAL_POLICY, same_channel_aggregation="sum")
    fused = fuse_ranked_hits(
        {
            "wiki_vector": [_wiki_chunk(2, "c2"), _wiki_chunk(3, "c3")],
            "source_vector": [_source("chunk-s", rank=1)],
        },
        policy=v1,
    )
    k = v1.rrf_k
    assert fused[0].canonical_id == "wiki:wiki-a"
    assert fused[0].rrf_score == 1 / (k + 2) + 1 / (k + 3)


def test_policy_rejects_unknown_aggregation() -> None:
    import pytest

    from nexuswiki_core.retrieval_policy import RetrievalPolicy

    with pytest.raises(ValueError):
        RetrievalPolicy(same_channel_aggregation="mean")
