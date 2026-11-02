"""Ask 컨텍스트 토큰 예산 할당기 및 이중 근거 쿼터 회귀 테스트."""

from nexuswiki_core.chunking import count_tokens
from nexuswiki_core.context_budget import (
    allocate_ask_context_budget,
    select_dual_evidence,
    truncate_text_to_tokens,
)
from nexuswiki_core.rrf import EvidenceHit


def test_allocate_ask_context_budget_preserves_dual_evidence_under_tight_budget() -> None:
    """상위 위키가 토큰 예산을 넘겨도 최상위 wiki 1개와 최상위 source 1개는 반드시 유지된다."""
    hits = [
        EvidenceHit.wiki(wiki_id="w-1", rank=1, metadata={"title": "위키 1"}),
        EvidenceHit.wiki(wiki_id="w-2", rank=2, metadata={"title": "위키 2"}),
        EvidenceHit.wiki(wiki_id="w-3", rank=3, metadata={"title": "위키 3"}),
        EvidenceHit.source(
            chunk_id="s-1", rank=4, metadata={"raw_source_id": "rs-1", "chunk_index": 0}
        ),
    ]
    long_text = "한국어 위키 본문 문장입니다. " * 120
    source_text = "원문 청크 근거 문장입니다. " * 80
    content_by_id = {
        "w-1": long_text,
        "w-2": long_text,
        "w-3": long_text,
        "s-1": source_text,
    }

    result = allocate_ask_context_budget(hits, content_by_id, max_context_tokens=200)

    assert result.estimated_context_tokens <= 200
    assert result.dual_evidence_preserved is True
    assert result.wiki_blocks >= 1
    assert result.source_blocks >= 1
    assert result.truncated is True
    assert result.dropped_blocks >= 2
    included_ids = [hit.canonical_id for hit in result.included_evidence]
    assert "wiki:w-1" in included_ids
    assert "source:s-1" in included_ids
    # RRF 상대 순서가 유지되어야 별칭(w1, s1) 부여 순서가 흔들리지 않는다.
    assert included_ids.index("wiki:w-1") < included_ids.index("source:s-1")


def test_allocate_ask_context_budget_keeps_all_blocks_when_within_budget() -> None:
    hits = [
        EvidenceHit.wiki(wiki_id="w-1", rank=1, metadata={"title": "위키 1"}),
        EvidenceHit.source(
            chunk_id="s-1", rank=2, metadata={"raw_source_id": "rs-1", "chunk_index": 0}
        ),
    ]
    content_by_id = {"w-1": "짧은 위키 본문", "s-1": "짧은 원문 본문"}

    result = allocate_ask_context_budget(hits, content_by_id, max_context_tokens=6000)

    assert result.truncated is False
    assert result.included_blocks == 2
    assert result.dropped_blocks == 0
    assert result.truncated_blocks == 0
    assert result.dual_evidence_preserved is True


def test_truncate_text_to_tokens_respects_token_cap() -> None:
    text = "토큰 예산 절단 테스트 문장입니다. " * 50
    clipped, was_clipped = truncate_text_to_tokens(text, 30)

    assert was_clipped is True
    assert count_tokens(clipped) <= 30


def _wiki_hit(index: int) -> EvidenceHit:
    return EvidenceHit.wiki(wiki_id=f"wiki-{index}", rank=index, metadata={})


def _source_hit(index: int, raw_source_id: str = "raw") -> EvidenceHit:
    return EvidenceHit.source(
        chunk_id=f"chunk-{index}",
        rank=index,
        metadata={"raw_source_id": raw_source_id, "chunk_index": index},
    )


def test_selection_keeps_sources_when_wiki_dominates_the_top() -> None:
    # 실제 재생에서 나온 형태: 위키 8쪽이 상위를 독차지하고 원문은 그 뒤에 있다.
    candidates = [
        *[_wiki_hit(i) for i in range(1, 9)],
        *[_source_hit(i, f"raw-{i}") for i in range(1, 9)],
    ]
    selected = select_dual_evidence(candidates, requested_k=8)
    assert [hit.kind for hit in selected] == ["wiki"] * 4 + ["source"] * 4
    assert [hit.evidence_id for hit in selected if hit.kind == "source"] == [
        "chunk-1",
        "chunk-2",
        "chunk-3",
        "chunk-4",
    ]


def test_selection_fills_empty_slots_with_the_other_kind() -> None:
    assert [
        h.kind for h in select_dual_evidence([_wiki_hit(i) for i in range(1, 9)], requested_k=8)
    ] == ["wiki"] * 8
    candidates = [_wiki_hit(1), *[_source_hit(i, f"raw-{i}") for i in range(1, 9)]]
    selected = select_dual_evidence(candidates, requested_k=8)
    assert len(selected) == 8
    assert [hit.kind for hit in selected].count("wiki") == 1


def test_selection_limits_one_source_but_fills_when_nothing_else_exists() -> None:
    candidates = [
        *[_wiki_hit(i) for i in range(1, 5)],
        *[_source_hit(i, "same") for i in range(1, 6)],
        _source_hit(9, "other"),
    ]
    selected = select_dual_evidence(candidates, requested_k=8)
    sources = [hit.evidence_id for hit in selected if hit.kind == "source"]
    assert sources == ["chunk-1", "chunk-2", "chunk-3", "chunk-9"]

    only_same = [_source_hit(i, "same") for i in range(1, 9)]
    assert len(select_dual_evidence(only_same, requested_k=8)) == 8


def test_selection_keeps_rrf_order_and_handles_short_input() -> None:
    candidates = [_source_hit(1), _wiki_hit(1), _source_hit(2), _wiki_hit(2)]
    assert select_dual_evidence(candidates, requested_k=8) == candidates
    assert select_dual_evidence([], requested_k=8) == []
