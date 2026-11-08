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


# --- 성적표: 판정 · 지연 · 누적 기록 · 화면 -------------------------------------------------


def _good(**overrides: Any) -> dict[str, Any]:
    base = {"status": "resolved", "doc": "delivery", "elapsed_ms": 1000, "model": "m/x"}
    return _row(**{**base, **overrides})


def test_answerable_question_passes_when_every_criterion_holds() -> None:
    assert replay.verdict(_good()) == {"pass": True, "reason": None}


def test_missing_dual_citation_fails_with_that_reason() -> None:
    result = replay.verdict(_good(dual_citation_rate=0.0))
    assert result["pass"] is False
    assert "함께 인용" in result["reason"]


def test_failure_reason_follows_the_documented_order() -> None:
    result = replay.verdict(_good(fabricated_anchor_count=2, keyword_hit=False))
    assert result["reason"] == "위조 앵커 2건"


def test_unknown_expected_fact_is_not_a_failure() -> None:
    assert replay.verdict(_good(keyword_hit=None))["pass"] is True


def test_unanswerable_question_passes_only_on_refusal() -> None:
    refused = _row(doc="none", status="no-evidence", prompt_tokens=None, keyword_hit=None)
    assert replay.verdict(refused)["pass"] is True
    answered = _row(doc="none", status="resolved")
    result = replay.verdict(answered)
    assert result["pass"] is False
    assert "답하면 안 되는" in result["reason"]


def test_turn_that_never_reached_the_model_fails_with_its_status() -> None:
    result = replay.verdict({"id": "q9", "doc": "delivery", "status": "http_500"})
    assert result == {"pass": False, "reason": "정상 완료가 아니다 (상태 http_500)"}
    assert "no-evidence" in replay.verdict({"doc": "delivery", "status": "no-evidence"})["reason"]


def test_fallback_is_not_a_normal_completion() -> None:
    result = replay.verdict(_good(status="fallback"))
    assert result["pass"] is False
    assert "fallback" in result["reason"]


def test_summary_reports_pass_rate_and_latency_percentiles() -> None:
    rows = [_good(id=f"q{i}", elapsed_ms=i * 1000) for i in range(1, 11)]
    rows[0]["dual_citation_rate"] = 0.0  # 한 문항 불통과
    summary = replay.summarize(rows)
    assert (summary["passed"], summary["asked"]) == (9, 10)
    assert summary["pass_rate"] == 0.9
    assert summary["latency_p50_ms"] == 6000
    assert summary["latency_p95_ms"] == 10000
    assert summary["model"] == "m/x"


def test_latency_is_absent_not_zero_without_elapsed_times() -> None:
    summary = replay.summarize([{"id": "q1", "doc": "x", "status": "http_500"}])
    assert summary["latency_p50_ms"] is None
    assert summary["latency_p95_ms"] is None
    assert summary["model"] == "unknown"


def _result(label: str = "after", **kwargs: Any) -> dict[str, Any]:
    rows = [_good(id="q01"), _good(id="q02", dual_citation_rate=0.0)]
    return {
        "label": label,
        "git_sha": kwargs.get("git_sha", "abc1234"),
        "planned_questions": kwargs.get("planned", 2),
        "rows": rows,
        "summary": replay.summarize(rows),
    }


def test_scorecard_line_has_no_text_and_marks_early_stops(tmp_path: Path) -> None:
    line = replay.scorecard_line(_result(planned=30), "after.json")
    assert (line["asked"], line["planned"]) == (2, 30)
    assert line["pass_rate"] == 0.5
    assert set(line) >= {"label", "git_sha", "model", "latency_p50_ms", "latency_p95_ms"}
    assert "answer" not in json.dumps(line)


def test_scorecard_line_records_unknown_revision_and_model() -> None:
    result = _result(git_sha=None)
    result["summary"]["model"] = None
    line = replay.scorecard_line(result, None)
    assert line["git_sha"] == "unknown"
    assert line["model"] == "unknown"


