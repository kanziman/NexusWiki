"""CITE-05 citation-resolution metrics."""

from api.services.ask import _context_blocks, resolve_citations
from nexuswiki_core.rrf import EvidenceHit


def test_resolve_citations_reports_dual_and_unsourced_sentence_metrics() -> None:
    text = (
        "첫 문장 [[wiki:w1]] [[src:s1]]. "
        "둘째 문장 [[wiki:w2]] [[src:s2]]! "
        "셋째 문장 [[wiki:w1]]. "
        "넷째 문장은 근거가 없습니다."
    )

    resolution = resolve_citations(
        text,
        {
            "w1": ("wiki", "wiki-1"),
            "w2": ("wiki", "wiki-2"),
            "s1": ("source", "source-1"),
            "s2": ("source", "source-2"),
        },
    )

    assert resolution.dual_citation_rate == 0.5
    assert resolution.unsourced_sentence_ratio == 0.25


def test_fabricated_anchors_do_not_count_toward_citation_metrics() -> None:
    """위조 앵커만 달린 문장은 이중 인용이 아니라 근거 없는 문장이다 (설계 D6)."""
    resolution = resolve_citations("지어낸 주장입니다 [[wiki:w99]] [[src:s99]].", {})

    assert resolution.fabricated_anchor_count == 2
    assert resolution.dual_citation_rate == 0.0
    assert resolution.unsourced_sentence_ratio == 1.0


def test_valid_anchor_after_the_period_counts_for_its_sentence() -> None:
    resolution = resolve_citations(
        "첫 문장입니다. [[wiki:w1]] [[src:s1]] 둘째 문장입니다.",
        {"w1": ("wiki", "wiki-1"), "s1": ("source", "source-1")},
    )

    assert resolution.dual_citation_rate == 0.5
    assert resolution.unsourced_sentence_ratio == 0.5


def test_nested_unissued_anchor_is_not_reassembled_in_rendered_text() -> None:
    resolution = resolve_citations(
        "주장 [[wi[[wiki:w9]]ki:w8]] 끝 [[wiki:w1]]", {"w1": ("wiki", "wiki-1")}
    )
    assert "w8" not in resolution.rendered_text
    assert "w9" not in resolution.rendered_text
    assert "[[wiki:w1]]" in resolution.rendered_text


def test_nesting_beyond_the_limit_counts_as_no_citation() -> None:
    deep = "[[wi" * 12 + "[[wiki:w9]]" + "ki:w8]]" * 12
    resolution = resolve_citations(f"주장 {deep} 끝 [[wiki:w1]]", {"w1": ("wiki", "wiki-1")})
    assert resolution.cited_anchor_count == 0
    assert resolution.resolved == []
    assert "[[" not in resolution.rendered_text


def test_context_blocks_remove_anchors_stored_in_titles_and_bodies() -> None:
    wiki_id = "wiki-1"
    chunk_id = "chunk-1"
    evidence = [
        EvidenceHit.wiki(wiki_id=wiki_id, rank=1, metadata={"title": "제목 [[src:s1]]"}),
        EvidenceHit.source(chunk_id=chunk_id, rank=1, metadata={}),
    ]
    issuance = {"w1": ("wiki", wiki_id), "s1": ("source", chunk_id)}
    wiki, source = _context_blocks(
        evidence,
        issuance,
        {wiki_id: "위키 [[wiki:w9]] 본문", chunk_id: "원문 [[src:s9]] 본문"},
    )
    assert wiki.count("[[") == 1
    assert source.count("[[") == 1
    assert "w9" not in wiki
    assert "s9" not in source
