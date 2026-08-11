"""05-01-PLAN.md Task 2 — 두 정규식 인용 앵커 문법 회귀 테스트."""

from nexuswiki_core.citations import (
    BROAD_ANCHOR_PATTERN,
    ISSUED_ANCHOR_PATTERN,
    strip_forged_anchors,
)


def test_issued_pattern_matches_the_exact_alias_shape_this_server_issues() -> None:
    assert ISSUED_ANCHOR_PATTERN.search("본문 [[wiki:w1]] 끝")
    assert ISSUED_ANCHOR_PATTERN.search("본문 [[src:s12]] 끝")


def test_issued_pattern_rejects_a_real_slug_or_id_instead_of_an_alias() -> None:
    assert ISSUED_ANCHOR_PATTERN.search("[[wiki:homepage]]") is None
    assert ISSUED_ANCHOR_PATTERN.search("[[src:not-a-real-id]]") is None


def test_broad_pattern_matches_both_issued_aliases_and_forged_shapes() -> None:
    assert BROAD_ANCHOR_PATTERN.search("[[wiki:w1]]")
    assert BROAD_ANCHOR_PATTERN.search("[[src:s12]]")
    assert BROAD_ANCHOR_PATTERN.search("[[wiki:homepage]]")
    assert BROAD_ANCHOR_PATTERN.search("[[src:not-a-real-id]]")


def test_strip_forged_anchors_removes_anything_broad_shaped() -> None:
    text = "이것은 [[wiki:homepage]] 그리고 [[src:not-a-real-id]] 그리고 [[wiki:w1]]입니다."

    stripped = strip_forged_anchors(text)

    assert "[[wiki:homepage]]" not in stripped
    assert "[[src:not-a-real-id]]" not in stripped
    assert "[[wiki:w1]]" not in stripped


def test_strip_forged_anchors_leaves_ordinary_text_untouched() -> None:
    text = "인용 표기가 전혀 없는 평범한 문단입니다."

    assert strip_forged_anchors(text) == text
