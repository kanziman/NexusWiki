"""`scripts/evaluation_showcase.py`의 공개 기록 export · check 검사.

공개 쇼케이스는 저장소에 커밋한 JSON만 보여 준다. 허용 목록 밖 필드가 새거나, 손으로 고친 숫자가
회차 수치와 어긋나거나, 무효 묶음이 결과처럼 남으면 공개 화면이 조용히 거짓을 말한다. 그 판정을
네트워크 없이 고정한다.
"""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[3]
COMMITTED = _ROOT / "apps" / "dashboard" / "content" / "evaluation.json"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "evaluation_showcase", _ROOT / "scripts" / "evaluation_showcase.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


show = _load()
rel = show.reliability

SAMPLE = {
    "version": 1,
    "documents": [{"id": "a"}, {"id": "b"}],
    "questions": [
        {"id": "q1", "doc": "a", "query": "첫 질문", "expect_any": ["x"]},
        {"id": "q2", "doc": "b", "query": "둘째 질문", "expect_any": ["y"]},
        {"id": "q3", "doc": "none", "query": "답 없는 질문", "answerable": False, "expect_any": []},
    ],
}
PROVENANCE = {
    "report_sha256": "r",
    "fixture_sha256": "f",
    "labels_sha256": "l",
    "curated_sha256": "c",
}


def _surface(surface: str, status: str, **fields: Any) -> dict[str, Any]:
    base = dict.fromkeys(sorted(show.MAP_KEYS))
    return {**base, "surface": surface, "status": status, **fields}


CURATED = {
    "version": 1,
    "notice": "테스트용",
    "map": [
        _surface(
            "검색",
            "partial",
            summary="1순위 적중 27/29",
            denominator="29문항",
            measured_at="2026-11-09",
            source="기록",
            source_url="https://github.com/kanziman/NexusWiki/blob/abc/x.md",
        ),
        _surface(
            "최종 답 정답성", "partial", derived_from="series.answerable", measured_at="2026-11-09"
        ),
        _surface("판사 자체", "empty", reason="판사를 쓰지 않는다"),
    ],
    "ledger": [
        {
            "date": "2026-11-07",
            "changed": "기준을 고쳤다",
            "technique": "성적표",
            "applied": "판정을 붙였다",
            "evidence": "PR #223",
            "evidence_url": "https://github.com/kanziman/NexusWiki/pull/223",
        },
        {
            "date": "2026-11-09",
            "changed": "고정 실패임을 확인했다",
            "technique": "반복 측정",
            "applied": "세 번 돌렸다",
            "evidence": "PR #247",
            "evidence_url": None,
        },
    ],
}


DEFAULT_RUNS = [
    ("reliability-1", "http"),
    ("reliability-2", "http"),
    ("ablation-answer:bothxbody", "harness"),
]
# q1은 늘 통과, q2는 늘 실패(알려진 실패), q3은 거절 문항으로 늘 정확히 거절한다.
DEFAULT_MATRIX = {"q1": ["pass"] * 3, "q2": ["fail"] * 3, "q3": ["pass"] * 3}
LABELS = {"q2": {"id": "q2", "cause": "question_ambiguity", "known_failure": True, "note": "모호"}}
REFUSAL_IDS = {"q3"}


