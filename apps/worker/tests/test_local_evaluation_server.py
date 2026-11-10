"""루프백 실행기의 비용·동시 실행·재시작·결과 보존을 모델 호출 없이 검사한다."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "local_evaluation_server", ROOT / "scripts/local_evaluation_server.py"
)
assert spec and spec.loader
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)


@pytest.fixture
def store(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {"questions": [{"id": "q01", "doc": "a", "query": "질문", "expect_any": ["정답"]}]}
        )
    )
    monkeypatch.setattr(server, "FIXTURE", fixture)
    source = tmp_path / ".worktrees/reliability-evidence-20261109/runs/reliability-1.json"
    source.parent.mkdir(parents=True)
    row = {
        "id": "q01",
        "doc": "a",
        "status": "resolved",
        "answer": "정답",
        "keyword_hit": True,
        "model": "test",
        "prompt_tokens": 10,
        "completion_tokens": 1,
        "elapsed_ms": 10,
        "cost_micros": 20,
        "fabricated_anchor_count": 0,
        "cited_wiki_count": 1,
        "cited_source_count": 1,
    }
    result = server.build_result(
        label="원본",
        sha="abc",
        questions=[{"id": "q01"}],
        rows=[row],
        fixed={
            "fixture_sha256": "f",
            "snapshot_sha256": "s",
            "answer_prompt_sha256": "p",
            "model": "test",
            "requested_k": 8,
            "policy_versions": ["v"],
        },
        stopped=None,
    )
    source.write_text(json.dumps(result))
    monkeypatch.setattr(server, "ROOT", tmp_path)
    value = server.Store(tmp_path / "store")
    yield value
    value.lock_file.close()


def test_rescore_persists_and_baseline_survives_restart(store):
    # 원본 fixture가 1문항이므로 테스트의 planned만 맞춘다.
    job = {
        "id": "test",
        "label": "재채점",
        "mode": "rescore",
        "status": "queued",
        "asked": 0,
        "planned": 1,
        "budget_micros": 0,
        "created_at": server.now(),
        "error": None,
    }
    store.execute(job)
    snapshot = store.snapshot()
    assert snapshot["jobs"][0]["status"] == "completed"
    assert len(snapshot["runs"]) == 2
    assert snapshot["runs"][1]["rows"][0]["passed"] is True
    store.baseline("test")
    root = store.root
    store.lock_file.close()
    restarted = server.Store(root)
    assert restarted.snapshot()["baseline_id"] == "test"
    restarted.lock_file.close()


def test_single_flight_and_paid_limits(store, monkeypatch):
    monkeypatch.setattr(server.threading.Thread, "start", lambda self: None)
    with pytest.raises(ValueError):
        store.start({"mode": "model", "label": "유료", "budget_micros": 999999999})
    with pytest.raises(ValueError):
        store.start({"mode": "rescore", "label": 123})
    store.start({"mode": "rescore", "label": "무료"})
    with pytest.raises(ValueError, match="진행 중"):
        store.start({"mode": "rescore", "label": "두번째"})


def test_nonlocal_configuration_and_unknown_baseline_rejected(store):
    with pytest.raises(SystemExit):
        server.Store(store.root / "remote", api="https://example.com")
    with pytest.raises(ValueError):
        store.baseline("../private")


def test_restart_marks_inflight_interrupted(store):
    server.atomic(
        store.root / "job-interrupted.json",
        {"id": "i", "status": "running", "created_at": server.now()},
    )
    root = store.root
    store.lock_file.close()
    restarted = server.Store(root)
    assert restarted.snapshot()["jobs"][0]["status"] == "interrupted"
    restarted.lock_file.close()


def test_last_unknown_cost_is_partial_and_checkpoint_is_kept(store, monkeypatch):
    source = server.read(
        server.ROOT / ".worktrees/reliability-evidence-20261109/runs/reliability-1.json"
    )
    state = store.root / "state.json"
    state.write_text(
        json.dumps({"stack_url": "http://127.0.0.1:54621", "workspace_id": "synthetic"})
    )
    store.state = state
    monkeypatch.setattr(server.replay, "_login", lambda *args: "test")
    monkeypatch.setattr(server.replay, "_api_sha", lambda *args: "test")
    monkeypatch.setattr(server.replay, "collect_fixed_inputs", lambda *args: source["fixed_inputs"])
    monkeypatch.setattr(
        server.replay, "select_questions", lambda sample, *args: sample["questions"]
    )
    row = {**source["rows"][0], "cost_micros": None}
    monkeypatch.setattr(server.replay, "_ask_once", lambda *args: row)
    job = {
        "id": "unknown",
        "label": "비용 미기록",
        "mode": "model",
        "status": "queued",
        "asked": 0,
        "planned": 1,
        "budget_micros": 200000,
        "created_at": server.now(),
        "error": None,
    }
    store.execute(job)
    assert server.read(store.root / "job-unknown.json")["status"] == "partial"
    checkpoint = server.read(store.root / "raw-unknown.json")
    assert len(checkpoint["rows"]) == 1
    assert checkpoint["stopped"]["reason"] == "unknown_cost"
    assert len(store.snapshot()["runs"]) == 1


def test_checkpoint_survives_interruption_before_next_question(store, monkeypatch):
    source = server.read(
        server.ROOT / ".worktrees/reliability-evidence-20261109/runs/reliability-1.json"
    )
    state = store.root / "state.json"
    state.write_text(
        json.dumps({"stack_url": "http://127.0.0.1:54621", "workspace_id": "synthetic"})
    )
    store.state = state
    monkeypatch.setattr(server.replay, "_login", lambda *args: "test")
    monkeypatch.setattr(server.replay, "_api_sha", lambda *args: "test")
    monkeypatch.setattr(server.replay, "collect_fixed_inputs", lambda *args: source["fixed_inputs"])
    monkeypatch.setattr(
        server.replay, "select_questions", lambda sample, *args: sample["questions"]
    )

    def interrupted(*args, after_question, **kwargs):
        after_question(20, source["rows"][0])
        raise RuntimeError("실행 중단")

    monkeypatch.setattr(server.replay, "run_replay", interrupted)
    job = {
        "id": "checkpoint",
        "label": "중단",
        "mode": "model",
        "status": "queued",
        "asked": 0,
        "planned": 1,
        "budget_micros": 200000,
        "created_at": server.now(),
        "error": None,
    }
    store.execute(job)
    assert server.read(store.root / "raw-checkpoint.json")["rows"][0]["answer"] == "정답"
    assert server.read(store.root / "job-checkpoint.json")["status"] == "failed"


def test_duplicate_label_is_rejected_as_conflict(store, monkeypatch):
    """재채점은 수 ms에 끝나 다시 누르기 쉽다. 같은 이름이 쌓이면 목록에서 구분할 수 없다."""
    monkeypatch.setattr(server.threading.Thread, "start", lambda self: None)
    with pytest.raises(server.Conflict, match="같은 이름"):
        store.start({"mode": "rescore", "label": "보존된 HTTP 1 · 초기 기준"})
    job = {
        "id": "done",
        "label": "채점기 수정 후",
        "mode": "rescore",
        "status": "queued",
        "asked": 0,
        "planned": 1,
        "budget_micros": 0,
        "created_at": server.now(),
        "error": None,
    }
    store.execute(job)
    with pytest.raises(server.Conflict, match="같은 이름"):
        store.start({"mode": "rescore", "label": "채점기 수정 후"})
    assert store.start({"mode": "rescore", "label": "다른 이름"})["label"] == "다른 이름"
