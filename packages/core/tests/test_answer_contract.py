"""Ask 인용 계약 판정과 Fallback (ai-control-output-contract, #190)."""

from __future__ import annotations

import time

import pytest

from nexuswiki_core.answer_contract import (
    FALLBACK_NOTICE,
    VIOLATION_FABRICATED_ANCHOR,
    VIOLATION_NO_CITATION,
    build_fallback_answer,
    check_answer_contract,
    repair_instruction,
)
from nexuswiki_core.citations import (
    BROAD_ANCHOR_PATTERN,
    ISSUED_ANCHOR_PATTERN,
    strip_forged_anchors,
)
from nexuswiki_core.rrf import EvidenceHit

_WIKI = "11111111-1111-4111-8111-111111111111"
_CHUNK = "22222222-2222-4222-8222-222222222222"
_ISSUANCE = {"w1": ("wiki", _WIKI), "s1": ("source", _CHUNK)}


def _evidence() -> list[EvidenceHit]:
    return [
        EvidenceHit.wiki(wiki_id=_WIKI, rank=1, metadata={"title": "배송 규정"}),
        EvidenceHit.source(
            chunk_id=_CHUNK, rank=1, metadata={"raw_source_id": "r", "chunk_index": 0}
        ),
    ]


def test_answer_with_issued_anchor_passes() -> None:
    assert (
        check_answer_contract("답 [[wiki:w1]]", cited_anchor_count=1, fabricated_anchor_count=0)
        == ()
    )


def test_answer_without_citation_is_a_violation() -> None:
    assert check_answer_contract(
        "그냥 답입니다.", cited_anchor_count=0, fabricated_anchor_count=0
    ) == (VIOLATION_NO_CITATION,)


def test_empty_answer_is_a_violation() -> None:
    assert check_answer_contract("", cited_anchor_count=0, fabricated_anchor_count=0) == (
        VIOLATION_NO_CITATION,
    )


@pytest.mark.parametrize(
    "text",
    [
        "제공된 자료로는 알 수 없습니다.",
        "제공된 자료로는 답변할 수 없습니다.",
        "이 내용은 자료에서 찾을 수 없습니다.",
        "제공된 자료에 해당 내용이 없습니다.",
        "자료에 없습니다.",
        "관련 근거가 없습니다.",
        "제공된 자료로는 알 수 없습니다.\n\n영업이익을 확인하려면 재무제표가 필요합니다.",
        "## 핵심 답변\n\n제공된 자료로는 알 수 없습니다.",
        "제공된 자료로는 이 질문에 답할 수 없습니다.",
        "제공된 자료에서 관련 정보를 찾을 수 없습니다.",
        "**제공된 자료로는 알 수 없습니다.**",
        # 합성 샘플 재생에서 실제 모델이 낸 근거 부족 답변
        "제공된 자료로는 알 수 없습니다.\n\n영업이익을 확인하려면 재무제표가 필요합니다.",
        "제공된 자료로는 알 수 없습니다.\n\n경영 실적 보고서가 있어야 답할 수 있습니다.",
        "## 핵심 답변\n\n제공된 자료로는 알 수 없습니다.\n\n---\n\n## 불확실한 부분",
    ],
)
def test_abstention_without_citation_passes(text: str) -> None:
    assert check_answer_contract(text, cited_anchor_count=0, fabricated_anchor_count=0) == ()


def test_fabricated_anchor_is_a_violation_even_with_real_citations() -> None:
    assert check_answer_contract(
        "답 [[wiki:w1]]", cited_anchor_count=1, fabricated_anchor_count=1
    ) == (VIOLATION_FABRICATED_ANCHOR,)


def test_uncited_connecting_sentences_are_not_judged() -> None:
    text = "요약하면 다음과 같습니다. 마감은 오후 2시입니다 [[src:s1]]. 참고하세요."
    assert check_answer_contract(text, cited_anchor_count=1, fabricated_anchor_count=0) == ()


def test_repair_instruction_lists_only_issued_anchors() -> None:
    text = repair_instruction((VIOLATION_NO_CITATION,), ["w1", "s1"])
    assert "[[wiki:w1]]" in text
    assert "[[src:s1]]" in text


def test_fallback_uses_only_issued_anchors_and_removes_body_anchor_syntax() -> None:
    text = build_fallback_answer(
        _evidence(),
        _ISSUANCE,
        {_WIKI: "마감은 오후 2시다 [[wiki:w9]] [[src:s99]]", _CHUNK: "원문 근거 문장 [[src:s7]]"},
    )
    assert text.startswith(FALLBACK_NOTICE)
    assert {m.group(0) for m in BROAD_ANCHOR_PATTERN.finditer(text)} == {
        "[[wiki:w1]]",
        "[[src:s1]]",
    }
    assert {m.group(1) for m in ISSUED_ANCHOR_PATTERN.finditer(text)} == {"wiki:w1", "src:s1"}