def _report(
    matrix: dict[str, list[str]] | None = None,
    runs: list[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    matrix = matrix or DEFAULT_MATRIX
    runs = runs or DEFAULT_RUNS
    summaries = []
    for i, (label, path) in enumerate(runs):
        cells = {qid: outcomes[i] for qid, outcomes in matrix.items()}
        answerable = [o for q, o in cells.items() if q not in REFUSAL_IDS and o != "not_run"]
        refusal = [o for q, o in cells.items() if q in REFUSAL_IDS and o != "not_run"]
        passed = sum(1 for o in answerable if o == "pass")
        interval = rel.wilson_interval(passed, len(answerable))
        summaries.append(
            {
                "label": label,
                "path": path,
                "revision": "abc123+dirty",
                "planned": len(matrix),
                "asked": len(answerable) + len(refusal),
                "stopped": None,
                "cost_micros": 760310,
                "answerable_asked": len(answerable),
                "answerable_passed": passed,
                "refusal_asked": len(refusal),
                "refusal_correct": sum(1 for o in refusal if o == "pass") if refusal else None,
                "false_refusals": 0,
                "answerable_pass_rate": passed / len(answerable) if answerable else None,
                "answerable_interval_95": list(interval) if interval else None,
                "stage_counts": {},
                "known_failures": [],
                "unexpected_failures": [],
                "known_failures_passed": [],
            }
        )
    questions = []
    for qid, outcomes in matrix.items():
        label = LABELS.get(qid)
        auto = ["retrieval_miss" if o == "fail" else None for o in outcomes]
        reported = [(label["cause"] if label else a) for a in auto]
        questions.append(
            {
                "id": qid,
                "outcomes": outcomes,
                "passed": outcomes.count("pass"),
                "asked": len([o for o in outcomes if o != "not_run"]),
                "stability": rel.stability(outcomes),
                "known_failure": bool(label),
                "label_cause": label["cause"] if label else None,
                "label_evidence": "내부 근거 경로" if label else None,
                "automatic_stages": auto,
                "reported_stages": [r if a else None for r, a in zip(reported, auto, strict=True)],
            }
        )
    http = [s for s in summaries if s["path"] == "http"]
    mixed = len({s["path"] for s in summaries}) > 1
    return {
        "schema": rel.SCHEMA,
        "created_at": "2026-11-09T01:15:21Z",
        "series_key": {
            "snapshot_sha256": "snap",
            "fixture_sha256": show.fingerprint.fixture_sha256(SAMPLE),
            "model": "anthropic/claude-sonnet-4.6",
            "policy_version": "hybrid-rrf-v2",
            "requested_k": 8,
            "answer_prompt_sha256": "prompt",
        },
        "runs": summaries,
        "not_run": [],
        "spread": {"all": rel.spread(summaries), "http_only": rel.spread(http) if mixed else None},
        "questions": questions,
        "stability_counts": {
            n: sum(1 for q in questions if q["stability"] == n) for n in show.STABILITY_NAMES
        },
        "retrieval_records": [
            {"source": "retrieval.json", "kind": "x", "used": True, "reason": None}
        ],
        "notes": [],
        "limitations": ["합성 샘플이다."],
    }


def _public(report: dict[str, Any] | None = None) -> dict[str, Any]:
    return show.build_public(
        report or _report(),
        sample=SAMPLE,
        labels=LABELS,
        curated=copy.deepcopy(CURATED),
        provenance=dict(PROVENANCE),
    )


def test_export_keeps_only_allowlisted_fields_and_public_labels():
    record = _public()
    assert show.check_public(record) == []
    runs = record["series"]["runs"]
    assert [r["label"] for r in runs] == ["HTTP 1", "HTTP 2", "스크립트 재집계 #232"]
    text = json.dumps(record, ensure_ascii=False)
    # 내부 실행 이름 · git revision · 검색 기록 출처는 공개 기록에 자리가 없다.
    for leaked in ("ablation-answer", "abc123", "retrieval.json", "revision", "stage_counts"):
        assert leaked not in text
    assert record["series"]["key"]["prompt_sha256"] == "prompt"
    assert runs[0]["cost_usd"] == pytest.approx(0.76031)
    assert record["synthetic"] == {
        "documents": 2,
        "questions": 3,
        "answerable": 2,
        "unanswerable": 1,
    }


def test_mixed_paths_keep_http_only_spread_and_single_path_has_none():
    mixed = _public()
    assert mixed["series"]["spread"]["http_only"]["runs"] == 2
    assert mixed["series"]["spread"]["http_only"]["paths"] == ["http"]
    single = _public(
        _report(
            {"q1": ["pass", "pass"], "q2": ["fail", "pass"], "q3": ["pass", "pass"]},
            [("reliability-1", "http"), ("reliability-2", "http")],
        )
    )
    assert single["series"]["spread"]["http_only"] is None
    assert show.check_public(single) == []


def test_run_without_refusal_questions_is_absent_not_zero():
    record = _public(
        _report({"q1": ["pass"], "q2": ["fail"], "q3": ["not_run"]}, [("reliability-1", "http")])
    )
    run = record["series"]["runs"][0]
    assert run["refusal_asked"] == 0
    assert run["refusal_correct"] is None
    assert show.check_public(record) == []
    broken = copy.deepcopy(record)
    broken["series"]["runs"][0]["refusal_correct"] = 0
    assert any("없음이어야" in p for p in show.check_public(broken))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("interval_95", [0.5, 0.99], "Wilson"),
        ("answerable_passed", 3, "통과 수"),
        ("path", "browser", "http 또는 harness"),
        ("asked", 4, "계획 수"),
    ],
)
def test_check_rejects_numbers_that_do_not_match_the_run(field, value, message):
    record = _public()
    record["series"]["runs"][0][field] = value
    assert any(message in p for p in show.check_public(record))


