"""Ask 컨텍스트 토큰 예산 할당기 및 이중 근거 쿼터 회귀 테스트."""

from nexuswiki_core.chunking import count_tokens
from nexuswiki_core.context_budget import allocate_ask_context_budget, truncate_text_to_tokens
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
