"""공개 합성 답변 사본의 식별자 차단·회차 일치·재채점 검증."""

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "evaluation_run_export", ROOT / "scripts/evaluation_run_export.py"
)
assert spec and spec.loader
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


def committed():
    return json.loads((ROOT / "apps/dashboard/content/evaluation-runs.json").read_text())


def test_public_records_pass_without_private_source_files():
    exporter.check_public(committed())


@pytest.mark.parametrize(
    "value",
    ["person@example.com", "51b80299-1234-4321-8888-123456789abc", "Bearer secretvalue123456"],
)
def test_sensitive_response_is_rejected(value):
    data = committed()
    data["runs"][0]["rows"][0]["response_text"] = value
    with pytest.raises(ValueError, match="공개할 수 없는 답변"):
        exporter.check_public(data)


def test_unknown_fields_and_changed_verdict_are_rejected():
    data = committed()
    bad = copy.deepcopy(data)
    bad["runs"][0]["rows"][0]["workspace_id"] = "private"
    with pytest.raises(ValueError, match="허용 필드"):
        exporter.check_public(bad)
    data["runs"][0]["rows"][5]["passed"] = True
    with pytest.raises(ValueError, match="판정 또는 집계"):
        exporter.check_public(data)


def test_different_evaluation_and_cost_are_rejected():
    data = committed()
    data["evaluation_sha256"] = "different"
    with pytest.raises(ValueError, match="지문 불일치"):
        exporter.check_public(data)
    data = committed()
    data["runs"][0]["rows"][0]["cost_micros"] += 1
    with pytest.raises(ValueError, match="원본 결과 불일치"):
        exporter.check_public(data)


def test_changed_response_cannot_keep_stored_keyword_pass():
    data = committed()
    assert data["runs"][0]["rows"][0]["passed"] is True
    data["runs"][0]["rows"][0]["response_text"] = "완전히 무관한 답변입니다."
    with pytest.raises(ValueError, match="기대 표현 판정 불일치"):
        exporter.check_public(data)
