"""`scripts/model_evidence_eval.py`의 등록 · 계획 · 상한 · 판정 · 성적표 검사.

이 실험 수치는 "저가 모델에서 위키가 정답성을 올리는가"의 근거로 인용된다. 결과를 보고 회차를
고르거나, 다른 모델의 답을 등록 모델로 세거나, 상한을 넘기면 결론이 조용히 망가지므로 네트워크
없이 고정한다.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "model_evidence_eval", _ROOT / "scripts" / "model_evidence_eval.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


me = _load()

MODELS = ["anthropic/claude-haiku-5.5", "openai/gpt-6-luna", "deepseek/deepseek-v4.1-flash"]
FIXED = {
    "snapshot_sha256": "snap",
    "chunk_boundaries_sha256": "chunks",
    "fixture_sha256": "fixture",
    "query_vectors_sha256": "qv",
    "policy_version": "hybrid-rrf-v2",
}


def _registration(**overrides: Any) -> dict[str, Any]:
    args: dict[str, Any] = {
        "models": MODELS,
        "rounds_max": 3,
        "rounds_min": 1,
        "cap_micros": 1_000_000,
        "probe_question": "q01",
        "probe_estimate_micros": 20_000,
        "safety": 1.5,
        "fixed_inputs": FIXED,
        "reference_retrieval_sha256": "ref",
        "paths": {"state": "state.json", "query_vectors": "qv.json", "sample": "sample.json"},
    }
    args.update(overrides)
    return me.build_registration(**args)


def _later(registration: dict[str, Any], seconds: int = 1) -> str:
    return (
        datetime.fromisoformat(registration["created_at"]) + timedelta(seconds=seconds)
    ).isoformat()


def _probe(registration: dict[str, Any], probe_model: str, **row: Any) -> dict[str, Any]:
    base = {"id": "q01", "doc": "delivery", "status": "resolved", "cost_micros": 800}
    record = me.build_probe_record(registration, probe_model, {**base, **row})
    record["created_at"] = _later(registration)
    return record


def _call(model: str, **fields: Any) -> dict[str, Any]:
    return {
        "model": model,
        "accounting_status": "settled",
        "prompt_tokens": 5000,
        "completion_tokens": 500,
        "budget_micros": 800,
        **fields,
    }


# --- 사전 등록 -----------------------------------------------------------------


def test_registration_edited_after_creation_is_refused() -> None:
    registration = _registration()
    me.check_registration(registration)
    registration["cap_micros"] = 5_000_000
    with pytest.raises(SystemExit, match="바뀌었다"):
        me.check_registration(registration)


def test_registration_without_positive_cap_is_refused() -> None:
    with pytest.raises(SystemExit, match="상한"):
        _registration(cap_micros=0)


def test_reingested_stack_names_snapshot_as_differing_input() -> None:
    actual = {**FIXED, "snapshot_sha256": "other"}
    assert me.differing_fixed_inputs(FIXED, actual) == ["snapshot_sha256"]


def test_record_at_or_before_registration_is_refused() -> None:
    registration = _registration()
    with pytest.raises(SystemExit, match="이르거나"):
        me._require_after_registration(registration, registration["created_at"])


# --- 턴 판정 · 모델 일치 ----------------------------------------------------------


def test_turn_served_by_other_model_is_measurement_failure() -> None:
    row = {"id": "q01", "doc": "delivery", "status": "resolved", "keyword_hit": True}
    enriched = me.enrich_turn(
        row, [_call("anthropic/claude-sonnet-4.6")], model=MODELS[1], max_tokens=1500
    )
    assert enriched["measurement_failure"] == "model_mismatch:anthropic/claude-sonnet-4.6"
    assert me.judge(enriched, "both")["classification"] == "measurement_failure"
    assert me.counts_for_fact({**enriched, "verdict": me.judge(enriched, "both")}) is False


def test_unsettled_cost_and_missing_usage_are_measurement_failures() -> None:
    row = {"id": "q01", "doc": "delivery", "status": "resolved"}
    unresolved = me.enrich_turn(
        row, [_call(MODELS[0], accounting_status="unresolved")], model=MODELS[0], max_tokens=1500
    )
    assert unresolved["measurement_failure"] == "cost_unresolved"
    missing = me.enrich_turn(row, [], model=MODELS[0], max_tokens=1500)
    assert missing["measurement_failure"] == "usage_missing"


def test_fallback_turn_marks_repair_and_fallback() -> None:
    row = {"id": "q02", "doc": "returns", "status": "fallback", "keyword_hit": True}
    enriched = me.enrich_turn(
        row, [_call(MODELS[2]), _call(MODELS[2])], model=MODELS[2], max_tokens=1500
    )
    assert enriched["repair_attempted"] is True
    assert enriched["fallback"] is True
    assert enriched["llm_calls"] == 2
    assert enriched["cost_micros"] == 1600
    verdict = me.judge(enriched, "both")
    # 제품 통과는 아니지만, 사실 포함은 Fallback 본문(keyword_hit)으로 센다.
    assert verdict["pass"] is False
    assert me.counts_for_fact({**enriched, "verdict": verdict}) is True


def test_truncation_detected_at_output_limit() -> None:
    row = {"id": "q01", "doc": "delivery", "status": "resolved"}
    enriched = me.enrich_turn(
        row, [_call(MODELS[0], completion_tokens=1500)], model=MODELS[0], max_tokens=1500
    )
    assert enriched["truncated"] is True


def test_source_only_answer_is_not_judged_on_dual_citation() -> None:
    row = {
        "id": "q01",
        "doc": "delivery",
        "status": "resolved",
        "keyword_hit": True,
        "fabricated_anchor_count": 0,
        "cited_wiki_count": 0,
        "cited_source_count": 2,
        "failed_channels": [],
    }
    verdict = me.judge(row, "source_only")
    assert verdict["classification"] == "fact_included"
    assert verdict["dual_citation"] is None


# --- 점검 · 계획 ---------------------------------------------------------------


def test_mismatched_probe_excludes_model_with_reason() -> None:
    registration = _registration()
    mismatched = me.enrich_turn(
        {"id": "q01", "doc": "delivery", "status": "resolved"},
        [_call("other/model")],
        model=MODELS[1],
        max_tokens=1500,
    )
    probes = {
        MODELS[0]: _probe(registration, MODELS[0]),
        MODELS[1]: _probe(registration, MODELS[1], **mismatched),
        MODELS[2]: _probe(registration, MODELS[2]),
    }
    assert probes[MODELS[1]]["ok"] is False
    plan = me.plan_rounds(registration, probes, spent_micros=0, question_count=30)
    assert plan["models"] == [MODELS[0], MODELS[2]]
    assert plan["excluded"][0]["model"] == MODELS[1]
    assert "model_mismatch" in plan["excluded"][0]["reason"]


def test_truncated_resolved_probe_stays_in_plan() -> None:
    registration = _registration()
    probes = {m: _probe(registration, m, truncated=True) for m in MODELS}
    assert probes[MODELS[0]]["truncated"] is True
    plan = me.plan_rounds(registration, probes, spent_micros=0, question_count=30)
    assert plan["models"] == MODELS


def test_rounds_shrink_to_fit_cap_by_cost_only() -> None:
    registration = _registration()
    # 턴 단위 = 2,000 × 1.5 = 3,000. 회차당 3모델 × 2조건 × 30문항 = 180턴 = 540,000.
    # 3회차 = 1,620,000 > 1,000,000, 2회차 = 1,080,000 > 1,000,000, 1회차 = 540,000.
    probes = {m: _probe(registration, m, cost_micros=2000) for m in MODELS}
    # 정답 필드를 일부러 넣는다. 계획은 이것을 읽지 않아야 한다.
    for probe in probes.values():
        probe["row"]["keyword_hit"] = False
        probe["row"]["verdict"] = {"pass": False}
    plan = me.plan_rounds(registration, probes, spent_micros=10_000, question_count=30)
    assert plan["rounds"] == 1
    assert plan["projections"] == {"3": 1_630_000, "2": 1_090_000, "1": 550_000}
    assert set(me.plan_view(probes[MODELS[0]])) == set(me._PROBE_PLAN_FIELDS)
    assert "row" not in me.plan_view(probes[MODELS[0]])


def test_cheap_probes_fit_three_rounds() -> None:
    registration = _registration()
    probes = {m: _probe(registration, m, cost_micros=800) for m in MODELS}
    plan = me.plan_rounds(registration, probes, spent_micros=3000, question_count=30)
    assert plan["rounds"] == 3


def test_no_plan_when_minimum_does_not_fit() -> None:
    registration = _registration(rounds_min=2)
    probes = {m: _probe(registration, m, cost_micros=5000) for m in MODELS}
    plan = me.plan_rounds(registration, probes, spent_micros=0, question_count=30)
    assert plan["rounds"] == 0
    assert "최소 2회차" in plan["reason"]


# --- 회차 순서 · 상한 ------------------------------------------------------------


def test_round_two_refused_while_round_one_record_missing(tmp_path: Path) -> None:
    plan = {"rounds": 2, "models": MODELS}
    for model in MODELS[:2]:
        path = me.run_path(tmp_path, 1, model)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    with pytest.raises(SystemExit, match=f"1회차 {MODELS[2]}"):
        me.check_run_order(tmp_path, plan, 2, MODELS[0])
    me.check_run_order(tmp_path, plan, 1, MODELS[2])


def test_run_order_is_round_major() -> None:
    order = me.run_order({"rounds": 2, "models": ["a", "b"]})
    assert order == [(1, "a"), (1, "b"), (2, "a"), (2, "b")]


def _questions(n: int) -> list[dict[str, Any]]:
    return [{"id": f"q{i:02d}", "doc": "delivery", "query": f"질문 {i}"} for i in range(1, n + 1)]


def test_cap_stops_before_turn_and_marks_rest_not_run() -> None:
    ledger = {"spent": 990_000}
    calls: list[str] = []

    async def spent() -> int:
        return ledger["spent"]

    async def run_turn(question: dict[str, Any]) -> dict[str, Any]:
        calls.append(question["id"])
        ledger["spent"] += 1000
        return {"id": question["id"], "doc": "delivery", "status": "resolved", "cost_micros": 1000}

    stopped: list[str] = []
    rows = asyncio.run(
        me.run_condition_turns(
            questions=_questions(10),
            run_turn=run_turn,
            spent=spent,
            cap_micros=1_000_000,
            estimate_micros=1000,
            safety=1.5,
            stopped=stopped,
        )
    )
    # 턴 직전 검사: 990,000 + 1,500 ≤ 상한 … 997,000 + 1,500 ≤, 998,000 + 1,500 ≤, 999,000 + 1,500 >
    assert calls == [f"q{i:02d}" for i in range(1, 10)]
    assert rows[-1]["status"] == "not_run"
    assert "cap 1000000" in rows[-1]["not_run_reason"]
    # 같은 stopped를 받은 다음 조건은 한 턴도 돌지 않는다.
    more = asyncio.run(
        me.run_condition_turns(
            questions=_questions(3),
            run_turn=run_turn,
            spent=spent,
            cap_micros=1_000_000,
            estimate_micros=1000,
            safety=1.5,
            stopped=stopped,
        )
    )
    assert [r["status"] for r in more] == ["not_run"] * 3


def test_measurement_failure_stops_the_run() -> None:
    async def spent() -> int:
        return 0

    async def run_turn(question: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": question["id"],
            "doc": "delivery",
            "status": "resolved",
            "cost_micros": 10,
            "measurement_failure": "model_mismatch:x",
        }

    stopped: list[str] = []
    rows = asyncio.run(
        me.run_condition_turns(
            questions=_questions(3),
            run_turn=run_turn,
            spent=spent,
            cap_micros=1_000_000,
            estimate_micros=10,
            safety=1.5,
            stopped=stopped,
        )
    )
    assert [r["status"] for r in rows] == ["resolved", "not_run", "not_run"]
    assert "measurement failure q01" in stopped[0]
    # 리뷰 r1: 멈춘 조건도 요약 · 성적표 줄까지 가야 한다(not_run 행에 판정이 없어 KeyError였다).
    rows[0]["verdict"] = me.judge(rows[0], "both")
    summary = me.summarize_rows(rows, "both")
    assert summary["measurement_failures"] == 1 and summary["not_run"] == 2


def test_cap_stopped_rows_summarize_and_reach_scoreboard(tmp_path: Path) -> None:
    async def spent() -> int:
        return 999_999

    async def run_turn(question: dict[str, Any]) -> dict[str, Any]:
        raise AssertionError("상한을 넘는 턴은 돌면 안 된다")

    stopped: list[str] = []
    rows = asyncio.run(
        me.run_condition_turns(
            questions=_questions(3),
            run_turn=run_turn,
            spent=spent,
            cap_micros=1_000_000,
            estimate_micros=1000,
            safety=1.5,
            stopped=stopped,
        )
    )
    entries = me.condition_entries({"source_onlyxbody": rows}, _questions(3), stopped[0])
    record = {"round": 3, "model": MODELS[0], "stopped": stopped[0], "conditions": entries}
    for entry in entries:
        me.append_line(
            tmp_path / me.SCOREBOARD_NAME,
            me.scoreboard_line(record=record, condition=entry, run_file="runs/x.json"),
        )
    lines, _ = me.read_lines(tmp_path / me.SCOREBOARD_NAME)
    assert [(x["condition"], x["not_run"], x["asked"]) for x in lines] == [
        ("source_onlyxbody", 3, 0),
        ("bothxbody", 3, 0),
    ]
    assert all("cap 1000000" in x["stopped"] for x in lines)


def test_exception_mid_condition_keeps_charged_turns() -> None:
    calls = {"n": 0}

    async def spent() -> int:
        return 0

    async def run_turn(question: dict[str, Any]) -> dict[str, Any]:
        calls["n"] += 1
        if calls["n"] == 3:
            raise RuntimeError("worker died")
        row = {"id": question["id"], "doc": "delivery", "status": "resolved", "cost_micros": 5}
        row["verdict"] = me.judge(
            {**row, "keyword_hit": True, "failed_channels": []}, "source_only"
        )
        return row

    started: dict[str, list[dict[str, Any]]] = {}
    with pytest.raises(RuntimeError):
        asyncio.run(
            me.run_condition_turns(
                questions=_questions(5),
                run_turn=run_turn,
                spent=spent,
                cap_micros=1_000_000,
                estimate_micros=5,
                safety=1.5,
                stopped=[],
                rows=started.setdefault("source_onlyxbody", []),
            )
        )
    entries = me.condition_entries(started, _questions(5), "exception RuntimeError")
    source, both = entries
    # 죽은 턴은 묻지 않은 턴(not_run)과 구분된다(리뷰 r2 권장).
    assert [r["status"] for r in source["rows"]] == [
        "resolved",
        "resolved",
        "interrupted",
        "not_run",
        "not_run",
    ]
    assert source["summary"]["cost_micros"] == 10
    assert source["summary"]["measurement_failures"] == 1
    assert both["summary"]["not_run"] == 5


@pytest.mark.parametrize(
    ("status", "failed_channels"),
    [("error", []), ("no-evidence", ["source_vector"])],
)
def test_refusal_question_failure_is_execution_failure(
    status: str, failed_channels: list[str]
) -> None:
    # 리뷰 r2: 402 `error`가 잘못된 거절로, 채널 실패 뒤 `no-evidence`가 정확한 거절로
    # 세이면 안 된다.
    row = {
        "id": "q30",
        "doc": "none",
        "status": status,
        "failed_channels": failed_channels,
        "answer": "",
        "fabricated_anchor_count": 0,
    }
    row = me.enrich_turn(row, [], model=MODELS[0], max_tokens=1500)
    row["verdict"] = me.judge(row, "both")
    assert row["verdict"]["classification"] == "execution_failure"
    summary = me.summarize_rows([row], "both")
    assert summary["execution_failures"] == 1
    assert summary["refusal_total"] == 0 and summary["refusal_correct"] == 0


def test_consecutive_execution_failures_stop_the_run() -> None:
    async def spent() -> int:
        return 0

    async def run_turn(question: dict[str, Any]) -> dict[str, Any]:
        row = {"id": question["id"], "doc": "delivery", "status": "error", "cost_micros": 0}
        row["verdict"] = me.judge(row, "both")
        return row

    stopped: list[str] = []
    rows = asyncio.run(
        me.run_condition_turns(
            questions=_questions(6),
            run_turn=run_turn,
            spent=spent,
            cap_micros=1_000_000,
            estimate_micros=1,
            safety=1.5,
            stopped=stopped,
        )
    )
    assert [r["status"] for r in rows] == ["error"] * 3 + ["not_run"] * 3
    assert "execution failures 3 in a row" in stopped[0]


def test_close_records_unstarted_runs_as_not_run(tmp_path: Path) -> None:
    registration = _registration()
    plan = {"rounds": 2, "models": MODELS[:2], "excluded": []}
    (tmp_path / "plan.json").write_text(json.dumps(plan), encoding="utf-8")
    stopped_record = {
        "round": 1,
        "model": MODELS[0],
        "stopped": "cap 1000000 micros: spent 999000, next turn estimate 1500",
        "answer_prompt_sha256": "prompt",
        "conditions": [],
    }
    me.write_new(me.run_path(tmp_path, 1, MODELS[0]), stopped_record)
    written = me.close_remaining(tmp_path, registration, plan, _questions(2), None)
    assert [p.name for p in written] == [
        "r1-openai_gpt-6-luna.json",
        f"r2-{me.model_slug(MODELS[0])}.json",
        "r2-openai_gpt-6-luna.json",
    ]
    record = json.loads(written[0].read_text(encoding="utf-8"))
    assert record["stopped"].startswith("not started: cap 1000000")
    assert all(r["status"] == "not_run" for c in record["conditions"] for r in c["rows"])
    lines, _ = me.read_lines(tmp_path / me.SCOREBOARD_NAME)
    assert len(lines) == 6


# --- 성적표 ------------------------------------------------------------------


def _row(qid: str, hit: bool, scope: str, doc: str = "delivery") -> dict[str, Any]:
    row = {
        "id": qid,
        "doc": doc,
        "status": "resolved",
        "keyword_hit": hit,
        "fabricated_anchor_count": 0,
        "cited_wiki_count": 1,
        "cited_source_count": 1,
        "failed_channels": [],
        "elapsed_ms": 1000,
        "cost_micros": 700,
        "answer": "비밀 답변 본문",
        "query": "비밀 질문",
    }
    row["verdict"] = me.judge(row, scope)
    return row


def _condition(name: str, hits: dict[str, bool]) -> dict[str, Any]:
    scope = me.CONDITIONS[name]
    rows = [_row(q, h, scope) for q, h in hits.items()]
    return {
        "condition": name,
        "scope": scope,
        "rows": rows,
        "summary": me.summarize_rows(rows, scope),
    }


def _write_run(
    root: Path,
    round_no: int,
    model: str,
    source: dict[str, bool],
    both: dict[str, bool],
    *,
    registration: dict[str, Any] | None = None,
    prompt: str = "prompt-1",
) -> None:
    record = {
        "schema": me.RUN_SCHEMA,
        "round": round_no,
        "model": model,
        "created_at": f"2026-11-09T10:{round_no:02d}:00+00:00",
        "stopped": None,
        "git_sha": "abc",
        "registration_sha256": registration["content_sha256"] if registration else None,
        "fixed_inputs_sha256": (
            me.canonical_sha256(registration["fixed_inputs"]) if registration else "fx"
        ),
        "answer_prompt_sha256": prompt,
        "conditions": [_condition("source_onlyxbody", source), _condition("bothxbody", both)],
    }
    path = me.run_path(root, round_no, model)
    me.write_new(path, record)
    for condition in record["conditions"]:
        me.append_line(
            root / me.SCOREBOARD_NAME,
            me.scoreboard_line(
                record=record, condition=condition, run_file=str(path.relative_to(root))
            ),
        )


def test_scoreboard_line_has_no_text_and_append_keeps_earlier_lines(tmp_path: Path) -> None:
    _write_run(tmp_path, 1, MODELS[0], {"q01": True}, {"q01": True})
    first = (tmp_path / me.SCOREBOARD_NAME).read_text(encoding="utf-8")
    _write_run(tmp_path, 1, MODELS[1], {"q01": False}, {"q01": True})
    text = (tmp_path / me.SCOREBOARD_NAME).read_text(encoding="utf-8")
    assert text.startswith(first)
    assert len(text.splitlines()) == 4
    assert "비밀" not in text
    line = json.loads(text.splitlines()[0])
    assert line["diagnostic"] is True and line["product_passed"] is None
    assert json.loads(text.splitlines()[1])["product_passed"] == 1


def test_existing_record_is_not_overwritten(tmp_path: Path) -> None:
    path = tmp_path / "x.json"
    me.write_new(path, {"a": 1})
    with pytest.raises(SystemExit, match="덮어쓰지"):
        me.write_new(path, {"a": 2})


def test_broken_line_is_skipped_and_counted(tmp_path: Path) -> None:
    (tmp_path / me.SCOREBOARD_NAME).write_text('{"model": "a"}\nnot json\n', encoding="utf-8")
    lines, broken = me.read_lines(tmp_path / me.SCOREBOARD_NAME)
    assert lines == [{"model": "a"}] and broken == 1


def test_always_recovered_and_partial_round_excluded(tmp_path: Path) -> None:
    (tmp_path / "plan.json").write_text(
        json.dumps({"models": MODELS[:2], "rounds": 3, "excluded": []}), encoding="utf-8"
    )
    for r in (1, 2):
        for model in MODELS[:2]:
            # q02는 원문만에서 늘 놓치고 위키로 늘 맞힌다. q03은 회차마다 흔들린다.
            _write_run(
                tmp_path,
                r,
                model,
                {"q01": True, "q02": False, "q03": r == 1},
                {"q01": True, "q02": True, "q03": True},
            )
    # 3회차는 한 모델만 끝났다.
    _write_run(
        tmp_path,
        3,
        MODELS[0],
        {"q01": False, "q02": False, "q03": False},
        {"q01": False, "q02": False, "q03": False},
    )
    view = me.build_view(tmp_path)
    assert view["complete_rounds"] == [1, 2]
    assert view["partial_rounds"] == [3]
    summary = view["summaries"][0]
    assert summary["rounds"] == [1, 2]
    assert summary["always_recovered"] == ["q02"]
    assert summary["wiki_diff"] == [1, 2]
    assert summary["stability"]["source_onlyxbody"] == {
        "stable_pass": 1,
        "stable_fail": 1,
        "flaky": 1,
    }
    page = me.render_html(view)
    assert "q02" in page and "부분 회차" in page


def test_values_from_records_are_escaped(tmp_path: Path) -> None:
    _write_run(tmp_path, 1, "<script>alert(1)</script>", {"q01": True}, {"q01": True})
    page = me.render_html(me.build_view(tmp_path))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;" in page


def test_non_loopback_scoreboard_host_is_refused() -> None:
    with pytest.raises(SystemExit, match="루프백"):
        me.assert_loopback_host("0.0.0.0")  # noqa: S104 - 거부되는지 확인하는 값이다
    assert me.assert_loopback_host("127.0.0.1") == "127.0.0.1"


def test_reference_lines_from_prior_sonnet_record(tmp_path: Path) -> None:
    registration = _registration()
    me.write_new(tmp_path / "registration.json", registration)
    sonnet = "anthropic/claude-sonnet-4.6"
    answer = {
        "fixed_inputs": FIXED,
        "git_sha": "016ad7b",
        "stopped": None,
        "conditions": [
            {"condition": name, "rows": [{**_row("q01", True, scope), "model": sonnet}]}
            for name, scope in (
                ("source_onlyxbody", "source_only"),
                ("bothxbody", "both"),
                ("bothxtitle_body", "both"),
            )
        ],
    }
    path = tmp_path / "answer.json"
    path.write_text(json.dumps(answer), encoding="utf-8")
    args = me.build_parser().parse_args(
        ["import-reference", "--dir", str(tmp_path), "--answer", str(path)]
    )
    assert me.cmd_import_reference(args) == 0
    lines, _ = me.read_lines(tmp_path / me.SCOREBOARD_NAME)
    assert [(x["reference"], x["round"], x["condition"], x["model"]) for x in lines] == [
        (True, None, "source_onlyxbody", sonnet),
        (True, None, "bothxbody", sonnet),
    ]
    with pytest.raises(SystemExit, match="이미"):
        me.cmd_import_reference(args)
    view = me.build_view(tmp_path)
    assert view["complete_rounds"] == []
    assert view["summaries"][-1]["reference"] is True


def test_reference_with_different_fixed_inputs_is_refused() -> None:
    registration = _registration()
    with pytest.raises(SystemExit, match="snapshot_sha256"):
        me.reference_conditions(
            {"fixed_inputs": {**FIXED, "snapshot_sha256": "x"}, "conditions": []}, registration
        )


def test_now_is_utc() -> None:
    assert datetime.fromisoformat(me._now()).tzinfo == UTC


def test_run_with_different_prompt_hash_is_not_aggregated(tmp_path: Path) -> None:
    registration = _registration()
    me.write_new(tmp_path / "registration.json", registration)
    (tmp_path / "plan.json").write_text(
        json.dumps({"models": MODELS[:1], "rounds": 2, "excluded": []}), encoding="utf-8"
    )
    _write_run(tmp_path, 1, MODELS[0], {"q01": False}, {"q01": True}, registration=registration)
    _write_run(
        tmp_path,
        2,
        MODELS[0],
        {"q01": True},
        {"q01": False},
        registration=registration,
        prompt="prompt-2",
    )
    view = me.build_view(tmp_path)
    assert view["complete_rounds"] == [1]
    assert len(view["mismatched"]) == 2
    assert view["summaries"][0]["always_recovered"] == ["q01"]
    assert "해시가 달라 합산에서 뺀 줄 2개" in me.render_html(view)


def test_planned_run_without_record_marks_round_partial(tmp_path: Path) -> None:
    (tmp_path / "plan.json").write_text(
        json.dumps({"models": MODELS[:2], "rounds": 1, "excluded": []}), encoding="utf-8"
    )
    _write_run(tmp_path, 1, MODELS[0], {"q01": True}, {"q01": True})
    view = me.build_view(tmp_path)
    assert view["complete_rounds"] == []
    assert view["partial_rounds"] == [1]
    assert view["missing_runs"] == [{"round": 1, "model": MODELS[1]}]
    assert "기록 없는 계획 실행" in me.render_html(view)


def test_summary_shows_stable_pass_fail_and_flaky(tmp_path: Path) -> None:
    (tmp_path / "plan.json").write_text(
        json.dumps({"models": MODELS[:1], "rounds": 1, "excluded": []}), encoding="utf-8"
    )
    _write_run(tmp_path, 1, MODELS[0], {"q01": True, "q02": False}, {"q01": True, "q02": True})
    page = me.render_html(me.build_view(tmp_path))
    # 위키(2·0·0) / 원문(1·1·0)
    assert "2·0·0 / 1·1·0" in page


# --- 위키 유리 시험지 실험 (wiki-advantage-eval) -----------------------------------

COMPILE = "qwen/qwen3.8-flash"


def _budget(**overrides: Any) -> dict[str, Any]:
    sample = {"documents": [], "questions": [{"id": "q01", "doc": "a", "query": "?"}]}
    args: dict[str, Any] = {
        "total_cap_micros": 1_000_000,
        "compile_model": COMPILE,
        "answer_models": MODELS,
        "sample": sample,
        "sample_path": "sample.json",
    }
    args.update(overrides)
    return me.build_budget(**args)


def test_budget_refuses_compile_model_equal_to_answer_model() -> None:
    with pytest.raises(SystemExit, match="컴파일 모델이 답변 모델과 같다"):
        _budget(compile_model=MODELS[1])


def test_registration_refuses_compile_model_among_answer_models() -> None:
    with pytest.raises(SystemExit, match="컴파일 모델"):
        _registration(budget={"compile_model": MODELS[0]})


def test_ingestion_with_failed_job_blocks_registration_cap() -> None:
    budget = _budget()
    ingestion = me.build_ingestion(
        budget=budget,
        jobs=[{"type": "compile", "status": "succeeded"}, {"type": "compile", "status": "dead"}],
        pages=12,
        documents=29,
        compile_models=[COMPILE],
        spent_micros=80_000,
    )
    assert ingestion["ok"] is False
    assert ingestion["failed_jobs"][0]["status"] == "dead"
    with pytest.raises(SystemExit, match="수집이 실패"):
        me.replay_cap(budget, ingestion, 80_000)


def test_ingestion_with_other_compile_model_or_no_pages_fails() -> None:
    budget = _budget()
    other = me.build_ingestion(
        budget=budget, jobs=[], pages=3, documents=3, compile_models=["x/y"], spent_micros=1
    )
    empty = me.build_ingestion(
        budget=budget, jobs=[], pages=0, documents=3, compile_models=[COMPILE], spent_micros=1
    )
    assert other["ok"] is False and "컴파일 모델" in other["reasons"][0]
    assert empty["ok"] is False and "위키가 없다" in empty["reasons"][0]


def test_replay_cap_is_total_minus_spent() -> None:
    budget = _budget()
    ok = me.build_ingestion(
        budget=budget, jobs=[], pages=12, documents=29, compile_models=[COMPILE], spent_micros=0
    )
    assert me.replay_cap(budget, ok, 80_000) == 920_000
    with pytest.raises(SystemExit, match="남지 않았다"):
        me.replay_cap(budget, ok, 1_000_000)


def test_conflict_turn_with_old_value_is_not_fact_correct() -> None:
    row = {
        "id": "c01",
        "doc": "old+new",
        "status": "resolved",
        "keyword_hit": True,
        "forbidden_hit": True,
        "qtype": "conflict",
    }
    assert me.fact_correct(row) is False
    row["verdict"] = me.judge({**row, "failed_channels": []}, "source_only")
    assert row["verdict"]["classification"] == "forbidden_fact"
    summary = me.summarize_rows([row], "source_only")
    assert summary["fact_included"] == 1
    assert summary["fact_correct"] == 0
    assert summary["forbidden_hits"] == 1


def test_old_rows_without_forbidden_keep_fact_result() -> None:
    assert me.fact_correct({"keyword_hit": True}) is True
    assert me.fact_correct({"keyword_hit": False}) is False
    assert me.fact_correct({"keyword_hit": None}) is None


def _summary(recovered: int, regressed: int, rounds: int) -> dict[str, Any]:
    return {
        "rounds": list(range(1, rounds + 1)),
        "always_recovered": [f"q{i}" for i in range(recovered)],
        "always_regressed": [f"r{i}" for i in range(regressed)],
    }


def test_effect_verdicts_follow_registered_criterion() -> None:
    criterion = {"min_net_recovered": 3, "min_models": 2}
    assert me.model_verdict(_summary(4, 0, 3), criterion, measurement_failures=0) == "supported"
    assert me.model_verdict(_summary(4, 2, 3), criterion, measurement_failures=0) == (
        "not_supported"
    )
    assert me.model_verdict(_summary(9, 0, 1), criterion, measurement_failures=0) == (
        "inconclusive"
    )
    assert me.model_verdict(_summary(9, 0, 3), criterion, measurement_failures=1) == (
        "inconclusive"
    )
    assert me.overall_verdict(["supported", "supported", "not_supported"], criterion) == (
        "supported"
    )
    assert me.overall_verdict(["not_supported"] * 3, criterion) == "not_supported"
    assert me.overall_verdict(["supported", "inconclusive", "not_supported"], criterion) == (
        "inconclusive"
    )


def _typed_run(
    root: Path,
    round_no: int,
    model: str,
    registration: dict[str, Any],
    source: dict[str, tuple[str, bool]],
    both: dict[str, tuple[str, bool]],
) -> None:
    def rows(cells: dict[str, tuple[str, bool]], scope: str) -> list[dict[str, Any]]:
        out = []
        for qid, (qtype, hit) in cells.items():
            doc = "none" if qtype == "refusal" else "a"
            row = _row(qid, hit, scope, doc=doc)
            row["qtype"] = qtype
            if qtype == "refusal":
                row["answer"] = "제공된 자료로는 알 수 없습니다" if hit else "1조원입니다"
                row["keyword_hit"] = None
            row["verdict"] = me.judge(row, scope)
            out.append(row)
        return out

    conditions = []
    for name, cells in (("source_onlyxbody", source), ("bothxbody", both)):
        scope = me.CONDITIONS[name]
        r = rows(cells, scope)
        conditions.append(
            {"condition": name, "scope": scope, "rows": r, "summary": me.summarize_rows(r, scope)}
        )
    record = {
        "schema": me.RUN_SCHEMA,
        "round": round_no,
        "model": model,
        "created_at": f"2026-11-10T10:{round_no:02d}:00+00:00",
        "stopped": None,
        "registration_sha256": registration["content_sha256"],
        "fixed_inputs_sha256": me.canonical_sha256(registration["fixed_inputs"]),
        "answer_prompt_sha256": "p",
        "conditions": conditions,
    }
    path = me.run_path(root, round_no, model)
    me.write_new(path, record)
    for condition in conditions:
        me.append_line(
            root / me.SCOREBOARD_NAME,
            me.scoreboard_line(
                record=record, condition=condition, run_file=str(path.relative_to(root))
            ),
        )


def test_effect_view_by_type_and_refusal_excluded(tmp_path: Path) -> None:
    registration = _registration(
        effect_criterion={"min_net_recovered": 2, "min_models": 1},
        budget={"compile_model": COMPILE},
    )
    me.write_new(tmp_path / "registration.json", registration)
    (tmp_path / "plan.json").write_text(
        json.dumps({"models": MODELS[:1], "rounds": 2, "excluded": []}), encoding="utf-8"
    )
    for r in (1, 2):
        _typed_run(
            tmp_path,
            r,
            MODELS[0],
            registration,
            # 원문만: 충돌 2문항을 놓치고, 거절은 1회차에만 성공
            {
                "c01": ("conflict", False),
                "c02": ("conflict", False),
                "m01": ("multi_doc", True),
                "r01": ("refusal", r == 1),
            },
            # 원문+위키: 충돌을 맞히고, 거절은 2회차에만 성공
            {
                "c01": ("conflict", True),
                "c02": ("conflict", True),
                "m01": ("multi_doc", True),
                "r01": ("refusal", r == 2),
            },
        )
    view = me.build_view(tmp_path)
    summary = view["summaries"][0]
    assert summary["always_recovered"] == ["c01", "c02"]
    assert "r01" not in summary["always_recovered"] + summary["always_regressed"]
    assert summary["by_type"]["conflict"]["recovered"] == ["c01", "c02"]
    assert summary["by_type"]["multi_doc"]["recovered"] == []
    assert "refusal" not in summary["by_type"]
    assert summary["verdict"] == "supported"
    assert view["effect"]["overall"] == "supported"
    page = me.render_html(view)
    assert "효과 판정: 지지" in page
    assert "거절 문항 (효과 판정에서 제외)" in page
    assert "1회: 1/1 · 2회: 0/1" in page


def test_view_without_criterion_has_no_effect_section(tmp_path: Path) -> None:
    _write_run(tmp_path, 1, MODELS[0], {"q01": True}, {"q01": True})
    view = me.build_view(tmp_path)
    assert view["effect"] is None
    assert "효과 판정" not in me.render_html(view)


def test_register_allows_only_subset_of_budget_answer_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample_path = _ROOT / "scripts" / "fixtures" / "wiki_advantage.v1.json"
    sample = me.replay._load_sample(sample_path)
    budget = me.build_budget(
        total_cap_micros=890_000,
        compile_model=COMPILE,
        answer_models=MODELS,
        sample=sample,
        sample_path=str(sample_path),
    )
    me.write_new(me.budget_path(tmp_path), budget)
    ingestion = me.build_ingestion(
        budget=budget, jobs=[], pages=39, documents=29, compile_models=[COMPILE], spent_micros=1
    )
    me.write_new(me.ingestion_path(tmp_path), ingestion)
    state = tmp_path / "state.json"
    state.write_text(
        json.dumps({"stack_url": "http://127.0.0.1:54621", "workspace_id": "ws"}), encoding="utf-8"
    )
    retrieve = tmp_path / "retrieve.json"
    retrieve.write_text(json.dumps({"phase": "retrieval", "fixed_inputs": FIXED}), encoding="utf-8")
    monkeypatch.setattr(me, "spent_since", lambda *_: 22_932)

    def args(*models: str) -> Any:
        return me.build_parser().parse_args(
            [
                "register",
                "--dir",
                str(tmp_path),
                "--state",
                str(state),
                "--query-vectors",
                "qv.json",
                "--reference-retrieval",
                str(retrieve),
                "--sample",
                str(sample_path),
                "--models",
                *models,
            ]
        )

    with pytest.raises(SystemExit, match="부분집합"):
        me.cmd_register(args(MODELS[0], "other/new-model"))
    assert me.cmd_register(args(MODELS[0], MODELS[1])) == 0
    registration = json.loads(me.registration_path(tmp_path).read_text(encoding="utf-8"))
    assert registration["models"] == MODELS[:2]
    assert registration["cap_micros"] == 890_000 - 22_932
    assert registration["effect_criterion"] == me.DEFAULT_EFFECT_CRITERION


def test_ingestion_with_pending_job_is_not_ok() -> None:
    # 리뷰 r1: 제품 재시도로 queued가 된 잡이 끝나기 전에 기록하면 다시 죽어도 ok로 남았다.
    budget = _budget()
    ingestion = me.build_ingestion(
        budget=budget,
        jobs=[{"type": "embed", "status": "succeeded"}, {"type": "embed", "status": "queued"}],
        pages=39,
        documents=29,
        compile_models=[COMPILE],
        spent_micros=1,
        workspace_id="ws-1",
    )
    assert ingestion["ok"] is False
    assert "끝나지 않은 잡 1개" in ingestion["reasons"]
    assert ingestion["workspace_id"] == "ws-1"


def test_capped_select_refuses_truncated_aggregate(monkeypatch: pytest.MonkeyPatch) -> None:
    rows = [{"status": "succeeded"}] * me.replay.POSTGREST_MAX_ROWS
    monkeypatch.setattr(me.replay, "_select", lambda *_, **__: rows)
    with pytest.raises(SystemExit, match="잘렸을 수 있다"):
        me.replay.select_capped(None, "http://127.0.0.1:1", "jobs", {"workspace_id": "eq.x"})


def test_overall_verdict_inconclusive_on_any_measurement_failure() -> None:
    criterion = {"min_net_recovered": 3, "min_models": 1}
    verdicts = ["supported", "inconclusive"]
    assert me.overall_verdict(verdicts, criterion) == "supported"
    assert me.overall_verdict(verdicts, criterion, measurement_failure=True) == "inconclusive"


def test_recovered_jobs_listed_and_do_not_block() -> None:
    # 사용자 결정(리뷰 r1 blocked 2): 실패는 최종 상태 기준, 재시도로 복구한 잡은 기록에 남긴다.
    retries = [
        {"job_id": "j1", "type": "embed", "attempt": 1, "status_code": 200},
        {"job_id": "j1", "type": "embed", "attempt": 2, "status_code": 200},
        # 받아들여지지 않은 재시도 호출(409)은 세지 않는다(리뷰 r2).
        {"job_id": "j1", "type": "embed", "attempt": 3, "status_code": 409},
        {"job_id": "j2", "type": "compile", "attempt": 1, "status_code": 200},
    ]
    jobs = [
        {"id": "j1", "type": "embed", "status": "succeeded", "attempts": 1},
        {"id": "j2", "type": "compile", "status": "dead", "attempts": 3},
        # 워커 자동 재시도로 복구한 잡: 재시도 기록에는 없고 attempts로만 보인다(리뷰 r2).
        {"id": "j3", "type": "embed", "status": "succeeded", "attempts": 2},
    ]
    recovered = me.recovered_jobs(retries, jobs)
    assert recovered == [
        {"job_id": "j1", "type": "embed", "api_retries": 2, "final_status": "succeeded"},
        {
            "job_id": "j3",
            "type": "embed",
            "api_retries": 0,
            "worker_attempts": 2,
            "final_status": "succeeded",
        },
    ]
    ok = me.build_ingestion(
        budget=_budget(),
        jobs=[jobs[0], jobs[2]],
        pages=39,
        documents=29,
        compile_models=[COMPILE],
        spent_micros=1,
        recovered=recovered,
    )
    assert ok["ok"] is True
    assert [r["job_id"] for r in ok["recovered_jobs"]] == ["j1", "j3"]


def test_failed_status_waiting_for_auto_retry_is_unfinished_not_failed() -> None:
    ingestion = me.build_ingestion(
        budget=_budget(),
        jobs=[{"type": "embed", "status": "failed"}],
        pages=39,
        documents=29,
        compile_models=[COMPILE],
        spent_micros=1,
    )
    assert ingestion["ok"] is False
    assert ingestion["failed_jobs"] == []
    assert ingestion["reasons"] == ["끝나지 않은 잡 1개"]


def test_type_table_shows_wiki_difference_column(tmp_path: Path) -> None:
    registration = _registration(
        effect_criterion={"min_net_recovered": 1, "min_models": 1},
        budget={"compile_model": COMPILE},
    )
    me.write_new(tmp_path / "registration.json", registration)
    (tmp_path / "plan.json").write_text(
        json.dumps({"models": MODELS[:1], "rounds": 2, "excluded": []}), encoding="utf-8"
    )
    for r in (1, 2):
        _typed_run(
            tmp_path,
            r,
            MODELS[0],
            registration,
            # 충돌은 위키로 +1, 여러 문서는 위키로 −1 → 전체 차이는 0이다.
            {"c01": ("conflict", False), "m01": ("multi_doc", True)},
            {"c01": ("conflict", True), "m01": ("multi_doc", False)},
        )
    page = me.render_html(me.build_view(tmp_path))
    # 리뷰 r3: 전체 요약 표에도 같은 머리가 있으니 유형별 구역 안만 본다.
    start = page.index("유형별 위키 차이")
    section = page[start : page.index("거절 문항 (효과 판정에서 제외)", start)]
    assert "<th>위키 차이</th>" in section
    assert "<b>+1 · +1</b>" in section
    assert "<b>-1 · -1</b>" in section
    assert "<b>+0 · +0</b>" not in section
    assert "<b>+0 · +0</b>" in page  # 전체 요약은 0
