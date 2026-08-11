"""Contracts for the repository-owned retrieval evaluation dataset."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures" / "retrieval"
CORPUS = FIXTURES / "representative_corpus.v1.json"
GOLDEN = FIXTURES / "golden_queries.v1.json"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text())


def _sha256(document: dict[str, object]) -> str:
    payload = {key: value for key, value in document.items() if key != "sha256"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _benchmark_module():
    spec = importlib.util.spec_from_file_location(
        "benchmark_retrieval", Path("scripts/benchmark_retrieval.py")
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_pinned_corpus_and_golden_set_cover_reviewable_multilingual_evidence() -> None:
    corpus = _load(CORPUS)
    golden = _load(GOLDEN)

    assert corpus["version"] == "representative-corpus-v1"
    assert corpus["sha256"] == _sha256(corpus)
    assert golden["version"] == "golden-queries-v1"
    assert golden["sha256"] == _sha256(golden)
    assert golden["corpus_version"] == corpus["version"]
    assert golden["corpus_sha256"] == corpus["sha256"]

    records = golden["queries"]
    assert isinstance(records, list)
    assert 30 <= len(records) <= 50
    languages = {record["language"] for record in records}
    assert {"ko", "en", "mixed"} <= languages

    evidence_ids = {f"source:{row['id']}" for row in corpus["source_chunks"]} | {
        f"wiki:{row['id']}" for row in corpus["wiki_pages"]
    }
    for record in records:
        assert record["scenario"]
        assert record["language"] in {"ko", "en", "mixed"}
        assert record["requested_k"] > 0
        required = record["required_evidence"]
        assert required
        for label in required:
            assert label["id"] in evidence_ids
            assert 1 <= label["max_rank"] <= record["requested_k"]
        for alternative in record["allowed_alternatives"]:
            assert alternative["for"] in {label["id"] for label in required}
            assert alternative["id"] in evidence_ids


def test_benchmark_verify_emits_pinned_stamps_and_metrics(tmp_path: Path) -> None:
    record = tmp_path / "record.json"
    result = subprocess.run(  # noqa: S603 -- fixed repository script and pytest temp output
        [sys.executable, "scripts/benchmark_retrieval.py", "--verify", "--output", str(record)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(record.read_text())
    assert payload["policy_version"] == "hybrid-rrf-v1"
    assert payload["corpus_sha256"] == _load(CORPUS)["sha256"]
    assert payload["golden_sha256"] == _load(GOLDEN)["sha256"]
    for metric in (
        "recall_at_k",
        "strict_query_pass_rate",
        "mrr",
        "mean_required_rank",
        "channel_hits",
        "channel_contribution",
        "latency_ms",
        "underfill",
        "graph_delta",
    ):
        assert metric in payload["metrics"]


def test_benchmark_fails_required_hit_rank_and_unlisted_substitution(tmp_path: Path) -> None:
    golden = _load(GOLDEN)
    first = golden["queries"][0]
    bad_result_sets = (
        {first["id"]: []},
        {first["id"]: ["source:src-onboarding"] * 4},
        {first["id"]: ["source:src-vpn"]},
    )
    for index, results in enumerate(bad_result_sets):
        result_file = tmp_path / f"bad-{index}.json"
        result_file.write_text(json.dumps({"queries": results}))
        completed = subprocess.run(  # noqa: S603 -- fixed repository script and pytest temp input
            [
                sys.executable,
                "scripts/benchmark_retrieval.py",
                "--verify",
                "--fixture-results",
                str(result_file),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode != 0
        assert "evaluation_failed" in completed.stderr


def test_fixture_validator_rejects_invalid_labels_and_unpinned_alternatives() -> None:
    corpus = _load(CORPUS)
    golden = _load(GOLDEN)
    module = _benchmark_module()
    mutations = (
        ("language", "fr"),
        ("required_evidence", []),
        ("allowed_alternatives", [{"for": "source:missing", "id": "wiki:wiki-sso"}]),
    )
    for field, value in mutations:
        candidate = json.loads(json.dumps(golden))
        candidate["queries"][0][field] = value
        candidate["sha256"] = _sha256(candidate)
        try:
            module._validate_inputs(corpus, candidate)
        except module.VerificationError:
            continue
        raise AssertionError(f"{field} mutation must fail closed")
