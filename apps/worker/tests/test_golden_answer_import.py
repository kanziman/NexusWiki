"""실제 재생에서 캡처한 근거만 새 골든셋에 연결하는지 검사한다."""

import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
import golden_answer_judge as j  # noqa: E402


def test_product_import_preserves_map_and_does_not_reuse_old_review(tmp_path):
    parent = SimpleNamespace(root=tmp_path, guard=threading.Lock(), max_budget=1000000)
    store = j.JudgeStore(parent)
    q = store.dataset["questions"][0]
    record = {
        "id": "live",
        "label": "새 실제 재생",
        "source": "ask-product-replay",
        "dataset_fingerprint": store.dataset["fingerprint"],
        "samples": [
            {
                "question_id": q["id"],
                "question_fingerprint": q["fingerprint"],
                "answer": "오후 2시 [[src:s1]]",
                "supplied_evidence": {"src:s1": "주문 마감은 오후 2시다."},
            }
        ],
    }
    j.atomic(store.root / "answers-live.json", record)
    samples = [s for s in store.samples() if s["origin"] == "stored"]
    assert len(samples) == 1
    assert samples[0]["supplied_evidence"] == record["samples"][0]["supplied_evidence"]
    assert samples[0]["citation_validity"]["verdict"] == "pass"
    assert store.snapshot()["reviews"] == {}
    record["samples"][0]["question_fingerprint"] = "old"
    j.atomic(store.root / "answers-live.json", record)
    assert not [s for s in store.samples() if s["origin"] == "stored"]


def test_different_dataset_or_untrusted_source_is_not_imported(tmp_path):
    store = j.JudgeStore(SimpleNamespace(root=tmp_path, guard=threading.Lock(), max_budget=1000000))
    for record in [
        {"source": "unknown"},
        {"source": "ask-product-replay", "dataset_fingerprint": "old"},
    ]:
        j.atomic(store.root / "answers-bad.json", record)
        assert not [s for s in store.samples() if s["origin"] == "stored"]


def test_additional_ai_review_never_becomes_human_review_or_agreement(tmp_path):
    store = j.JudgeStore(SimpleNamespace(root=tmp_path, guard=threading.Lock(), max_budget=1000000))
    sample = store.samples()[0]
    metrics = {
        key: {"verdict": "review_needed", "reason": "AI 검토", "answer_quote": "", "evidence": []}
        for key in j.METRICS
    }
    record = {
        "reviewer_kind": "ai_assistant",
        "dataset_fingerprint": store.dataset["fingerprint"],
        "rubric": j.RUBRIC,
        "rows": [{"fingerprint": sample["fingerprint"], "metrics": metrics}],
    }
    before = store.snapshot()
    path = store.root / "ai-review-test.json"
    j.atomic(path, record)
    after = store.snapshot()
    assert after["ai_reviews"][sample["fingerprint"]]["metrics"] == metrics
    assert after["reviews"] == before["reviews"] == {}
    assert after["results"] == before["results"] == {}
    assert after["agreement"] == before["agreement"]
    for field, wrong in [
        ("reviewer_kind", "human"),
        ("dataset_fingerprint", "old"),
        ("rubric", "old"),
    ]:
        j.atomic(path, {**record, field: wrong})
        assert store.snapshot()["ai_reviews"] == {}
    record["rows"][0]["fingerprint"] = "old-answer"
    j.atomic(path, record)
    assert store.snapshot()["ai_reviews"] == {}


def test_single_json_fence_is_normalized_without_extracting_arbitrary_prose():
    packet = {
        "answer": "원문에서는 알 수 없습니다.",
        "answerable": False,
        "reference_evidence": {},
        "supplied_evidence": {},
    }
    metrics = {
        key: {
            "verdict": "not_applicable",
            "reason": "주장 없음",
            "answer_quote": "",
            "evidence": [],
        }
        for key in j.METRICS
    }
    raw = json.dumps({"metrics": metrics}, ensure_ascii=False)
    assert j.validate_metrics("```json\n" + raw + "\n```", packet) == metrics
    with pytest.raises(json.JSONDecodeError):
        j.validate_metrics("설명문\n```json\n" + raw + "\n```", packet)
