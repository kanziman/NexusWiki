"""공개 평가에서 분모 0·조건 불일치·개인 데이터가 성과로 둔갑하지 않는지 검사한다."""

import argparse
import copy
import importlib.util
import json
import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "research_eval", ROOT / "scripts/evidence_research_eval.py"
)
evaluation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evaluation)


def test_empty_records_are_invalid_and_have_no_recovery_rate():
    result = evaluation.build_public([])
    assert result["valid"] is False
    assert result["adopted"] is False
    assert result["recovery"]["rate"] is None


def test_execution_fingerprint_detects_prompt_and_output_limit_changes(tmp_path):
    api = tmp_path / "apps/api/src/ask.py"
    worker = tmp_path / "apps/worker/src/main.py"
    api.parent.mkdir(parents=True)
    worker.parent.mkdir(parents=True)
    api.write_text('PROMPT = "충분하면 충분만 출력"')
    worker.write_text("MAX_TOKENS = 1500")
    initial = evaluation.execution_sha256(tmp_path)
    worker.write_text("MAX_TOKENS = 256")
    capped = evaluation.execution_sha256(tmp_path)
    assert initial != capped
    api.write_text('PROMPT = "답변하지 말고 충분만 출력"')
    assert capped != evaluation.execution_sha256(tmp_path)


MODEL = "anthropic/claude-sonnet-4.6"


def _run_args(tmp_path, manifest, **extra):
    state = tmp_path / "state.json"
    state.write_text(json.dumps({"stack_url": "http://127.0.0.1:54621", "workspace_id": "ws"}))
    runtime = tmp_path / "runtime.json"
    runtime.write_text(json.dumps(manifest))
    values = {
        "out": str(tmp_path / "on-1.json"),
        "state": str(state),
        "mode": "on",
        "pair": 1,
        "model": MODEL,
        "runtime_manifest": str(runtime),
        "resume_from": None,
        "api": "http://127.0.0.1:8032",
    }
    values.update(extra)
    return argparse.Namespace(**values)