def test_fallback_removes_anchors_from_titles_and_nested_anchors() -> None:
    evidence = [
        EvidenceHit.wiki(wiki_id=_WIKI, rank=1, metadata={"title": "제목 [[src:s1]] [[wiki:w9]]"}),
        EvidenceHit.source(chunk_id=_CHUNK, rank=1, metadata={}),
    ]
    text = build_fallback_answer(
        evidence,
        _ISSUANCE,
        {_WIKI: "중첩 [[wi[[wiki:w8]]ki:w1]] 본문", _CHUNK: "원문"},
    )
    assert {m.group(0) for m in BROAD_ANCHOR_PATTERN.finditer(text)} == {
        "[[wiki:w1]]",
        "[[src:s1]]",
    }
    assert text.count("[[wiki:w1]]") == 1
    assert text.count("[[src:s1]]") == 1


def test_fallback_alternates_kinds_and_is_bounded() -> None:
    wiki_ids = [f"{i}1111111-1111-4111-8111-111111111111" for i in range(1, 6)]
    chunk_ids = [f"{i}2222222-2222-4222-8222-222222222222" for i in range(1, 6)]
    evidence = [
        *[EvidenceHit.wiki(wiki_id=w, rank=i, metadata={}) for i, w in enumerate(wiki_ids, 1)],
        *[EvidenceHit.source(chunk_id=c, rank=i, metadata={}) for i, c in enumerate(chunk_ids, 1)],
    ]
    issuance = {
        **{f"w{i}": ("wiki", w) for i, w in enumerate(wiki_ids, 1)},
        **{f"s{i}": ("source", c) for i, c in enumerate(chunk_ids, 1)},
    }
    text = build_fallback_answer(evidence, issuance, {})
    anchors = [m.group(1) for m in ISSUED_ANCHOR_PATTERN.finditer(text)]
    assert anchors == ["wiki:w1", "src:s1", "wiki:w2", "src:s2", "wiki:w3", "src:s3"]


def test_long_body_is_cut() -> None:
    text = build_fallback_answer(_evidence(), _ISSUANCE, {_WIKI: "가" * 1000})
    assert len(text) < 500


@pytest.mark.parametrize(
    "text",
    [
        "원인을 알 수 없는 오류가 나면 재시도합니다.",
        "문서 업로드 용량에는 제한이 없습니다.",
        "자료 처리 비용은 없습니다.",
        "자료에 따르면 환불 수수료는 없습니다.",
        "문서를 찾을 수 없으면 관리자에게 문의합니다.",
        "문서를 찾을 수 없는 경우 재시도합니다.",
        "환불을 거부할 근거가 없습니다.",
        "환불은 구매 후 7일 이내에 가능합니다. 부분 환불 여부는 제공된 자료로는 알 수 없습니다.",
        "환불은 7일 안에 됩니다. 수수료는 3천 원입니다. 다만 배송비는 자료에서 찾을 수 없습니다.",
        "제공된 자료로는 알 수 없습니다. 하지만 환불은 7일 안에 됩니다.",
        "제공된 자료로는 알 수 없습니다. 환불에는 영수증이 필요합니다.",
        "제공된 자료로는 알 수 없습니다. 영수증이 있으면 환불은 7일 안에 됩니다.",
        "환불은 구매 후 7일 이내에 가능하지만 부분 환불 여부는 자료에서 찾을 수 없습니다.",
        "자료에서 찾을 수 없는 경우 재시도합니다.",
        "제공된 자료로는 알 수 없습니다. 영수증 자료를 제공하면 환불은 7일 안에 됩니다.",
        "- 환불은 7일 안에 됩니다\n- 수수료는 자료에서 찾을 수 없습니다",
        "제공된 자료로는 알 수 없습니다.\n- 환불은 7일 안에 됩니다",
    ],
)
def test_general_answers_are_still_violations(text: str) -> None:
    assert check_answer_contract(text, cited_anchor_count=0, fabricated_anchor_count=0) == (
        VIOLATION_NO_CITATION,
    )


def test_deep_nesting_is_stripped_in_bounded_time() -> None:
    deep = "[[wi" * 80_000 + "[[wiki:w1]]" + "ki:w1]]" * 80_000
    started = time.perf_counter()
    cleaned = strip_forged_anchors(deep)
    assert time.perf_counter() - started < 2.0
    assert not BROAD_ANCHOR_PATTERN.search(cleaned)


def test_shallow_nesting_is_fully_removed() -> None:
    assert strip_forged_anchors("앞 [[wi[[wiki:w8]]ki:w1]] 뒤") == "앞  뒤"
    assert strip_forged_anchors("[[일반 링크]]는 그대로") == "[[일반 링크]]는 그대로"


@pytest.mark.parametrize("depth", [7, 8, 9, 20])
@pytest.mark.parametrize("prefix", ["", "[", "[[[", "[[[[["])
def test_odd_bracket_runs_cannot_leave_an_anchor(depth: int, prefix: str) -> None:
    deep = "[[wi" * depth + "[[wiki:w8]]" + "ki:w1]]" * depth
    assert not BROAD_ANCHOR_PATTERN.search(strip_forged_anchors(prefix + deep))


def test_blank_heavy_answers_are_judged_in_bounded_time() -> None:
    started = time.perf_counter()
    check_answer_contract("\n" * 200_000, cited_anchor_count=0, fabricated_anchor_count=0)
    assert time.perf_counter() - started < 1.0
