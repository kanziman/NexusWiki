"""CITE-05 citation-resolution metrics."""

from api.services.ask import resolve_citations


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
