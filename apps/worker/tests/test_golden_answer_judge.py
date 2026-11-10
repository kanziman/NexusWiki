"""#266: 실제 유료 호출이나 사람 판정 생성 없이 평가 체계의 계약을 검사한다."""

import json
import sys
import threading
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import golden_answer_judge as judge  # noqa: E402


@pytest.fixture
def store(tmp_path):
    parent = SimpleNamespace(root=tmp_path, guard=threading.Lock(), max_budget=2_000_000)
    return judge.JudgeStore(parent)


def response(packet, cost=10):
    anchor, quote = next(iter(packet["reference_evidence"].items()))
    supplied = packet["supplied_evidence"] or {}
    cite = next(iter(supplied), anchor)
    metrics = {
        m: {
            "verdict": "pass",
            "reason": "테스트 판정",
            "answer_quote": packet["answer"],
            "evidence": [
                {
                    "anchor": cite if m == "citation_accuracy" else anchor,
                    "quote": supplied.get(cite, quote)[:30],
                }
            ],
        }
        for m in judge.METRICS
    }
    return {
        "content": json.dumps({"metrics": metrics}),
        "cost_micros": cost,
        "served_model": "test/model",
    }


def job():
    return {
        "id": "test-job",
        "created_at": "2026-11-10",
        "status": "queued",
        "model": "test/model",
        "model_config": {
            "input_usd_per_million": "1",
            "output_usd_per_million": "1",
            "max_output_tokens": 500,
        },
        "budget_micros": 1_000_000,
        "spent_micros": 0,
        "unknown_cost": False,
        "planned": 2,
        "asked": 0,
        "rows": [],
        "error": None,
        "prompt_fingerprint": judge.digest(judge.SYSTEM),
    }


def test_candidates_are_unreviewed_and_refs_are_bound(store, tmp_path):
    data = store.snapshot()
    assert len(data["dataset"]["questions"]) == 30
    assert data["reviews"] == {}
    assert all(q["review_status"] == "unreviewed" for q in data["dataset"]["questions"])
    assert "일반 상품" in data["dataset"]["questions"][5]["query"]
    for stats in data["agreement"]["synthetic"].values():
        assert stats["agreement"] is None and stats["paired"] == 0
    changed = judge.read(ROOT / "scripts/fixtures/golden_answers.v1.json")
    changed["documents"][0]["text"] += "변경"
    changed["documents"][0]["text"] = "오류" + changed["documents"][0]["text"][2:]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(changed))
    with pytest.raises(ValueError, match="근거"):
        judge.load_dataset(path)


def test_reference_offsets_are_validated(tmp_path):
    data = judge.read(ROOT / "scripts/fixtures/golden_answers.v1.json")
    data["questions"][0]["evidence"][0]["end"] = 999999
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="구간"):
        judge.load_dataset(path)


def test_citation_validity_does_not_claim_semantic_accuracy(store):
    samples = {s["question_id"]: s for s in store.samples()}
    assert samples["g27"]["citation_validity"]["verdict"] == "fail"
    assert samples["g28"]["citation_validity"]["verdict"] == "pass"
    assert samples["g29"]["citation_validity"]["verdict"] == "not_applicable"


def test_structural_validation_and_missing_original_evidence(store):
    q, s = store.dataset["questions"][0], store.samples()[0]
    packet = judge.packet_for(store.dataset, q, s)
    result = response(packet)
    assert judge.validate_metrics(result["content"], packet)["facts"]["verdict"] == "pass"
    packet["supplied_evidence"] = None
    assert (
        judge.validate_metrics(result["content"], packet)["citation_accuracy"]["verdict"]
        == "not_evaluable"
    )
    bad = json.loads(result["content"])
    bad["metrics"]["facts"]["evidence"][0]["quote"] = "이 근거는 원문에 없음"
    with pytest.raises(ValueError, match="구간"):
        judge.validate_metrics(json.dumps(bad), packet)
    bad["metrics"]["facts"]["answer_quote"] = "원문에 없는 답"
    with pytest.raises(ValueError, match="답변"):
        judge.validate_metrics(json.dumps(bad), packet)


def test_old_value_in_negation_is_not_keyword_failure(store):
    q = store.dataset["questions"][5]
    s = deepcopy(store.samples()[5])
    s["answer"] = "일반 입고는 2시간이며, 반품 기준 48시간은 적용하지 않습니다."
    packet = judge.packet_for(store.dataset, q, s)
    assert judge.validate_metrics(response(packet)["content"], packet)["facts"]["verdict"] == "pass"
    assert "부정·대조" in judge.SYSTEM


def test_success_and_paid_invalid_response_checkpoint(store):
    store.provider = lambda model, cfg, packet: response(packet)
    j = job()
    store.execute(j, store.samples()[:2])
    assert j["status"] == "completed" and j["spent_micros"] == 20
    assert len(j["rows"]) == 2 and not j["not_run"]
    store.provider = lambda *args: {"content": "wrong", "cost_micros": 17}
    j = job()
    store.execute(j, store.samples()[:2])
    assert j["status"] == "partial" and j["spent_micros"] == 17
    assert len(j["not_run"]) == 1 and j["rows"][0]["status"] == "error"
    assert j["unknown_cost"] is False


