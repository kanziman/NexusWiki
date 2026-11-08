"""`scripts/ask_replay_reliability.py`의 묶음 · 변동폭 · 원인 판정 · 반복 재생 검사.

이 보고서는 "한 번의 재생 차이를 효과로 읽지 않게" 하려고 존재한다. 다른 조건의 회차가 섞이거나,
멈춘 회차의 미실행이 실패로 세지거나, 장애가 검색 미적중으로 몰리면 그 목적이 조용히 무너진다.
네트워크 없이 그 판정을 고정한다.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

_ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "ask_replay_reliability", _ROOT / "scripts" / "ask_replay_reliability.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rel = _load()
replay = rel.replay

KEY = {
    "snapshot_sha256": "snap-1",
    "fixture_sha256": "fix-1",
    "model": "m/x",
    "policy_versions": ["hybrid-rrf-v2"],
    "requested_k": 8,
    "answer_prompt_sha256": "prompt-1",
}


def _row(qid: str, *, ok: bool = True, doc: str = "a", **overrides: Any) -> dict[str, Any]:
    row = {
        "id": qid,
        "doc": doc,
        "status": "resolved",
        "fabricated_anchor_count": 0,
        "keyword_hit": ok,
        "cited_wiki_count": 1,
        "cited_source_count": 1,
        "cost_micros": 10,
        "missing_channels": [],
        "answer": "답변 본문 표식",
    }
    return {**row, **overrides}


def _result(label: str, rows: list[dict[str, Any]], **fixed: Any) -> dict[str, Any]:
    return {
        "label": label,
        "git_sha": fixed.pop("git_sha", "abc"),
        "execution_path": "http",
        "planned_questions": fixed.pop("planned", len(rows)),
        "stopped": fixed.pop("stopped", None),
        "fixed_inputs": {**KEY, **fixed},
        "rows": rows,
    }


def _report(runs: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
    return rel.build_report(
        runs,
        labels=kwargs.get("labels", {}),
        retrieval_records=kwargs.get("retrieval_records", []),
        not_run=kwargs.get("not_run"),
        fixture_ids=kwargs.get("fixture_ids"),
    )


def _http(*results: dict[str, Any]) -> list[dict[str, Any]]:
    return [rel.http_run(r, f"{r['label']}.json") for r in results]


# --- 3절: 묶음과 변동폭 --------------------------------------------------------------------


def test_runs_differing_only_in_revision_form_one_series() -> None:
    runs = _http(*(_result(f"r{n}", [_row("q01")], git_sha=sha) for n, sha in enumerate("abc", 1)))
    report = _report(runs)
    assert [r["revision"] for r in report["runs"]] == ["a", "b", "c"]
    assert report["series_key"]["snapshot_sha256"] == "snap-1"


def test_run_from_a_different_ingestion_is_refused_by_name() -> None:
    runs = _http(
        _result("r1", [_row("q01")]),
        _result("r2", [_row("q01")]),
        _result("r3", [_row("q01")], snapshot_sha256="snap-2"),
    )
    with pytest.raises(SystemExit, match="snapshot_sha256"):
        _report(runs)


def test_result_written_before_fingerprints_is_refused() -> None:
    old = _result("old", [_row("q01")])
    old.pop("fixed_inputs")
    with pytest.raises(SystemExit, match="지문이 없다"):
        _report(_http(_result("new", [_row("q01")]), old))


def test_unknown_fixed_input_is_not_assumed_equal() -> None:
    runs = _http(
        _result("r1", [_row("q01")], answer_prompt_sha256="unknown"),
        _result("r2", [_row("q01")], answer_prompt_sha256="unknown"),
    )
    with pytest.raises(SystemExit, match="answer_prompt_sha256"):
        _report(runs)


def test_two_policy_versions_inside_one_run_are_refused() -> None:
    runs = _http(_result("r1", [_row("q01")], policy_versions=["hybrid-rrf-v1", "hybrid-rrf-v2"]))
    with pytest.raises(SystemExit, match="policy_version"):
        _report(runs)


def test_question_passing_in_two_of_three_runs_is_unstable() -> None:
    runs = _http(
        _result("r1", [_row("q01")]),
        _result("r2", [_row("q01", ok=False)]),
        _result("r3", [_row("q01")]),
    )
    question = _report(runs)["questions"][0]
    assert (question["passed"], question["asked"], question["stability"]) == (2, 3, "unstable")


def test_questions_after_an_early_stop_are_not_run_not_failures() -> None:
    full = [_row(f"q{i:02d}") for i in range(1, 31)]
    stopped = _result("r2", full[:20], planned=30, stopped={"reason": "spend_cap", "asked": 20})
    report = _report(_http(_result("r1", full), stopped))
    late = next(q for q in report["questions"] if q["id"] == "q25")
    assert late["outcomes"] == ["pass", "not_run"]
    assert late["stability"] == "stable_pass"
    assert report["runs"][1]["unexpected_failures"] == []
    assert report["runs"][1]["asked"] == 20


def test_spread_reports_each_count_min_max_and_per_run_interval() -> None:
    def run(label: str, failures: int) -> dict[str, Any]:
        rows = [_row(f"q{i:02d}", ok=i > failures) for i in range(1, 30)]
        return _result(label, rows)

    report = _report(_http(run("r1", 2), run("r2", 1), run("r3", 1)))
    spread = report["spread"]["all"]
    assert spread["answerable_passed"] == [27, 28, 28]
    assert spread["min_rate"] == pytest.approx(27 / 29)
    assert spread["max_rate"] == pytest.approx(28 / 29)
    assert spread["mean_rate"] == pytest.approx((27 + 28 + 28) / 87)
    assert all(r["answerable_interval_95"] for r in report["runs"])
    assert report["spread"]["http_only"] is None  # 경로가 하나뿐이다


def test_wilson_interval_matches_the_documented_figure() -> None:
    low, high = rel.wilson_interval(28, 30)
    assert (round(low * 100, 1), round(high * 100, 1)) == (78.7, 98.2)
    assert rel.wilson_interval(0, 0) is None


def test_refusal_split_is_reported_per_run() -> None:
    rows = [_row("q01"), _row("q30", doc="none", answer="제공된 자료로는 알 수 없습니다.")]
    run = _report(_http(_result("r1", rows)))["runs"][0]
    assert (run["refusal_correct"], run["refusal_asked"], run["false_refusals"]) == (1, 1, 0)


# --- 3절: #232 하네스 회차 -----------------------------------------------------------------


def _ablation(rows: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    def condition(scope: str, embedding_input: str) -> dict[str, Any]:
        return {
            "condition": f"{scope}x{embedding_input}",
            "scope": scope,
            "embedding_input": embedding_input,
            "rows": [{**r, "verdict": {"pass": True}, "model": "m/x"} for r in rows],
        }

    record = {
        "experiment": "retrieval-evidence-ablation",
        "phase": "answer",
        "label": "ablation-answer",
        "git_sha": "016ad7b",
        "fixed_inputs": {
            "snapshot_sha256": "snap-1",
            "fixture_sha256": "fix-1",
            "policy_version": "hybrid-rrf-v2",
            "requested_k": 8,
        },
        "answer_prompt_sha256": "prompt-1",
        "conditions": [
            condition("source_only", "body"),
            condition("both", "body"),
            condition("both", "title_body"),
        ],
    }
    return {**record, **overrides}


def test_ablation_product_condition_joins_as_a_harness_run() -> None:
    runs = _http(_result("r1", [_row("q01")]), _result("r2", [_row("q01", ok=False)]))
    runs.append(rel.ablation_run(_ablation([_row("q01")]), "answer.json"))
    report = _report(runs)
    assert [r["path"] for r in report["runs"]] == ["http", "http", "harness"]
    assert report["spread"]["http_only"]["runs"] == 2
    assert report["spread"]["all"]["runs"] == 3
    # 기록의 저장된 판정이 아니라 제품 판정으로 다시 계산한다.
    assert report["questions"][0]["outcomes"] == ["pass", "fail", "pass"]


@pytest.mark.parametrize("condition", ["source_onlyxbody", "bothxtitle_body"])
def test_other_ablation_conditions_are_refused(condition: str) -> None:
    with pytest.raises(SystemExit, match="제품 설정과 달라"):
        rel.ablation_run(_ablation([_row("q01")]), "answer.json", condition)


def test_record_from_another_experiment_is_refused() -> None:
    with pytest.raises(SystemExit, match="#232 답변 기록이 아니다"):
        rel.ablation_run(_ablation([_row("q01")], experiment="rerank"), "answer.json")


# --- 4절: 처음 틀어진 단계 · 라벨 · 알려진 실패 ----------------------------------------------


def _retrieval(found: dict[str, int | None], snapshot: str = "snap-1", **status: str) -> dict:
    rows = [
        {
            "id": qid,
            "doc": "a",
            "status": status.get(qid, "ok"),
            "result": {"first_relevant_rank": rank},
        }
        for qid, rank in found.items()
    ]
    record = {"fixed_inputs": {"snapshot_sha256": snapshot}, "rows": rows}
    return rel.retrieval_evidence(record, "retrieval.json")


def _stage(row: dict[str, Any], records: list[dict[str, Any]]) -> str | None:
    report = _report(_http(_result("r1", [row])), retrieval_records=records)
    return report["questions"][0]["automatic_stages"][0]


def test_gold_absent_from_retrieval_is_a_retrieval_miss() -> None:
    assert _stage(_row("q01", ok=False), [_retrieval({"q01": None})]) == "retrieval_miss"


def test_gold_retrieved_but_answer_wrong_is_composition() -> None:
    assert _stage(_row("q01", ok=False), [_retrieval({"q01": 3})]) == "composition"


def test_http_error_is_an_execution_failure_regardless_of_retrieval() -> None:
    row = {"id": "q01", "doc": "a", "status": "http_502", "prompt_tokens": None}
    assert _stage(row, [_retrieval({"q01": None})]) == "execution_failure"


def test_failed_channel_on_the_turn_is_an_execution_failure() -> None:
    row = _row("q01", ok=False, missing_channels=["source_vector"])
    assert _stage(row, [_retrieval({"q01": 1})]) == "execution_failure"


def test_no_evidence_and_fallback_proceed_to_the_next_checks() -> None:
    no_evidence = _row("q01", status="no-evidence")
    fallback = _row("q01", status="fallback")
    assert _stage(no_evidence, [_retrieval({"q01": None})]) == "retrieval_miss"
    assert _stage(fallback, [_retrieval({"q01": 2})]) == "composition"


def test_retrieval_measurement_failure_is_not_counted_as_a_miss() -> None:
    record = _retrieval({"q01": None}, q01="channel_failed")
    assert _stage(_row("q01", ok=False), [record]) == "retrieval_evidence_unavailable"


def test_retrieval_record_from_another_ingestion_is_refused() -> None:
    report = _report(
        _http(_result("r1", [_row("q01", ok=False)])),
        retrieval_records=[_retrieval({"q01": None}, snapshot="snap-2")],
    )
    assert report["questions"][0]["automatic_stages"] == ["retrieval_evidence_unavailable"]
    assert report["retrieval_records"][0]["used"] is False


def test_unanswerable_question_answered_is_composition() -> None:
    row = _row("q30", doc="none", answer="영업이익은 1조원입니다.")
    assert _stage(row, []) == "composition"


def test_without_retrieval_records_stage_is_unavailable_not_guessed() -> None:
    assert _stage(_row("q01", ok=False), []) == "retrieval_evidence_unavailable"


def test_retrieval_eval_record_is_preferred_and_disagreement_is_reported() -> None:
    ablation_record = {
        "experiment": "retrieval-evidence-ablation",
        "phase": "retrieval",
        "fixed_inputs": {"snapshot_sha256": "snap-1"},
        "conditions": [
            {
                "condition": "bothxbody",
                "rows": [
                    {"id": "q01", "doc": "a", "status": "ok", "result": {"first_relevant_rank": 2}}
                ],
            }
        ],
    }
    records = [
        rel.retrieval_evidence(ablation_record, "retrieve.json"),
        _retrieval({"q01": None}),
    ]
    report = _report(_http(_result("r1", [_row("q01", ok=False)])), retrieval_records=records)
    assert report["questions"][0]["automatic_stages"] == ["retrieval_miss"]
    assert any("q01" in note for note in report["notes"])


_Q06_LABEL = {
    "q06": {
        "id": "q06",
        "cause": "question_ambiguity",
        "known_failure": True,
        "evidence": "#232",
    }
}


def test_labeled_failure_reports_the_label_beside_the_automatic_stage() -> None:
    report = _report(
        _http(_result("r1", [_row("q01"), _row("q06", ok=False)])),
        labels=_Q06_LABEL,
        retrieval_records=[_retrieval({"q01": 1, "q06": None})],
    )
    q06 = report["questions"][1]
    assert q06["reported_stages"] == ["question_ambiguity"]
    assert q06["automatic_stages"] == ["retrieval_miss"]
    run = report["runs"][0]
    assert (run["known_failures"], run["unexpected_failures"]) == (["q06"], [])
    assert run["stage_counts"] == {"question_ambiguity": 1}
    # 분모에서 빼지 않는다.
    assert (run["answerable_passed"], run["answerable_asked"]) == (1, 2)


def test_known_failure_that_passes_is_surfaced() -> None:
    report = _report(
        _http(_result("r1", [_row("q06", ok=False)]), _result("r2", [_row("q06")])),
        labels=_Q06_LABEL,
    )
    assert report["runs"][1]["known_failures_passed"] == ["q06"]
    assert "통과한 알려진 실패: q06" in rel.render_markdown(report)


def test_unlabeled_failure_is_unexpected() -> None:
    report = _report(_http(_result("r1", [_row("q02", ok=False)])), labels=_Q06_LABEL)
    assert report["runs"][0]["unexpected_failures"] == ["q02"]


_SAMPLE = {"questions": [{"id": "q06"}, {"id": "q07"}]}


def _labels_file(tmp_path: Path, *entries: dict[str, Any]) -> Path:
    path = tmp_path / "labels.json"
    path.write_text(json.dumps({"version": 1, "labels": list(entries)}), encoding="utf-8")
    return path


def _entry(**overrides: Any) -> dict[str, Any]:
    return {
        "id": "q06",
        "cause": "question_ambiguity",
        "known_failure": True,
        "evidence": "#232",
        **overrides,
    }


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        (_entry(evidence="  "), "근거 참조가 비었다"),
        (_entry(id="q99"), "q99"),
        (_entry(cause="retrieval"), "원인"),
        (_entry(answer="본문"), "허용하지 않는 필드 answer"),
        (_entry(known_failure="yes"), "known_failure"),
    ],
)
def test_label_file_breaking_the_contract_is_refused(
    tmp_path: Path, entry: dict[str, Any], message: str
) -> None:
    with pytest.raises(SystemExit, match=message):
        rel.load_labels(_labels_file(tmp_path, entry), _SAMPLE)


def test_duplicate_labels_are_refused(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="둘 이상"):
        rel.load_labels(_labels_file(tmp_path, _entry(), _entry()), _SAMPLE)


def test_repository_label_file_marks_q06_as_known_question_ambiguity() -> None:
    sample = replay._load_sample(replay.DEFAULT_SAMPLE)
    labels = rel.load_labels(rel.DEFAULT_LABELS, sample)
    assert labels["q06"]["cause"] == "question_ambiguity"
    assert labels["q06"]["known_failure"] is True
    assert "#232" in labels["q06"]["evidence"]


def test_fixture_hash_still_matches_the_232_record() -> None:
    """⚠️ fixture를 바꾸면 #232 회차와 새 재생이 한 묶음이 될 수 없다. 의도했는지 본다."""
    sample = replay._load_sample(replay.DEFAULT_SAMPLE)
    assert replay.fingerprint.fixture_sha256(sample) == (
        "8250970cc6732378b0208fe9a239e17dbf793d3d087e452eed94ef3b647d5d83"
    )