def test_check_rejects_spread_that_does_not_match_runs():
    record = _public()
    record["series"]["spread"]["all"]["max_rate"] = 1.0
    assert any("spread.all" in p for p in show.check_public(record))
    record = _public()
    record["series"]["spread"]["http_only"] = None
    assert any("http_only" in p for p in show.check_public(record))


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r.__setitem__("extra", 1),
        lambda r: r["series"]["runs"][0].__setitem__("workspace_id", "w-1"),
        lambda r: r["series"]["runs"][0].__setitem__("answer", "본문"),
        lambda r: r["provenance"].__setitem__("generation_id", "gen-1"),
        lambda r: r["series"]["key"].__setitem__("user_id", "u-1"),
    ],
)
def test_check_rejects_forbidden_or_unlisted_fields(mutate):
    record = _public()
    mutate(record)
    assert show.check_public(record)


def test_invalid_series_carries_reason_and_no_numbers():
    report = _report()
    report["series_key"]["model"] = rel.UNKNOWN
    record = _public(report)
    series = record["series"]
    assert series["valid"] is False
    assert "model" in series["invalid_reason"]
    assert series["runs"] == [] and series["spread"] is None and series["stability_counts"] is None
    assert show.check_public(record) == []
    leaked = copy.deepcopy(record)
    leaked["series"]["runs"] = _public()["series"]["runs"]
    assert any("무효 묶음에 수치" in p for p in show.check_public(leaked))
    no_reason = copy.deepcopy(record)
    no_reason["series"]["invalid_reason"] = ""
    assert any("이유가 없다" in p for p in show.check_public(no_reason))


def test_fixture_mismatch_marks_series_invalid():
    report = _report()
    report["series_key"]["fixture_sha256"] = "다른 fixture"
    record = _public(report)
    assert record["series"]["valid"] is False
    assert "fixture" in record["series"]["invalid_reason"]


def test_export_refuses_to_write_a_record_that_fails_check(tmp_path, monkeypatch):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    sample_path = tmp_path / "sample.json"
    sample_path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    curated_path = tmp_path / "curated.json"
    curated_path.write_text(json.dumps(CURATED), encoding="utf-8")
    out = tmp_path / "out.json"
    monkeypatch.setattr(show, "check_public", lambda record: ["가짜 문제"])
    with pytest.raises(SystemExit):
        show.main(
            [
                "export",
                "--report",
                str(report_path),
                "--fixture",
                str(sample_path),
                "--labels",
                str(sample_path),
                "--curated",
                str(curated_path),
                "--out",
                str(out),
            ]
        )
    assert not out.exists()


def test_export_cli_writes_checked_record(tmp_path):
    report_path = tmp_path / "report.json"
    report_path.write_text(json.dumps(_report()), encoding="utf-8")
    sample_path = tmp_path / "sample.json"
    sample_path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    curated_path = tmp_path / "curated.json"
    curated_path.write_text(json.dumps(CURATED), encoding="utf-8")
    out = tmp_path / "out.json"
    assert (
        show.main(
            [
                "export",
                "--report",
                str(report_path),
                "--fixture",
                str(sample_path),
                "--labels",
                str(sample_path),
                "--curated",
                str(curated_path),
                "--out",
                str(out),
            ]
        )
        == 0
    )
    assert show.main(["check", str(out)]) == 0


def test_questions_carry_fixture_text_kind_note_and_both_stages():
    record = _public()
    questions = {q["id"]: q for q in record["series"]["questions"]}
    assert questions["q1"]["query"] == "첫 질문"
    assert questions["q3"]["kind"] == "refusal"
    known = questions["q2"]
    assert known["outcomes"] == ["fail", "fail", "fail"]
    assert known["stability"] == "stable_fail"
    assert known["reported_stage"] == "question_ambiguity"
    assert known["automatic_stage"] == "retrieval_miss"
    assert known["note"] == "모호"
    assert questions["q1"]["reported_stage"] is None
    # 라벨의 내부 근거 경로는 공개하지 않는다. 방문자용 메모(note)만 나간다.
    assert "내부 근거 경로" not in json.dumps(record, ensure_ascii=False)


def test_failed_runs_with_different_stages_are_mixed():
    report = _report()
    report["questions"][1]["automatic_stages"] = ["retrieval_miss", "composition", "retrieval_miss"]
    question = _public(report)["series"]["questions"][1]
    assert question["automatic_stage"] == "mixed"
    assert show.check_public(_public(report)) == []


