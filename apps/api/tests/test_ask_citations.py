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