# --- 3 · 4절: 보고서 기록 -------------------------------------------------------------------


def _report_args(tmp_path: Path, *extra: str) -> list[str]:
    return ["report", "--out", str(tmp_path / "rel.json"), *extra]


def test_report_refuses_an_existing_output_before_reading_inputs(tmp_path: Path) -> None:
    out = tmp_path / "rel.json"
    out.write_text("keep", encoding="utf-8")
    args = rel.build_parser().parse_args(_report_args(tmp_path, "--result", "does-not-exist.json"))
    with pytest.raises(SystemExit, match="덮어쓰지 않는다"):
        args.func(args)
    assert out.read_text(encoding="utf-8") == "keep"


def test_report_record_has_no_text_or_workspace(tmp_path: Path) -> None:
    result = _result("r1", [_row("q06", ok=False, query="질문 원문 표식")])
    result["workspace_id"] = "ws-secret"
    path = tmp_path / "r1.json"
    path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    labels = _labels_file(tmp_path, _entry())
    sample = tmp_path / "sample.json"
    sample.write_text(json.dumps(_SAMPLE), encoding="utf-8")
    args = rel.build_parser().parse_args(
        _report_args(
            tmp_path, "--result", str(path), "--labels", str(labels), "--sample", str(sample)
        )
    )
    args.func(args)
    text = (tmp_path / "rel.json").read_text(encoding="utf-8")
    record = json.loads(text)
    assert record["schema"] == "ask-replay-reliability-v1"
    for secret in ("답변 본문 표식", "질문 원문 표식", "ws-secret"):
        assert secret not in text
    assert record["limitations"]