def test_partially_executed_run_keeps_not_run_out_of_failures():
    report = _report(
        {"q1": ["pass", "not_run"], "q2": ["fail", "not_run"], "q3": ["pass", "pass"]},
        [("reliability-1", "http"), ("reliability-2", "http")],
    )
    record = _public(report)
    assert show.check_public(record) == []
    stopped = record["series"]["runs"][1]
    assert stopped["asked"] == 1 and stopped["answerable_asked"] == 0
    assert stopped["interval_95"] is None
    questions = {q["id"]: q for q in record["series"]["questions"]}
    assert questions["q1"]["stability"] == "stable_pass"
    assert questions["q2"]["stability"] == "stable_fail"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda q: q[0].__setitem__("stability", "stable_fail"), "stability"),
        (lambda q: q[0].__setitem__("outcomes", ["pass", "pass"]), "outcomes"),
        (lambda q: q[0].__setitem__("outcomes", ["pass", "pass", "skip"]), "outcomes"),
        (lambda q: q[2].__setitem__("kind", "answerable"), "거절 문항 수"),
        (lambda q: q[0].__setitem__("reported_stage", "composition"), "실패가 없는데"),
        (lambda q: q[1].__setitem__("reported_stage", None), "보고 단계가 없다"),
        (lambda q: q[1].__setitem__("automatic_stage", "made_up"), "알 수 없는 단계"),
        (lambda q: q[1].__setitem__("outcomes", ["pass", "fail", "fail"]), "stability"),
        (lambda q: q.pop(), "문항 수"),
        (lambda q: q[1].__setitem__("id", "q1"), "중복"),
    ],
)
def test_check_rejects_question_results_that_do_not_add_up(mutate, message):
    record = _public()
    mutate(record["series"]["questions"])
    assert any(message in p for p in show.check_public(record))


def test_check_rejects_run_totals_that_differ_from_question_cells():
    record = _public()
    record["series"]["questions"][1]["outcomes"] = ["pass", "fail", "fail"]
    record["series"]["questions"][1]["stability"] = "unstable"
    problems = show.check_public(record)
    assert any("문항 결과와 다르다" in p for p in problems)


def test_check_rejects_stability_counts_that_differ_from_questions():
    record = _public()
    record["series"]["stability_counts"]["stable_pass"] += 1
    assert any("stability_counts" in p for p in show.check_public(record))


def test_report_whose_questions_differ_from_fixture_is_invalid():
    report = _report()
    report["questions"] = report["questions"][:2]
    record = _public(report)
    assert record["series"]["valid"] is False
    assert "문항" in record["series"]["invalid_reason"]
    assert record["series"]["questions"] == []


def test_map_and_ledger_come_from_curated_file_unchanged():
    record = _public()
    assert record["map"] == CURATED["map"]
    assert record["ledger"] == CURATED["ledger"]
    assert "notice" not in json.dumps(record["map"], ensure_ascii=False)


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda m, g: m[1].__setitem__("summary", "3회 모두 28/29"), "파생 칸에 직접"),
        (lambda m, g: m[1].__setitem__("denominator", "29문항"), "파생 칸에 직접"),
        (lambda m, g: m[0].__setitem__("summary", "가" * 61), "60자"),
        (lambda m, g: m[0].__setitem__("denominator", None), "denominator"),
        (lambda m, g: m[0].__setitem__("measured_at", "11월 9일"), "YYYY-MM-DD"),
        (lambda m, g: m[0].__setitem__("source_url", "javascript:alert(1)"), "https"),
        (lambda m, g: m[2].__setitem__("reason", ""), "이유가 없다"),
        (lambda m, g: m[2].__setitem__("summary", "0/0"), "비어 있음 칸에 수치"),
        (lambda m, g: m[0].__setitem__("status", "great"), "status"),
        (lambda m, g: m[0].__setitem__("surface", "판사 자체"), "중복"),
        (lambda m, g: g.reverse(), "오름차순"),
        (lambda m, g: g[0].__setitem__("changed", " "), "changed"),
        (lambda m, g: g[0].__setitem__("evidence_url", "http://x"), "https"),
        (lambda m, g: g[0].__setitem__("author_user_id", "u"), "공개할 수 없는"),
    ],
)
def test_check_rejects_broken_map_or_ledger(mutate, message):
    record = _public()
    mutate(record["map"], record["ledger"])
    assert any(message in p for p in show.check_public(record))


def test_export_rejects_curated_file_with_unexpected_keys(tmp_path):
    path = tmp_path / "curated.json"
    path.write_text(json.dumps({**CURATED, "draft": True}), encoding="utf-8")
    with pytest.raises(SystemExit):
        show._read_curated(path)


def test_committed_public_record_passes_check():
    record = json.loads(COMMITTED.read_text(encoding="utf-8"))
    assert show.check_public(record) == []