def test_unknown_cost_and_timeout_stop_without_retry(store):
    calls = []

    def provider(model, cfg, packet):
        calls.append(1)
        return response(packet, None)

    store.provider = provider
    j = job()
    store.execute(j, store.samples()[:2])
    assert j["unknown_cost"] and len(calls) == 1 and j["status"] == "partial"

    def fail(*args):
        raise RuntimeError("secret-do-not-return")

    store.provider = fail
    j = job()
    store.execute(j, store.samples()[:2])
    assert j["unknown_cost"] and "secret" not in json.dumps(j)


def test_budget_prevents_calls_and_restart_marks_interrupted(store):
    store.provider = lambda *args: pytest.fail("예산 부족 호출")
    j = job()
    j["budget_micros"] = 1
    store.execute(j, store.samples()[:2])
    assert j["asked"] == 0 and len(j["not_run"]) == 2
    j["status"] = "running"
    judge.atomic(store.root / "job-interrupted.json", j)
    restored = judge.JudgeStore(store.parent)
    assert judge.read(restored.root / "job-interrupted.json")["status"] == "interrupted"


def test_explicit_model_and_shared_busy_guard(store, monkeypatch):
    s = store.samples()[0]
    payload = {"model": "test/model", "budget_micros": 200000, "sample_ids": [s["id"]]}
    with pytest.raises(ValueError, match="준비"):
        store.start(payload)
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-only")
    store.models = {"test/model": job()["model_config"]}
    judge.atomic(store.parent.root / "job-other.json", {"status": "running"})
    with pytest.raises(judge.Conflict, match="진행"):
        store.start(payload)
    payload["sample_ids"] = [s["id"], s["id"]]
    with pytest.raises(ValueError, match="중복"):
        store.start(payload)


def test_reviews_persist_revisions_and_stale_targets(store):
    sample = store.samples()[0]
    payload = {
        "kind": "sample",
        "id": sample["id"],
        "target": sample["fingerprint"],
        "revision": 0,
        "reason": "직접 대조한 테스트 데이터",
        "metrics": dict.fromkeys(judge.METRICS, "fail"),
    }
    assert store.review(payload) == {"saved": True}
    restored = judge.JudgeStore(store.parent)
    assert restored.snapshot()["reviews"][sample["fingerprint"]]["revision"] == 1
    with pytest.raises(judge.Conflict, match="다른 검토"):
        store.review(payload)
    payload["target"] = "old"
    with pytest.raises(judge.Conflict, match="입력"):
        store.review(payload)
    q = store.dataset["questions"][0]
    assert q["fingerprint"] not in restored.snapshot()["reviews"]


def test_agreement_excludes_unreviewed_and_separates_origins(store):
    s = store.samples()[0]
    r = {s["fingerprint"]: {"metrics": {"facts": {"verdict": "pass"}}}}
    human = {s["fingerprint"]: {"metrics": {"facts": "fail"}}}
    rows = [s, s, {**s, "origin": "stored", "fingerprint": "different"}]
    stats = judge.agreement(rows, r, human)
    assert stats["synthetic"]["facts"]["paired"] == 1
    assert stats["synthetic"]["facts"]["false_pass"] == 1
    assert stats["stored"]["facts"]["agreement"] is None
    assert stats["synthetic"]["refusal"]["paired"] == 0


def test_model_configuration_rejects_bad_pricing(monkeypatch):
    monkeypatch.setenv("EVALUATION_JUDGE_MODELS", json.dumps({"test/model": job()["model_config"]}))
    assert "test/model" in judge.model_config()
    monkeypatch.setenv("EVALUATION_JUDGE_MODELS", '{"test/model":{"input_usd_per_million":"NaN"}}')
    assert judge.model_config() == {}


def test_inflight_checkpoint_and_immutable_inputs_survive_restart(store):
    samples = store.samples()[:2]

    def interrupt(*args):
        raise KeyboardInterrupt()

    store.provider = interrupt
    j = job()
    with pytest.raises(KeyboardInterrupt):
        store.execute(j, samples)
    path = next(store.root.glob("job-*.json"))
    before = judge.read(path)
    assert before["asked"] == 1 and before["in_flight"]["sample_id"] == samples[0]["id"]
    assert before["inputs"][0]["packet"]["answer"] == samples[0]["answer"]
    assert before["inputs"][0]["packet"]["reference_evidence"]
    assert before["prompt"] == judge.SYSTEM
    judge.JudgeStore(store.parent)
    recovered = judge.read(path)
    assert recovered["unknown_cost"] is True and recovered["status"] == "interrupted"
    assert recovered["rows"][0]["cost_micros"] is None
    assert recovered["not_run"] == [samples[1]["id"]]
    assert recovered["inputs"] == before["inputs"]


@pytest.mark.parametrize("choices", [[], [{}], [{"message": None}], [{"message": {"content": []}}]])
def test_provider_retains_known_cost_with_malformed_choices(monkeypatch, choices):
    original = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"usage": {"cost": 0.000017}, "choices": choices})
    )
    monkeypatch.setenv("OPENROUTER_API_KEY", "test")
    monkeypatch.setattr(
        judge.httpx, "Client", lambda **kwargs: original(transport=transport, **kwargs)
    )
    result = judge.OpenRouterJudge()("test/model", job()["model_config"], {})
    assert result["cost_micros"] == 17 and result["content"] == ""
