"""`scripts/retrieval_ablation.py`의 순수 로직과 안전장치 검사.

이 실험 수치는 "위키가 답변에 도움이 되는가"의 근거로 인용된다. 장애를 미적중으로 세거나
단일 근거 조건을 이중 인용 실패로 세면 결론이 조용히 뒤집히므로, 네트워크 없이 그 판정을 고정한다.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import uuid4

import pytest

from api.services.retrieval import RetrievalService

_ROOT = Path(__file__).resolve().parents[3]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "retrieval_ablation", _ROOT / "scripts" / "retrieval_ablation.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ablation = _load()

GOLD = "raw-gold"
OTHER = "raw-other"
WIKI_SOURCES = {"wiki-gold": {GOLD}, "wiki-other": {OTHER}}
CHUNK_SOURCES = {"chunk-gold": GOLD, "chunk-other": OTHER}
QUESTIONS = [
    {"id": "q01", "doc": "delivery", "query": "당일배송 마감은?"},
    {"id": "q30", "doc": "none", "query": "없는 회사 영업이익은?"},
]
EXPECTED = {"q01": {GOLD}, "q30": set()}


def _rows(function: str) -> list[dict[str, object]]:
    if function == "search_chunks":
        return [{"id": "chunk-gold", "raw_source_id": GOLD, "chunk_index": 0}]
    if function == "search_source_lexical":
        return [{"id": "chunk-other", "raw_source_id": OTHER, "chunk_index": 1}]
    if function == "search_wiki_embeddings":
        return [{"id": "emb-1", "wiki_id": "wiki-gold", "chunk_index": 0}]
    if function == "search_wiki_lexical":
        return [{"id": "wiki-other", "slug": "other", "title": "Other"}]
    raise AssertionError(function)


class FakeDb:
    def __init__(self, failing: set[str] | None = None) -> None:
        self.calls: list[str] = []
        self.failing = failing or set()

    async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict[str, object]]:
        self.calls.append(function)
        if function in self.failing:
            raise RuntimeError("down")
        return _rows(function)


def _query_vectors(*, vector: list[float] | None = None) -> dict[str, Any]:
    vec = [0.0] * 1024 if vector is None else vector
    return {
        "schema": ablation.QUERY_VECTORS_SCHEMA,
        "vectors": {
            q["id"]: {
                "normalized": ablation.normalize(q["query"]),
                "vector": vec,
                "error": None,
            }
            for q in QUESTIONS
        },
    }


def _retrieve_with(db: FakeDb, query_vectors: dict[str, Any] | None = None):
    embedder = ablation.FixedQueryEmbeddingClient(query_vectors or _query_vectors())

    async def retrieve(scope: str, embedding_input: str, query: str):
        service = RetrievalService(embedder, policy=ablation.scope_policy(scope))
        result = await service.retrieve(uuid4(), query, ablation.REQUESTED_K, db)
        return [ablation._evidence_json(hit) for hit in result.evidence], result.meta

    return retrieve


def _evaluate(scope: str, db: FakeDb, **kwargs: Any) -> dict[str, Any]:
    return asyncio.run(
        ablation.evaluate_condition(
            scope=scope,
            embedding_input="body",
            questions=kwargs.get("questions", QUESTIONS),
            expected_by_question=kwargs.get("expected", EXPECTED),
            retrieve=kwargs.get("retrieve") or _retrieve_with(db),
            wiki_sources=WIKI_SOURCES,
            chunk_sources=CHUNK_SOURCES,
        )
    )


def test_scopes_map_to_exact_channel_sets() -> None:
    assert ablation.scope_policy("source_only").enabled_channels == {
        "source_vector",
        "source_lexical",
    }
    assert ablation.scope_policy("wiki_only").enabled_channels == {"wiki_vector", "wiki_lexical"}
    assert len(ablation.scope_policy("both").enabled_channels) == 4
    with pytest.raises(ValueError):
        ablation.scope_policy("graph_only")


def test_wiki_only_ranks_only_wiki_and_marks_source_disabled_not_failed() -> None:
    db = FakeDb()
    condition = _evaluate("wiki_only", db)

    assert sorted(set(db.calls)) == ["search_wiki_embeddings", "search_wiki_lexical"]
    row = condition["rows"][0]
    assert {item["kind"] for item in row["result"]["ranked"]} == {"wiki"}
    # 그래프는 모든 조건에서 운영 기본값(꺼짐)으로 고정이라 함께 나온다(설계 D3).
    assert row["disabled_channels"] == ["graph", "source_lexical", "source_vector"]
    assert row["failed_channels"] == []
    assert row["classification"] == "hit"
    assert condition["diagnostic"] is True


def test_single_scope_dual_hit_is_intended_not_a_failure() -> None:
    condition = _evaluate("source_only", FakeDb())

    result = condition["rows"][0]["result"]
    assert result["dual_hit"] is None
    assert result["dual_hit_note"] == "intended_single_evidence"
    assert condition["summary"]["dual_hit_at_8"] is None


def test_both_scope_keeps_dual_hit_and_is_not_diagnostic() -> None:
    condition = _evaluate("both", FakeDb())

    assert condition["diagnostic"] is False
    assert condition["rows"][0]["result"]["dual_hit"] is True
    assert condition["summary"]["dual_hit_at_8"] == 1.0


def test_channel_failure_is_execution_failure_not_retrieval_miss() -> None:
    condition = _evaluate("both", FakeDb(failing={"search_chunks", "search_wiki_embeddings"}))

    row = condition["rows"][0]
    assert row["failed_channels"] == ["source_vector", "wiki_vector"]
    assert row["classification"] == "execution_failure"


def test_missing_query_vector_fails_vector_channels_only() -> None:
    vectors = _query_vectors()
    vectors["vectors"]["q01"]["vector"] = None
    condition = _evaluate("both", FakeDb(), retrieve=_retrieve_with(FakeDb(), vectors))

    row = condition["rows"][0]
    assert row["failed_channels"] == ["source_vector", "wiki_vector"]
    assert row["classification"] == "execution_failure"


def test_gold_absent_with_healthy_channels_is_retrieval_miss() -> None:
    condition = _evaluate("both", FakeDb(), expected={"q01": {"raw-elsewhere"}, "q30": set()})

    assert condition["rows"][0]["classification"] == "retrieval_miss"


def test_unmapped_gold_document_is_measurement_failure_without_retrieval() -> None:
    db = FakeDb()
    condition = _evaluate("both", db, expected={"q01": None, "q30": set()})

    assert condition["rows"][0]["classification"] == "measurement_failure"
    assert condition["rows"][1]["classification"] == "unanswerable"
    # 정답 문서를 모르는 질문은 검색하지 않는다. 답할 수 없는 질문은 검색한다.
    assert len(db.calls) == 4


def _snapshot(**overrides: Any) -> dict[str, Any]:
    data = {
        "raw_sources": [{"id": GOLD, "title": "배송 정책"}],
        "source_chunks": [
            {
                "id": "chunk-gold",
                "raw_source_id": GOLD,
                "chunk_index": 0,
                "content": "본문",
                "char_start": 0,
                "char_end": 2,
                "embedding_version": "m@p-v1",
            }
        ],
        "wiki_pages": [{"id": "wiki-gold", "title": "배송", "content": "위키", "sources": [GOLD]}],
        "wiki_chunks": [
            {
                "wiki_id": "wiki-gold",
                "chunk_index": 0,
                "chunk_content": "위키",
                "embedding_version": "m@p-v1",
            }
        ],
    }
    data.update(overrides)
    return ablation.snapshot_inputs(**data)


def test_snapshot_hash_changes_when_only_a_title_changes() -> None:
    base = _snapshot()
    renamed = _snapshot(raw_sources=[{"id": GOLD, "title": "배송 정책 v2"}])

    assert base["snapshot_sha256"] != renamed["snapshot_sha256"]
    assert base["chunk_boundaries_sha256"] == renamed["chunk_boundaries_sha256"]
    assert base["embedding_versions"] == ["m@p-v1"]


def test_fixed_inputs_are_deterministic_and_track_query_vectors() -> None:
    sample = {"documents": [], "questions": QUESTIONS}
    first = ablation.fixed_inputs(
        snapshot=_snapshot(), sample=sample, query_vectors=_query_vectors()
    )
    again = ablation.fixed_inputs(
        snapshot=_snapshot(), sample=sample, query_vectors=_query_vectors()
    )
    other = ablation.fixed_inputs(
        snapshot=_snapshot(), sample=sample, query_vectors=_query_vectors(vector=[1.0] * 1024)
    )

    assert first == again
    assert first["query_vectors_sha256"] != other["query_vectors_sha256"]
    assert first["policy_version"] == "hybrid-rrf-v2"
    assert first["graph_enabled"] is False


def test_build_query_vectors_records_failures_without_raising() -> None:
    async def embed(text: str) -> list[float]:
        if "없는" in text:
            raise RuntimeError("provider down")
        return [0.5] * 1024

    built = asyncio.run(ablation.build_query_vectors(QUESTIONS, embed))

    assert built["vectors"]["q01"]["vector"] == [0.5] * 1024
    assert built["vectors"]["q30"] == {
        "normalized": ablation.normalize(QUESTIONS[1]["query"]),
        "vector": None,
        "error": "RuntimeError",
    }


def test_record_is_append_only_and_marked_as_its_own_experiment(tmp_path: Path) -> None:
    record = ablation.build_record(
        label="t",
        git_sha=None,
        fixed={"snapshot_sha256": "x"},
        snapshot_counts={},
        conditions=[_evaluate("both", FakeDb())],
    )
    path = tmp_path / "r.json"
    ablation.write_record(path, record)

    assert json.loads(path.read_text())["experiment"] == "retrieval-evidence-ablation"
    with pytest.raises(FileExistsError):
        ablation.write_record(path, record)


def test_retrieve_refuses_existing_output_before_any_request(tmp_path: Path) -> None:
    out = tmp_path / "exists.json"
    out.write_text("{}")

    with pytest.raises(SystemExit, match="덮어쓰지 않는다"):
        ablation.main(
            [
                "retrieve",
                "--state",
                str(tmp_path / "missing.json"),
                "--query-vectors",
                "q",
                "--out",
                str(out),
            ]
        )


def test_retrieve_refuses_non_loopback_stack_before_any_request(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"stack_url": "https://example.supabase.co", "documents": []}))

    with pytest.raises(SystemExit, match="루프백"):
        ablation.main(
            [
                "retrieve",
                "--state",
                str(state),
                "--query-vectors",
                str(tmp_path / "q.json"),
                "--out",
                str(tmp_path / "out.json"),
            ]
        )
    assert not (tmp_path / "out.json").exists()


def test_retrieve_refuses_non_loopback_worker(tmp_path: Path) -> None:
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"stack_url": "http://127.0.0.1:54621", "documents": []}))

    with pytest.raises(SystemExit, match="루프백"):
        ablation.main(
            [
                "retrieve",
                "--state",
                str(state),
                "--query-vectors",
                str(tmp_path / "q.json"),
                "--out",
                str(tmp_path / "out.json"),
                "--worker-url",
                "https://worker.example.com",
            ]
        )


# --- slice 2: 제목 머리말 벡터 · 동등성 · 비교 ---------------------------------


def test_title_body_text_prefixes_only_the_embedding_input() -> None:
    assert ablation.embedding_text("title_body", title="배송 정책", body="본문") == (
        "문서: 배송 정책\n본문"
    )
    assert ablation.embedding_text("body", title="배송 정책", body="본문") == "본문"
    with pytest.raises(ValueError, match="title_missing"):
        ablation.embedding_text("title_body", title="  ", body="본문")


def _corpus(title: str = "배송 정책") -> dict[str, list[dict[str, Any]]]:
    return {
        "raw_sources": [{"id": GOLD, "title": title}],
        "source_chunks": [{"id": "chunk-gold", "raw_source_id": GOLD, "content": "본문"}],
        "wiki_pages": [{"id": "wiki-gold", "title": ""}],
        "wiki_chunks": [{"id": "emb-1", "wiki_id": "wiki-gold", "chunk_content": "위키"}],
    }


def test_vector_items_fail_untitled_chunks_instead_of_falling_back_to_body() -> None:
    items, failures = ablation.vector_items("title_body", **_corpus())

    assert [i["chunk_ref"] for i in items] == ["chunk-gold"]
    assert items[0]["text"] == "문서: 배송 정책\n본문"
    assert failures == [{"kind": "wiki", "chunk_ref": "emb-1", "reason": "title_missing"}]


class FakeLocalDb:
    def __init__(self, existing: set[tuple[str, str, str]] | None = None) -> None:
        self.existing = existing or set()
        self.inserted: list[tuple[str, str, str]] = []
        self.sql: list[str] = []

    def json(self, sql: str) -> Any:
        self.sql.append(sql)
        if "json_build_array(kind, chunk_ref, text_sha256" in sql:
            return [[*k, 0] for k in self.existing]
        return [{"id": "chunk-gold", "raw_source_id": GOLD, "chunk_index": 0, "distance": 0.1}]

    def run(self, sql: str) -> str:
        self.sql.append(sql)
        return ""


def _budget(cap: int | None = 1000, *, cost_per_call: int = 1, fail_first: int = 0):
    state = {"usage": 0, "calls": 0}

    async def embed(text: str) -> list[float]:
        state["calls"] += 1
        if state["calls"] <= fail_first:
            raise RuntimeError("rate_limited")
        state["usage"] += cost_per_call
        return [0.1] * 1024

    async def no_sleep(_: float) -> None:
        return None

    return (
        ablation.EmbedBudget(
            cap_micros=cap, embed=embed, usage_total=lambda: state["usage"], sleep=no_sleep
        ),
        state,
    )


def _prepare(db: FakeLocalDb, items: list[dict[str, str]], budget: Any) -> dict[str, Any]:
    original = ablation.insert_vectors

    def record(db_: Any, **kwargs: Any) -> None:
        db.inserted.extend((k, r, s) for k, r, s, *_ in kwargs["rows"])

    ablation.insert_vectors = record
    try:
        return asyncio.run(
            ablation.prepare_title_vectors(
                db, workspace=str(uuid4()), embedding_version="m@p-v1", items=items, budget=budget
            )
        )
    finally:
        ablation.insert_vectors = original


def test_title_vectors_reuse_only_exact_text_hash_matches() -> None:
    items, _ = ablation.vector_items("title_body", **_corpus())
    key = ("source", "chunk-gold", items[0]["text_sha256"])
    budget, state = _budget()

    reused = _prepare(FakeLocalDb(existing={key}), items, budget)
    assert reused["reused"] == 1 and reused["created"] == 0 and state["calls"] == 0

    renamed, _ = ablation.vector_items("title_body", **_corpus(title="배송 정책 v2"))
    db = FakeLocalDb(existing={key})
    created = _prepare(db, renamed, budget)
    # 본문은 같고 제목만 바뀌었으므로 새 벡터를 만든다.
    assert created["created"] == 1 and state["calls"] == 1
    assert db.inserted[0][2] != key[2]


def test_budget_refuses_paid_call_without_cap() -> None:
    budget, _ = _budget(cap=None)

    with pytest.raises(SystemExit, match="embed-cap-micros"):
        asyncio.run(budget.embed("x"))


def test_budget_retries_rate_limit_without_counting_cost() -> None:
    budget, state = _budget(fail_first=2)

    asyncio.run(budget.embed("x"))
    assert state["calls"] == 3 and budget.calls == 1 and budget.spent_micros == 1


def test_cap_stops_preparation_and_marks_the_rest_not_run() -> None:
    items = [
        {"kind": "source", "chunk_ref": f"c{i}", "text": f"t{i}", "text_sha256": f"h{i}"}
        for i in range(5)
    ]
    budget, state = _budget(cap=3, cost_per_call=1)

    result = _prepare(FakeLocalDb(), items, budget)

    assert result["created"] == 3 and state["calls"] == 3
    assert [f["reason"] for f in result["failures"]] == ["not_run_cap", "not_run_cap"]
    assert result["stopped"]


def test_routing_db_sends_only_vector_channels_to_experiment_store() -> None:
    local = FakeLocalDb()
    user = FakeDb()
    routing = ablation.AblationRoutingDb(
        user, local, input_format="title_body-v1", embedding_version="m@p-v1"
    )
    params = {"p_workspace_id": str(uuid4()), "p_query": [0.0] * 1024, "p_k": 20}

    asyncio.run(routing.rpc("search_chunks", params=params))
    asyncio.run(routing.rpc("search_source_lexical", params={"p_k": 20}))

    assert user.calls == ["search_source_lexical"]
    assert "ablation.search_chunks(" in local.sql[0]
    assert "'title_body-v1'" in local.sql[0]


def test_equivalence_check_names_mismatched_question_and_function() -> None:
    class Product:
        async def rpc(self, function: str, *, params: dict[str, Any]) -> list[dict[str, Any]]:
            return [{"id": "a", "distance": 0.1}, {"id": "b", "distance": 0.2}]

    class Experiment:
        async def rpc(self, function: str, *, params: dict[str, Any]) -> list[dict[str, Any]]:
            rows = [{"id": "a", "distance": 0.1}, {"id": "b", "distance": 0.2}]
            return rows[::-1] if function == "search_wiki_embeddings" else rows

    result = asyncio.run(
        ablation.equivalence_check(
            workspace=str(uuid4()),
            query_vectors=_query_vectors(),
            product_db=Product(),
            experiment_db=Experiment(),
            limit=20,
        )
    )

    assert result["passed"] is False
    assert {"question": "q01", "function": "search_wiki_embeddings"} in result["mismatches"]
    assert all(m["function"] == "search_wiki_embeddings" for m in result["mismatches"])


def _condition(scope: str, embedding_input: str, classes: dict[str, str]) -> dict[str, Any]:
    return {
        "scope": scope,
        "embedding_input": embedding_input,
        "condition": f"{scope}x{embedding_input}",
        "diagnostic": scope != "both",
        "rows": [{"id": q, "classification": c} for q, c in classes.items()],
        "summary": {"hit_at_8": 0.5, "classification_counts": {}},
    }


def test_transitions_separate_recovery_regression_and_failures() -> None:
    conditions = [
        _condition("both", "body", {"q1": "retrieval_miss", "q2": "hit", "q3": "hit"}),
        _condition(
            "both", "title_body", {"q1": "hit", "q2": "retrieval_miss", "q3": "execution_failure"}
        ),
    ]

    [item] = ablation.transitions(conditions)
    assert item["comparison"] == "both: body -> title_body"
    assert item["recovered"] == ["q1"]
    assert item["regressed"] == ["q2"]
    assert item["excluded_failures"] == ["q3"]


def _record(fixed: dict[str, Any], *conditions: dict[str, Any], experiment: str | None = None):
    return {
        "experiment": experiment or ablation.EXPERIMENT,
        "fixed_inputs": fixed,
        "conditions": list(conditions),
    }


def test_compare_refuses_records_with_different_fixed_inputs_and_names_them() -> None:
    a = _record(
        {"query_vectors_sha256": "1", "snapshot_sha256": "s"}, _condition("both", "body", {})
    )
    b = _record(
        {"query_vectors_sha256": "2", "snapshot_sha256": "s"}, _condition("both", "title_body", {})
    )

    with pytest.raises(SystemExit, match="query_vectors_sha256"):
        ablation.compare_markdown([a, b])


def test_compare_refuses_other_experiments() -> None:
    a = _record({}, _condition("both", "body", {}))
    rerank = _record({}, _condition("both", "title_body", {}), experiment="rerank-off-on")

    with pytest.raises(SystemExit, match="다른 실험"):
        ablation.compare_markdown([a, rerank])


def test_compare_labels_diagnostic_conditions() -> None:
    record = _record(
        {},
        _condition("source_only", "body", {"q1": "hit"}),
        _condition("both", "body", {"q1": "hit"}),
    )

    table = ablation.compare_markdown([record])
    assert "source_onlyxbody (진단)" in table
    assert "bothxbody |" in table or "bothxbody " in table


# --- slice 3: 사전 등록 · 답변 재생 · 진단 판정 · 공개 필드 ----------------------


def _retrieval_record(created_at: str, conditions: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "experiment": ablation.EXPERIMENT,
        "phase": "retrieval",
        "created_at": created_at,
        "fixed_inputs": {"snapshot_sha256": "s"},
        "conditions": conditions,
        "limitations": ["합성"],
    }


def _registration(created_at: str, **overrides: Any) -> dict[str, Any]:
    registration = ablation.build_registration(cap_micros=3_000_000, turn_estimate_micros=60_000)
    registration["created_at"] = created_at
    registration.update(overrides)
    return registration


def test_registration_after_retrieval_is_refused() -> None:
    retrieval = _retrieval_record("2026-11-08T10:00:00+00:00", [])

    ablation.check_registration(_registration("2026-11-08T09:00:00+00:00"), retrieval)
    with pytest.raises(SystemExit, match="늦다"):
        ablation.check_registration(_registration("2026-11-08T11:00:00+00:00"), retrieval)


def test_registration_without_cap_or_with_edited_rule_is_refused() -> None:
    retrieval = _retrieval_record("2026-11-08T10:00:00+00:00", [])

    with pytest.raises(SystemExit, match="비용 상한"):
        ablation.check_registration(
            _registration("2026-11-08T09:00:00+00:00", answer_cap_micros=None), retrieval
        )
    tampered = _registration("2026-11-08T09:00:00+00:00")
    tampered["rule"] = {**tampered["rule"], "always": ["wiki_onlyxbody"]}
    with pytest.raises(SystemExit, match="규칙"):
        ablation.check_registration(tampered, retrieval)
    with pytest.raises(SystemExit):
        ablation.build_registration(cap_micros=0, turn_estimate_micros=1)


def _scored(scope: str, embedding_input: str, hit8: float, classes: dict[str, str]):
    condition = _condition(scope, embedding_input, classes)
    condition["summary"] = {"hit_at_8": hit8}
    return condition


def test_selection_rule_adds_title_condition_only_when_not_worse() -> None:
    base = {"q1": "hit", "q2": "hit", "q3": "retrieval_miss"}
    conditions = [
        _scored("source_only", "body", 0.6, base),
        _scored("both", "body", 0.66, base),
        _scored("both", "title_body", 0.66, {"q1": "hit", "q2": "retrieval_miss", "q3": "hit"}),
    ]

    selected, reasons = ablation.select_conditions(ablation.SELECTION_RULE, conditions)
    assert selected == ["source_onlyxbody", "bothxbody", "bothxtitle_body"]

    conditions[2] = _scored(
        "both", "title_body", 0.33, {"q1": "retrieval_miss", "q2": "retrieval_miss", "q3": "hit"}
    )
    selected, reasons = ablation.select_conditions(ablation.SELECTION_RULE, conditions)
    assert selected == ["source_onlyxbody", "bothxbody"]
    assert reasons["bothxtitle_body"].startswith("skipped")


def test_run_answers_stops_before_exceeding_cap_and_marks_rest_not_run() -> None:
    plan = [("bothxbody", "both", {"id": f"q{i}", "doc": "d"}) for i in range(5)]
    called: list[str] = []

    async def run_turn(name: str, scope: str, question: dict[str, Any]) -> dict[str, Any]:
        called.append(question["id"])
        return {"id": question["id"], "doc": "d", "status": "resolved", "cost_micros": 30}

    rows, spent, stopped = asyncio.run(
        ablation.run_answers(plan=plan, run_turn=run_turn, cap_micros=100, turn_estimate_micros=30)
    )

    assert called == ["q0", "q1", "q2"] and spent == 90
    assert [r["status"] for r in rows] == ["resolved"] * 3 + ["not_run"] * 2
    assert stopped and "100" in stopped


def _answer(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": "q01",
        "doc": "delivery",
        "status": "resolved",
        "fabricated_anchor_count": 0,
        "keyword_hit": True,
        "cited_wiki_count": 0,
        "cited_source_count": 2,
        "answer": "오후 2시입니다.",
        "cost_micros": 10,
    }
    row.update(overrides)
    return row


def test_single_scope_answer_is_judged_on_fact_not_dual_citation() -> None:
    verdict = ablation.answer_verdict(_answer(), "source_only")

    assert verdict["pass"] is True
    assert verdict["classification"] == "fact_included"
    assert verdict["dual_citation_note"] == "intended_single_evidence"


def test_both_scope_answer_keeps_product_dual_citation_rule() -> None:
    verdict = ablation.answer_verdict(_answer(), "both")

    assert verdict["pass"] is False
    assert "인용" in verdict["reason"]


def test_answer_failures_are_classified() -> None:
    assert ablation.answer_verdict(_answer(status="error"), "both")["classification"] == (
        "execution_failure"
    )
    assert ablation.answer_verdict(_answer(keyword_hit=False), "wiki_only")["classification"] == (
        "fact_missing"
    )
    refusal = _answer(doc="none", answer="제공된 자료로는 알 수 없습니다.")
    assert ablation.answer_verdict(refusal, "source_only")["classification"] == "refusal_correct"
    assert ablation.answer_verdict(_answer(status="not_run"), "both")["classification"] == (
        "not_run_cap"
    )


def _answer_record() -> dict[str, Any]:
    retrieval = _retrieval_record(
        "2026-11-08T10:00:00+00:00",
        [
            _scored("source_only", "body", 1.0, {"q01": "hit"}),
            _scored("both", "body", 1.0, {"q01": "hit"}),
        ],
    )
    rows = [
        {"condition": "source_onlyxbody", **_answer()},
        {"condition": "bothxbody", **_answer(cited_wiki_count=1)},
    ]
    return ablation.build_answer_record(
        label="t",
        git_sha=None,
        retrieval=retrieval,
        registration=_registration("2026-11-08T09:00:00+00:00"),
        selected=["source_onlyxbody", "bothxbody"],
        reasons={"source_onlyxbody": "always", "bothxbody": "always"},
        prompt_sha256="p",
        rows=rows,
        spent=20,
        stopped=None,
    )


def test_answer_record_labels_diagnostic_and_reports_rules() -> None:
    record = _answer_record()
    by = {c["condition"]: c for c in record["conditions"]}

    assert by["source_onlyxbody"]["diagnostic"] is True
    assert by["source_onlyxbody"]["summary"]["verdict_rule"] == "diagnostic_fact_only"
    assert by["bothxbody"]["summary"]["verdict_rule"] == "product_dual_citation"
    assert by["bothxbody"]["rows"][0]["retrieval_classification"] == "hit"
    assert record["fixed_inputs"] == {"snapshot_sha256": "s"}


def test_publishable_excludes_text_and_identifiers() -> None:
    record = _answer_record()
    record["workspace_id"] = "ws-secret"
    published = json.dumps(record["publishable"], ensure_ascii=False)

    assert "오후 2시" not in published
    assert "ws-secret" not in published
    assert "당일배송" not in published
    assert record["publishable"]["experiment"] == ablation.EXPERIMENT
    assert record["publishable"]["conditions"][0]["questions"]["q01"]["fact_included"] is True


def test_retrieval_record_carries_publishable_without_query_text() -> None:
    record = ablation.build_record(
        label="t",
        git_sha=None,
        fixed={},
        snapshot_counts={},
        conditions=[_evaluate("both", FakeDb())],
    )
    published = json.dumps(record["publishable"], ensure_ascii=False)

    assert "당일배송" not in published and "chunk-gold" not in published
    assert record["publishable"]["conditions"][0]["questions"]["q01"]["first_relevant_rank"] == 1


def test_compare_shows_answer_table_with_rule_labels() -> None:
    record = _answer_record()
    table = ablation.compare_markdown([record])

    assert "답변 재생" in table
    # 진단 통과율과 제품 통과율은 다른 행이다. 해당하지 않는 칸은 비어 있다.
    product = next(line for line in table.splitlines() if line.startswith("| 제품 통과율"))
    diagnostic = next(line for line in table.splitlines() if line.startswith("| 진단 통과율"))
    assert product.split("|")[2].strip() == "-"  # source_only
    assert diagnostic.split("|")[3].strip() == "-"  # both


def test_turn_row_reads_ask_events_like_the_replay_script() -> None:
    events = [
        ("delta", {"text": "오후 2시 "}),
        ("delta", {"text": "입니다 [S1]"}),
        (
            "citations",
            {
                "fabricated_anchor_count": 0,
                "cited_anchor_count": 1,
                "resolved": [{"kind": "source"}],
                "dual_citation_rate": 0.0,
            },
        ),
    ]
    question = {"id": "q01", "doc": "delivery", "expect_any": ["오후2시"]}
    row = ablation.turn_row(
        question, events, {"status": "resolved"}, [{"cost_micros": 5, "model": "m"}], 10
    )

    assert row["status"] == "resolved" and row["cost_micros"] == 5
    assert row["cited_source_count"] == 1 and row["cited_wiki_count"] == 0
    assert row["keyword_hit"] is True


def test_query_vectors_with_failures_are_never_fixed(tmp_path: Path) -> None:
    vectors = _query_vectors()
    vectors["vectors"]["q30"] = {"normalized": "x", "vector": None, "error": "RuntimeError"}
    path = tmp_path / "q.json"
    path.write_text(json.dumps(vectors))

    assert ablation.failed_query_vectors(vectors) == [{"id": "q30", "error": "RuntimeError"}]
    with pytest.raises(SystemExit, match="실패한 질문"):
        ablation.load_query_vectors(path, QUESTIONS)


def test_local_db_parses_multiline_json_agg_output() -> None:
    class Done:
        returncode = 0
        stdout = '[{"id": "a", "distance": 0.1}, \n {"id": "b", "distance": 0.2}]\n'
        stderr = ""

    db = ablation.LocalDb("c", runner=lambda *a, **k: Done())
    assert [r["id"] for r in db.json("select 1;")] == ["a", "b"]


# --- 리뷰 r1 지적 사항 -----------------------------------------------------------


def test_answer_turn_with_failed_channel_is_execution_failure() -> None:
    events = [
        ("meta", {"thread_id": "t", "missing_channels": ["wiki_vector"]}),
        ("delta", {"text": "오후 2시"}),
        ("citations", {"fabricated_anchor_count": 0, "resolved": [{"kind": "source"}]}),
    ]
    row = ablation.turn_row(
        {"id": "q01", "doc": "delivery", "expect_any": ["오후2시"]},
        events,
        {"status": "resolved"},
        [],
        1,
    )

    assert row["failed_channels"] == ["wiki_vector"]
    verdict = ablation.answer_verdict(row, "both")
    assert verdict["classification"] == "execution_failure" and verdict["pass"] is False


def test_answer_records_with_different_prompts_are_not_merged() -> None:
    a = _answer_record()
    b = _answer_record()
    b["answer_prompt_sha256"] = "other"
    for c in b["conditions"]:
        c["condition"] = c["condition"] + "-b"

    with pytest.raises(SystemExit, match="answer_prompt_sha256"):
        ablation.compare_markdown([a, b])


def test_answer_summary_separates_product_and_diagnostic_pass_rates() -> None:
    by = {c["condition"]: c["summary"] for c in _answer_record()["conditions"]}

    assert by["source_onlyxbody"]["diagnostic_pass_rate"] == 1.0
    assert by["source_onlyxbody"]["product_pass_rate"] is None
    assert by["bothxbody"]["product_pass_rate"] == 1.0
    assert by["bothxbody"]["diagnostic_pass_rate"] is None
    assert _answer_record()["conditions"][0]["enabled_channels"] == [
        "source_lexical",
        "source_vector",
    ]


def test_retrieval_rows_record_succeeded_channels() -> None:
    row = _evaluate("wiki_only", FakeDb())["rows"][0]

    assert row["succeeded_channels"] == ["wiki_lexical", "wiki_vector"]


# --- 리뷰 r2 지적 사항 -----------------------------------------------------------


def test_publishable_never_mixes_product_and_diagnostic_pass_rates() -> None:
    published = _answer_record()["publishable"]

    for condition in published["conditions"]:
        assert "pass_rate" not in condition["summary"]
    by = {c["condition"]: c["summary"] for c in published["conditions"]}
    assert by["source_onlyxbody"]["product_pass_rate"] is None
    assert by["bothxbody"]["diagnostic_pass_rate"] is None


def test_publishable_cost_keeps_partial_scope_markers() -> None:
    record = ablation.build_record(
        label="t",
        git_sha=None,
        fixed={},
        snapshot_counts={},
        conditions=[_evaluate("both", FakeDb())],
        cost={
            "embedding_micros": 3,
            "embedding_scope": "this_run_only",
            "reused_query_vectors": True,
            "reused_query_vectors_micros": 60,
            "reused_title_vectors": 35,
            "reused_title_vectors_micros": 70,
        },
    )

    cost = record["publishable"]["cost"]
    assert cost["embedding_scope"] == "this_run_only"
    assert cost["reused_title_vectors_micros"] == 70 and cost["reused_query_vectors_micros"] == 60


def test_title_vector_cost_is_stored_and_reported_when_reused() -> None:
    items, _ = ablation.vector_items("title_body", **_corpus())
    key = ("source", "chunk-gold", items[0]["text_sha256"])
    budget, _ = _budget(cost_per_call=7)

    db = FakeLocalDb()
    created = _prepare(db, items, budget)
    assert created["created_micros"] == 7

    class CostedDb(FakeLocalDb):
        def json(self, sql: str) -> Any:
            if "json_build_array(kind, chunk_ref, text_sha256, cost_micros)" in sql:
                return [[*key, 7]]
            return super().json(sql)

    reused = _prepare(CostedDb(), items, budget)
    assert reused["reused"] == 1 and reused["reused_micros"] == 7 and reused["created"] == 0


def test_answer_rows_record_succeeded_channels() -> None:
    record = _answer_record()
    row = record["conditions"][1]["rows"][0]

    assert row["succeeded_channels"] == sorted(ablation.SCOPES["both"])
