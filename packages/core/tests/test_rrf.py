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
