"""CITE-05 sentence-boundary regression coverage."""

from nexuswiki_core.sentences import split_sentences


def test_split_sentences_handles_mixed_korean_english_and_full_width_boundaries() -> None:
    assert split_sentences("첫 문장입니다. English question? 마지막입니다！ 끝。") == [
        "첫 문장입니다",
        "English question",
        "마지막입니다",
        "끝",
    ]


def test_split_sentences_does_not_split_decimals_or_numbered_list_markers() -> None:
    assert split_sentences("값은 3.14입니다. 1. 첫 항목입니다!   ") == [
        "값은 3.14입니다",
        "1. 첫 항목입니다",
    ]


def test_split_sentences_drops_empty_and_whitespace_only_pieces() -> None:
    assert split_sentences("  ...   !?  문장.   ") == ["문장"]


def test_split_sentences_keeps_anchor_after_period_with_its_sentence() -> None:
    """ai-control-flow-accounting D6: 마침표 뒤 앵커가 다음 문장의 근거로 넘어가지 않는다."""
    assert split_sentences("첫 문장입니다. [[wiki:w1]] [[src:s1]] 둘째 문장입니다.") == [
        "첫 문장입니다 [[wiki:w1]] [[src:s1]]",
        "둘째 문장입니다",
    ]


def test_split_sentences_splits_when_anchor_touches_the_period() -> None:
    assert split_sentences("첫 문장입니다.[[src:s1]] 둘째 문장입니다.[[wiki:w1]]") == [
        "첫 문장입니다 [[src:s1]]",
        "둘째 문장입니다 [[wiki:w1]]",
    ]


def test_split_sentences_keeps_leading_anchor_when_no_previous_sentence_exists() -> None:
    assert split_sentences("[[wiki:w1]] 문장입니다.") == ["[[wiki:w1]] 문장입니다"]