_ABLATION_DIR = _ROOT / ".worktrees" / "ablation-evidence-20261108"


@pytest.mark.skipif(not _ABLATION_DIR.exists(), reason="#232 원본 기록은 Git 밖 로컬에만 있다")
def test_real_232_records_classify_q06_as_known_question_ambiguity(tmp_path: Path) -> None:
    args = rel.build_parser().parse_args(
        _report_args(
            tmp_path,
            "--ablation-answer",
            str(_ABLATION_DIR / "answer.json"),
            "--retrieval",
            str(_ABLATION_DIR / "retrieve.json"),
        )
    )
    args.func(args)
    record = json.loads((tmp_path / "rel.json").read_text(encoding="utf-8"))
    q06 = next(q for q in record["questions"] if q["id"] == "q06")
    assert (q06["reported_stages"], q06["automatic_stages"]) == (
        ["question_ambiguity"],
        ["retrieval_miss"],
    )
    run = record["runs"][0]
    assert (run["path"], run["answerable_passed"], run["answerable_asked"]) == ("harness", 28, 29)
    assert (run["known_failures"], run["unexpected_failures"]) == (["q06"], [])


# --- 5절: 비용 상한 안의 반복 재생 -----------------------------------------------------------

_STACK, _API, _WS = "http://127.0.0.1:54621", "http://127.0.0.1:8031", "ws-1"