def test_append_keeps_earlier_lines_untouched(tmp_path: Path) -> None:
    path = tmp_path / "scorecard.jsonl"
    replay.append_scorecard(path, {"label": "first"})
    first = path.read_text(encoding="utf-8")
    replay.append_scorecard(path, {"label": "second"})
    text = path.read_text(encoding="utf-8")
    assert text.startswith(first)
    assert [json.loads(raw)["label"] for raw in text.splitlines()] == ["first", "second"]


def test_broken_scorecard_lines_are_skipped_and_counted(tmp_path: Path) -> None:
    path = tmp_path / "scorecard.jsonl"
    path.write_text('{"label": "ok"}\n{broken\n[1]\n', encoding="utf-8")
    lines, broken = replay.read_scorecard(path)
    assert [line["label"] for line in lines] == ["ok"]
    assert broken == 2


def test_report_lists_runs_in_order_and_marks_missing_detail(tmp_path: Path) -> None:
    scorecard = tmp_path / "scorecard.jsonl"
    with_file = replay.scorecard_line(_result("a"), "a.json")
    (tmp_path / "a.json").write_text(json.dumps(_result("a")), encoding="utf-8")
    replay.append_scorecard(scorecard, with_file)
    replay.append_scorecard(scorecard, replay.scorecard_line(_result("b"), "missing.json"))
    runs, broken, _ = replay.build_report_data(scorecard, [])
    assert [r["label"] for r in runs] == ["a", "b"]
    assert runs[0]["rows"] is not None
    assert runs[1]["rows"] is None
    assert broken == 0


def test_report_rederives_verdicts_for_old_result_files(tmp_path: Path) -> None:
    old = _result("old")
    for row in old["rows"]:
        row.pop("verdict", None)
    old_path = tmp_path / "old.json"
    old_path.write_text(json.dumps(old), encoding="utf-8")
    runs, _, _ = replay.build_report_data(tmp_path / "none.jsonl", [old_path])
    assert [row["verdict"]["pass"] for row in runs[0]["rows"]] == [True, False]


def test_empty_report_names_the_command(tmp_path: Path) -> None:
    runs, broken, notes = replay.build_report_data(tmp_path / "none.jsonl", [])
    html = replay.render_report(runs, broken, notes)
    assert "합성 샘플 수치이며 운영 트래픽이 아닙니다" in html
    assert "ask_replay.py ask" in html


def test_markup_in_results_cannot_break_out_of_the_page(tmp_path: Path) -> None:
    hostile = _result("x")
    hostile["rows"][0]["answer"] = "</script><script>alert(1)</script><b>굵게</b>"
    path = tmp_path / "x.json"
    path.write_text(json.dumps(hostile), encoding="utf-8")
    runs, broken, notes = replay.build_report_data(tmp_path / "none.jsonl", [path])
    html = replay.render_report(runs, broken, notes)
    assert "</script><script>alert(1)" not in html
    assert html.count("</script>") == 2  # 데이터 블록과 화면 코드, 둘뿐이다
    assert "textContent" in html and "innerHTML" not in html


def test_wiki_and_source_in_different_sentences_still_pass() -> None:
    """스펙은 답변 단위다. 한 문장에 둘이 없어도 위키와 원문을 각각 인용했으면 통과다."""
    row = _good(dual_citation_rate=0.0, cited_wiki_count=2, cited_source_count=1)
    assert replay.verdict(row) == {"pass": True, "reason": None}


def test_answer_citing_only_wiki_fails_with_counts() -> None:
    result = replay.verdict(_good(cited_wiki_count=3, cited_source_count=0))
    assert result["pass"] is False
    assert "위키 3, 원문 0" in result["reason"]


def test_old_rows_fall_back_to_the_sentence_rate_and_say_so() -> None:
    result = replay.verdict(_good(dual_citation_rate=0.0))
    assert result["pass"] is False
    assert "옛 결과" in result["reason"]


def test_count_kind_separates_missing_events_from_zero() -> None:
    resolved = [{"kind": "wiki"}, {"kind": "source"}, {"kind": "wiki"}]
    assert replay._count_kind({"resolved": resolved}, "wiki") == 2
    assert replay._count_kind({"resolved": resolved}, "source") == 1
    assert replay._count_kind({"resolved": []}, "wiki") == 0
    assert replay._count_kind({}, "wiki") is None
