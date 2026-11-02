"""`scripts/ask_replay.py`의 순수 로직 검사.

이 스크립트의 수치가 이력서와 쇼케이스에 인용되므로, 집계가 조용히 틀리면 그대로 거짓 근거가 된다.
네트워크 없이 파싱·집계·안전장치만 검사한다.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("ask_replay", _ROOT / "scripts" / "ask_replay.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


replay = _load()


def _row(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "q01",
        "status": "resolved",
        "prompt_tokens": 1000,
        "completion_tokens": 100,
        "cost_micros": 10,
        "dual_citation_rate": 1.0,
        "unsourced_sentence_ratio": 0.0,
        "fabricated_anchor_count": 0,
        "keyword_hit": True,
        "budget": None,
        **overrides,
    }


@pytest.mark.parametrize(
    "url",
    [
        "https://abc.supabase.co",
        "https://api-production-44b4.up.railway.app",
        "http://10.0.0.1:8000",
    ],
)
def test_non_loopback_urls_are_refused(url: str) -> None:
    with pytest.raises(SystemExit):
        replay.assert_loopback(url)


def test_loopback_url_is_normalized() -> None:
    assert replay.assert_loopback("http://127.0.0.1:54621/") == "http://127.0.0.1:54621"


def test_parse_sse_groups_frames_and_keeps_order() -> None:
    lines = [
        "event: meta",
        'data: {"thread_id": "t"}',
        "",
        "event: delta",
        'data: {"text": "가"}',
        "",
        "event: done",
        "data: {}",
    ]
    assert replay.parse_sse(lines) == [
        ("meta", {"thread_id": "t"}),
        ("delta", {"text": "가"}),
        ("done", {}),
    ]


def test_parse_sse_surfaces_broken_frames() -> None:
    with pytest.raises(json.JSONDecodeError):
        replay.parse_sse(["event: delta", "data: {broken", ""])


def test_citations_text_replaces_accumulated_deltas() -> None:
    events = [
        ("delta", {"text": "위조 "}),
        ("delta", {"text": "앵커"}),
        ("citations", {"text": "정리본"}),
    ]
    assert replay.answer_text(events) == "정리본"
    assert replay.answer_text(events[:2]) == "위조 앵커"


def test_keyword_hit_ignores_spacing_and_skips_unanswerable_questions() -> None:
    assert replay.keyword_hit("마감은 오후 2시 입니다", ["오후2시"]) is True
    assert replay.keyword_hit("마감은 오후 3시 입니다", ["오후2시"]) is False
    assert replay.keyword_hit("모릅니다", []) is None


def test_no_llm_turns_do_not_dilute_citation_rate() -> None:
    summary = replay.summarize(
        [
            _row(dual_citation_rate=0.5),
            _row(
                id="q02",
                status="no-evidence",
                prompt_tokens=None,
                completion_tokens=None,
                keyword_hit=None,
            ),
        ]
    )
    assert summary["questions"] == 2
    assert summary["llm_turns"] == 1
    assert summary["dual_citation_rate_mean"] == 0.5
    assert summary["keyword_recall"] == 1.0


def test_summary_counts_budget_effects() -> None:
    summary = replay.summarize(
        [
            _row(budget={"truncated": True, "dropped_blocks": 2}),
            _row(id="q02", budget={"truncated": False, "dropped_blocks": 0}),
            _row(id="q03"),
        ]
    )
    assert summary["budget_reported_turns"] == 2
    assert summary["budget_truncated_turns"] == 1
    assert summary["budget_dropped_blocks_total"] == 2


def test_compare_uses_only_common_questions_and_states_it_is_a_sample() -> None:
    before = {
        "label": "before",
        "git_sha": "aaa",
        "rows": [_row(id="q01", prompt_tokens=1000), _row(id="q02", prompt_tokens=90000)],
    }
    after = {"label": "after", "git_sha": "bbb", "rows": [_row(id="q01", prompt_tokens=800)]}
    table = replay.compare_table(before, after)
    assert "합성 샘플 문항 1개" in table
    assert "운영 트래픽 수치가 아니다" in table
    assert "| 평균 입력 토큰 | 1,000 | 800 | -20.0% |" in table


def test_select_refuses_service_role_reads_without_workspace_filter() -> None:
    with pytest.raises(ValueError):
        replay._select(None, "http://127.0.0.1:54621", "usage_events", {"select": "cost_micros"})


def test_sample_questions_point_at_real_documents() -> None:
    sample = json.loads(replay.DEFAULT_SAMPLE.read_text(encoding="utf-8"))
    ids = {document["id"] for document in sample["documents"]}
    for question in sample["questions"]:
        if question.get("doc") == "none":
            assert question.get("answerable") is False
            continue
        assert set(question["doc"].split("+")) <= ids
        assert question["expect_any"]


def test_sample_expected_facts_exist_in_the_source_documents() -> None:
    """기대값이 원문에 없으면 포함률이 근거 없이 깎인다. 교차 계산 값은 하나 이상만 있으면 된다."""
    sample = json.loads(replay.DEFAULT_SAMPLE.read_text(encoding="utf-8"))
    corpus = "".join("".join(document["text"].split()) for document in sample["documents"])
    for question in sample["questions"]:
        if question["expect_any"]:
            assert any("".join(item.split()) in corpus for item in question["expect_any"]), (
                question["id"]
            )