def _sse(*events: tuple[str, dict[str, Any]]) -> bytes:
    return "".join(
        f"event: {name}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        for name, payload in events
    ).encode("utf-8")


def _mock(monkeypatch: pytest.MonkeyPatch, asked: list[str], turn_cost: int = 10) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        table = path.removeprefix("/rest/v1/")
        if path == "/auth/v1/token":
            return httpx.Response(200, json={"access_token": "secret-token"})
        if path == "/health":
            return httpx.Response(200, json={"git_sha": "abc1234"})
        if table == "prompt_templates":
            return httpx.Response(200, json=[{"id": "p", "system_prompt": "s", "template": "t"}])
        if table in {"raw_sources", "source_chunks", "wiki_pages", "wiki_embeddings"}:
            return httpx.Response(200, json=[])
        if table == "ask_messages":
            return httpx.Response(
                200, json=[{"status": "resolved", "trace_id": "t1", "control_report": {}}]
            )
        if table == "usage_events":
            usage = {"prompt_tokens": 1, "completion_tokens": 1, "cost_micros": turn_cost}
            return httpx.Response(200, json=[{**usage, "model": "m/x"}])
        if path == f"/workspaces/{_WS}/ask":
            asked.append(json.loads(request.content)["query"])
            meta = {"policy_version": "hybrid-rrf-v2", "missing_channels": []}
            cited = {"resolved": [{"kind": "wiki"}, {"kind": "source"}]}
            body = _sse(("meta", meta), ("delta", {"text": "답"}), ("citations", cited))
            return httpx.Response(200, content=body)
        raise AssertionError(f"예상하지 못한 요청: {request.method} {path}")

    real_client = httpx.Client
    monkeypatch.setattr(
        rel.httpx, "Client", lambda *a, **k: real_client(transport=httpx.MockTransport(handler))
    )
    monkeypatch.setattr(replay.time, "sleep", lambda _s: None)