def _forbid_network(monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("지문 검증 전에 네트워크를 쓰면 안 된다")

    monkeypatch.setattr(evaluation.httpx, "Client", refuse)
    monkeypatch.setattr(evaluation.replay, "_ask_once", refuse)


@pytest.mark.parametrize(
    "manifest", [{"model": MODEL}, {"model": MODEL, "execution_sha256": "old"}]
)
def test_run_refuses_missing_or_stale_execution_fingerprint(tmp_path, monkeypatch, manifest):
    _forbid_network(monkeypatch)
    monkeypatch.setattr(evaluation, "execution_sha256", lambda root=None: "current")
    args = _run_args(tmp_path, manifest)
    with pytest.raises(SystemExit, match="실행 코드 지문"):
        evaluation.run(args)
    assert not Path(args.out).exists()


def test_resume_refuses_prior_record_with_different_conditions(tmp_path, monkeypatch):
    monkeypatch.setattr(evaluation, "execution_sha256", lambda root=None: "current")

    @contextmanager
    def client(**kwargs):
        yield object()

    def no_paid_call(*args, **kwargs):
        raise AssertionError("조건이 다른 재개에서 유료 호출을 하면 안 된다")

    monkeypatch.setattr(evaluation.httpx, "Client", client)
    monkeypatch.setattr(evaluation.replay, "_login", lambda *a: "token")
    monkeypatch.setattr(evaluation.replay, "_ask_once", no_paid_call)
    monkeypatch.setattr(
        evaluation, "snapshot", lambda *a: {"corpus": "c", "prompts": "p", "tables": {}}
    )
    args = _run_args(tmp_path, {"model": MODEL, "execution_sha256": "current"})
    prior = tmp_path / "on-1.partial.json"
    conditions = {
        "corpus": "c",
        "prompts": "p",
        "fixture": evaluation.digest(evaluation.replay._load_sample(evaluation.SAMPLE)),
        "model": MODEL,
        "settings": evaluation.digest({"model": MODEL, "execution_sha256": "current"}),
        "policy": evaluation.digest(
            {
                name: (evaluation.ROOT / "packages/core/src/nexuswiki_core" / name).read_text()
                for name in ("retrieval_policy.py", "rrf.py", "llm_policy.py")
            }
        ),
        "execution": "current",
    }
    # 대조군: 조건이 같은 원본은 거부 단계를 통과해 첫 질문 호출까지 간다.
    prior.write_text(json.dumps({"mode": "on", "pair": 1, "conditions": conditions}))
    args.resume_from = str(prior)
    with pytest.raises(AssertionError, match="유료 호출"):
        evaluation.run(args)

    # 실행 지문만 다른 원본: 코드가 바뀐 뒤의 재개는 거부돼야 한다.
    prior.write_text(
        json.dumps({"mode": "on", "pair": 1, "conditions": {**conditions, "execution": "old"}})
    )
    with pytest.raises(SystemExit, match="재개 원본의 비교 조건"):
        evaluation.run(args)
    assert not Path(args.out).exists()

    # 모드가 다른 원본도 거부한다.
    prior.write_text(json.dumps({"mode": "off", "pair": 1, "conditions": conditions}))
    with pytest.raises(SystemExit, match="재개 원본의 비교 조건"):
        evaluation.run(args)


def test_public_export_drops_credentials_and_operational_payloads():
    sample = evaluation.replay._load_sample(evaluation.SAMPLE)
    records = [
        {
            "pair": pair,
            "mode": mode,
            "revision": "baseline",
            "created_at": "2026-11-08",
            "conditions": {
                "fixture": evaluation.digest(sample),
                "model": "synthetic-model",
                "secret": "DO-NOT-PUBLISH",
            },
            "rows": [],
            "credential": "DO-NOT-PUBLISH",
            "snapshot": {"raw_sources": []},
        }
        for pair in evaluation.EVALUATION_PAIRS
        for mode in ("off", "on")
    ]
    import json

    exported = evaluation.build_public(records)
    assert "DO-NOT-PUBLISH" not in json.dumps(exported)
    assert exported["valid"] is False


def test_hashed_evidence_maps_to_expected_raw_document():
    import hashlib

    record = {
        "snapshot": {
            "source_chunks": [{"id": "chunk", "raw_source_id": "raw"}],
            "wiki_pages": [{"id": "wiki", "sources": ["raw"]}],
        }
    }
    assert evaluation.origins(
        record,
        [
            {
                "kind": "source",
                "document_hash": hashlib.sha256(b"chunk").hexdigest(),
            }
        ],
    ) == {"raw"}
    assert evaluation.origins(record, [{"kind": "source", "document_hash": "missing"}]) is None


def test_paired_recovery_and_condition_mismatch_are_distinguished():
    sample = evaluation.replay._load_sample(evaluation.SAMPLE)
    snapshot = {
        "raw_sources": [{"id": d["id"], "title": d["title"]} for d in sample["documents"]],
        "source_chunks": [{"id": d["id"], "raw_source_id": d["id"]} for d in sample["documents"]],
        "wiki_pages": [],
    }
    conditions = dict(
        corpus="fixed",
        prompts="fixed",
        policy="fixed",
        settings="fixed",
        execution="fixed",
        model="model",
        fixture=evaluation.digest(sample),
    )
    records = []
    for pair in evaluation.EVALUATION_PAIRS:
        for mode in ("off", "on"):
            rows = []
            for question in sample["questions"]:
                evidence = [
                    {"kind": "source", "document_id": d}
                    for d in question["doc"].split("+")
                    if d != "none"
                ]
                initial = evidence[:1] if question["id"] == "r01" else evidence
                rows.append(
                    {
                        "id": question["id"],
                        "status": "resolved",
                        "cost_micros": 100 if mode == "off" else 120,
                        "elapsed_ms": 1000,
                        "first_delta_ms": 500,
                        "fabricated_anchor_count": 0,
                        "verdict": {
                            "pass": mode == "on" or question["id"] != "r01",
                            "reason": None,
                        },
                        "research": {"initial_evidence": initial, "final_evidence": evidence},
                    }
                )
            records.append(
                dict(
                    pair=pair,
                    mode=mode,
                    rows=rows,
                    snapshot=snapshot,
                    conditions=conditions.copy(),
                    revision="HEAD",
                    created_at="now",
                )
            )
    result = evaluation.build_public(records)
    assert result["valid"] and result["adopted"]
    assert result["recovery"]["eligible"] == result["recovery"]["answer"] == 1
    assert "반복 안정성은 미측정" in result["method"]
    assert not evaluation.build_public(records[:1])["valid"]
    assert not evaluation.build_public(records + [records[0]])["valid"]
    legacy = copy.deepcopy(records)
    for record in legacy:
        del record["conditions"]["execution"]
    assert not evaluation.build_public(legacy)["valid"]
    altered = copy.deepcopy(records)
    altered[1]["conditions"]["policy"] = "different"
    assert not evaluation.build_public(altered)["valid"]
    altered = copy.deepcopy(records)
    altered[1]["rows"][30]["retrieval"] = {"missing_channels": ["source_vector"]}
    result = evaluation.build_public(altered)
    assert not result["valid"] and not result["adopted"]
    assert result["recovery"]["answer"] == 0
