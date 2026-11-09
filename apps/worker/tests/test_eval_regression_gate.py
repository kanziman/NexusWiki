"""#246: 실제 합성 결과 재채점의 실패 전파와 오프라인 실행을 검증한다."""

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "eval_gate", ROOT / "scripts/check_eval_regression.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.fixture
def corpus():
    return json.loads(gate.DEFAULT_FIXTURE.read_text())


def test_frozen_real_answers_match_without_network(corpus, monkeypatch):
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError("관문은 네트워크를 사용하면 안 된다")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert gate.check(corpus) == []
    assert len(corpus["rows"]) == 30
    assert any(not row["expected"]["pass"] for row in corpus["rows"])
    assert any(row["doc"] == "none" for row in corpus["rows"])


@pytest.mark.parametrize("change", ["citation", "keyword", "refusal", "reason"])
def test_changed_quality_verdict_is_reported(corpus, change):
    row = corpus["rows"][0]
    if change == "citation":
        row["cited_wiki_count"] = 0
    elif change == "keyword":
        row["keyword_hit"] = False
    elif change == "refusal":
        row = next(r for r in corpus["rows"] if r["doc"] == "none")
        row["answer"] = "회사의 영업이익은 100원입니다."
    else:
        row["expected"]["reason"] = "잘못된 이유"
    assert any(row["id"] in diff for diff in gate.check(corpus))


@pytest.mark.parametrize(
    "damage", ["missing", "duplicate", "extra", "private", "type", "empty", "both", "doc"]
)
def test_invalid_corpus_fails_closed(corpus, damage):
    if damage == "missing":
        corpus["rows"].pop()
    elif damage == "duplicate":
        corpus["rows"][1] = copy.deepcopy(corpus["rows"][0])
    elif damage == "extra":
        corpus["rows"][0]["id"] = "q99"
    elif damage == "private":
        corpus["rows"][0]["workspace_id"] = "must-not-be-published"
    elif damage == "type":
        corpus["rows"][0]["cited_wiki_count"] = True
    elif damage == "both":
        corpus["rows"].pop()
        corpus["question_ids"].pop()
    elif damage == "doc":
        corpus["rows"][0]["doc"] = "none"
    else:
        corpus["rows"] = []
        corpus["question_ids"] = []
    with pytest.raises(ValueError):
        gate.check(corpus)


@pytest.mark.parametrize("where", ["fixture", "row", "expected"])
def test_unknown_field_error_names_field_without_value(corpus, where):
    leaked_value = "must-not-be-printed"
    if where == "fixture":
        corpus["workspace_id"] = leaked_value
    elif where == "row":
        corpus["rows"][0]["workspace_id"] = leaked_value
    else:
        corpus["rows"][0]["expected"]["workspace_id"] = leaked_value
    with pytest.raises(ValueError, match="workspace_id") as raised:
        gate.check(corpus)
    assert leaked_value not in str(raised.value)


def test_general_question_answer_body_is_rejected(corpus):
    row = next(r for r in corpus["rows"] if r["doc"] != "none")
    row["answer"] = "저장하면 안 되는 일반 문항 답변"
    with pytest.raises(ValueError, match=f"{row['id']}: 일반 문항의 답변 본문"):
        gate.check(corpus)


def test_fixture_keeps_answer_body_only_for_refusal_questions(corpus):
    for row in corpus["rows"]:
        if row["doc"] == "none":
            assert row["answer"], "거절 재채점에는 답변 본문이 필요하다"
        else:
            assert row["answer"] == ""


def test_cli_exit_codes_reach_ci(corpus, tmp_path):
    fixture = tmp_path / "fixture.json"
    command = [sys.executable, str(ROOT / "scripts/check_eval_regression.py"), str(fixture)]
    fixture.write_text(json.dumps(corpus))
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 0
    corpus["rows"][0]["cited_source_count"] = 0
    fixture.write_text(json.dumps(corpus))
    result = subprocess.run(command, capture_output=True, text=True, check=False)  # noqa: S603
    assert result.returncode == 1 and "q01" in result.stdout
    fixture.write_text("{}")
    assert subprocess.run(command, capture_output=True, check=False).returncode == 2  # noqa: S603