def _inputs(tmp_path: Path, api: str = _API) -> list[str]:
    sample = {
        "documents": [{"id": "a", "title": "A", "text": "."}],
        "questions": [
            {"id": "q01", "doc": "a", "query": "첫째", "expect_any": ["답"]},
            {"id": "q02", "doc": "a", "query": "둘째", "expect_any": ["답"]},
        ],
    }
    state = {
        "stack_url": _STACK,
        "workspace_id": _WS,
        "documents": ["a"],
        "email": "e@example.com",
        "credential": "secret-credential",
    }
    (tmp_path / "sample.json").write_text(json.dumps(sample), encoding="utf-8")
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return [
        "repeat",
        "--state",
        str(tmp_path / "state.json"),
        "--label",
        "rel",
        "--out-dir",
        str(tmp_path / "runs"),
        "--api-url",
        api,
        "--sample",
        str(tmp_path / "sample.json"),
        "--turn-estimate-micros",
        "10",
    ]


def _forbid_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_a: Any, **_k: Any) -> None:
        raise AssertionError("요청하면 안 된다")

    monkeypatch.setattr(rel.httpx, "Client", refuse)


def test_repeat_without_a_cap_refuses_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _forbid_network(monkeypatch)
    with pytest.raises(SystemExit):
        rel.build_parser().parse_args(_inputs(tmp_path) + ["--runs", "3"])


def test_repeat_refuses_a_non_loopback_api_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _forbid_network(monkeypatch)
    argv = _inputs(tmp_path, api="https://api.example.com")
    args = rel.build_parser().parse_args(argv + ["--runs", "1", "--max-total-spend-micros", "100"])
    with pytest.raises(SystemExit, match="루프백"):
        args.func(args)


def test_cap_reached_in_the_second_run_stops_before_the_next_question(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    asked: list[str] = []
    _mock(monkeypatch, asked)
    # 회차당 2문항 × 10 micros. 1회차 20, 2회차 첫 문항 30.
    # 다음 문항은 30 + 10 > 35라 시작하지 않는다.
    argv = _inputs(tmp_path) + ["--runs", "3", "--max-total-spend-micros", "35"]
    args = rel.build_parser().parse_args(argv)
    assert args.func(args) == 1
    manifest = json.loads((tmp_path / "runs" / "repeat.json").read_text(encoding="utf-8"))
    assert [(r["status"], r["reason"]) for r in manifest["runs"]] == [
        ("complete", None),
        ("partial", "spend_cap"),
        ("not_run", "spend_cap"),
    ]
    assert manifest["spent_micros"] == 30 <= manifest["cap_micros"]
    assert asked == ["첫째", "둘째", "첫째"]
    second = json.loads((tmp_path / "runs" / "rel-2.json").read_text(encoding="utf-8"))
    assert second["stopped"] == {"reason": "spend_cap", "asked": 1}


def test_two_complete_runs_add_two_scorecard_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock(monkeypatch, [])
    scorecard = tmp_path / "runs" / "scorecard.jsonl"
    scorecard.parent.mkdir()
    scorecard.write_text('{"label": "earlier"}\n', encoding="utf-8")
    argv = _inputs(tmp_path) + ["--runs", "2", "--max-total-spend-micros", "1000"]
    args = rel.build_parser().parse_args(argv)
    assert args.func(args) == 0
    lines = scorecard.read_text(encoding="utf-8").splitlines()
    assert lines[0] == '{"label": "earlier"}'
    assert [json.loads(line)["label"] for line in lines[1:]] == ["rel-1", "rel-2"]
    manifest = json.loads((tmp_path / "runs" / "repeat.json").read_text(encoding="utf-8"))
    assert [r["status"] for r in manifest["runs"]] == ["complete", "complete"]


def test_repeat_refuses_to_overwrite_existing_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _forbid_network(monkeypatch)
    (tmp_path / "runs").mkdir()
    (tmp_path / "runs" / "rel-1.json").write_text("keep", encoding="utf-8")
    argv = _inputs(tmp_path) + ["--runs", "2", "--max-total-spend-micros", "1000"]
    args = rel.build_parser().parse_args(argv)
    with pytest.raises(SystemExit, match="덮어쓰지 않는다"):
        args.func(args)


def test_repeat_manifest_feeds_the_report_with_not_run_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _mock(monkeypatch, [])
    argv = _inputs(tmp_path) + ["--runs", "3", "--max-total-spend-micros", "35"]
    args = rel.build_parser().parse_args(argv)
    args.func(args)
    labels = _labels_file(tmp_path, _entry(id="q01", known_failure=False, cause="other"))
    report_args = rel.build_parser().parse_args(
        _report_args(
            tmp_path,
            "--repeat",
            str(tmp_path / "runs" / "repeat.json"),
            "--labels",
            str(labels),
            "--sample",
            str(tmp_path / "sample.json"),
        )
    )
    report_args.func(report_args)
    record = json.loads((tmp_path / "rel.json").read_text(encoding="utf-8"))
    assert [r["label"] for r in record["runs"]] == ["rel-1", "rel-2"]
    assert record["not_run"] == [{"label": "rel-3", "reason": "spend_cap"}]
    q02 = next(q for q in record["questions"] if q["id"] == "q02")
    assert q02["outcomes"] == ["pass", "not_run"]


# --- 리뷰 r1 지적 ---------------------------------------------------------------------------


def test_harness_rows_not_run_by_the_cap_are_not_failures() -> None:
    rows = [_row("q01"), _row("q02", status="not_run", keyword_hit=None)]
    run = rel.ablation_run(_ablation(rows), "answer.json")
    assert [r["id"] for r in run["rows"]] == ["q01"]
    assert run["planned"] == 2
    report = _report([run], fixture_ids=["q01", "q02"])
    q02 = next(q for q in report["questions"] if q["id"] == "q02")
    assert q02["outcomes"] == ["not_run"]
    assert report["runs"][0]["answerable_asked"] == 1


def test_questions_no_run_reached_still_appear_as_not_run() -> None:
    fixture = [f"q{i:02d}" for i in range(1, 31)]
    rows = [_row(qid) for qid in fixture[:20]]
    stopped = {"reason": "spend_cap", "asked": 20}
    runs = _http(
        _result("r1", rows, planned=30, stopped=stopped),
        _result("r2", rows, planned=30, stopped=stopped),
    )
    report = _report(runs, fixture_ids=fixture)
    assert [q["id"] for q in report["questions"]] == fixture
    late = report["questions"][-1]
    assert (late["outcomes"], late["stability"]) == (["not_run", "not_run"], "not_run")
    assert report["stability_counts"]["not_run"] == 10


def test_unseeded_fixture_questions_are_not_padded_beyond_the_plan() -> None:
    runs = _http(_result("r1", [_row("q01"), _row("q02")]))
    report = _report(runs, fixture_ids=["q01", "q02", "q03"])
    assert [q["id"] for q in report["questions"]] == ["q01", "q02"]


def test_harness_failed_channel_is_an_execution_failure() -> None:
    row = _row("q01", ok=False, failed_channels=["wiki_vector"])
    row.pop("missing_channels")
    assert _stage(row, [_retrieval({"q01": None})]) == "execution_failure"


def test_series_counts_known_and_unexpected_failures() -> None:
    report = _report(
        _http(
            _result("r1", [_row("q06", ok=False), _row("q02", ok=False)]),
            _result("r2", [_row("q06", ok=False), _row("q02")]),
            _result("r3", [_row("q06"), _row("q02")]),
        ),
        labels=_Q06_LABEL,
    )
    failures = report["series_failures"]
    assert (failures["known_failure_count"], failures["unexpected_failure_count"]) == (2, 1)
    assert failures["known_failure_questions"] == ["q06"]
    assert failures["unexpected_failure_questions"] == ["q02"]
    assert failures["known_failures_passed"] == ["q06"]
    assert "묶음 전체 실패: 알려진 실패 2회 (q06) · 예상 밖 실패 1회 (q02)" in rel.render_markdown(
        report
    )


def test_repeat_refuses_a_non_loopback_database_before_any_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _forbid_network(monkeypatch)
    argv = _inputs(tmp_path) + ["--runs", "1", "--max-total-spend-micros", "100"]
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    state["stack_url"] = "https://abc.supabase.co"
    (tmp_path / "state.json").write_text(json.dumps(state), encoding="utf-8")
    args = rel.build_parser().parse_args(argv)
    with pytest.raises(SystemExit, match="루프백"):
        args.func(args)


def test_run_without_observed_policy_is_refused_from_the_series() -> None:
    run = _result("r1", [_row("q01")], policy_versions="unknown")
    with pytest.raises(SystemExit, match="policy_version"):
        _report(_http(run))


# --- 리뷰 r2 지적: 계획 문항 id ----------------------------------------------------------------


def test_planned_ids_report_the_right_unasked_questions_for_a_partial_seed() -> None:
    """일부 문서만 수집하면 계획이 fixture 앞부분과 다르다. 개수로 채우면 엉뚱한 문항이 나온다."""
    fixture = [f"q{i:02d}" for i in range(1, 31)]
    plan = ["q01", "q02", "q05", "q27", "q28", "q30"]
    rows = [_row(qid) for qid in plan[:3]]
    stopped = {"reason": "spend_cap", "asked": 3}
    results = []
    for label in ("r1", "r2"):
        result = _result(label, rows, planned=len(plan), stopped=stopped)
        result["planned_question_ids"] = plan
        results.append(result)
    report = _report(_http(*results), fixture_ids=fixture)
    assert [q["id"] for q in report["questions"]] == plan
    assert [q["id"] for q in report["questions"] if q["stability"] == "not_run"] == [
        "q27",
        "q28",
        "q30",
    ]


def test_build_result_records_the_planned_question_ids() -> None:
    questions = [{"id": "q01"}, {"id": "q30"}]
    result = replay.build_result(
        label="t", sha=None, questions=questions, rows=[], fixed={}, stopped="spend_cap"
    )
    assert result["planned_question_ids"] == ["q01", "q30"]
