"""Contracts for the repository-owned retrieval evaluation dataset."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "retrieval"
CORPUS = FIXTURES / "representative_corpus.v1.json"
GOLDEN = FIXTURES / "golden_queries.v1.json"
MANIFEST = FIXTURES / "benchmark_hnsw_corpus.v1.json"
BENCHMARK_RECORDS = Path("docs/ops/benchmark-records")


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    payload = json.loads(record.read_text(encoding="utf-8"))
    from nexuswiki_core.retrieval_policy import POLICY_VERSION

    assert payload["policy_version"] == POLICY_VERSION
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
        result_file.write_text(json.dumps({"queries": results}), encoding="utf-8")
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


def test_benchmark_manifest_and_counter_stream_are_pinned_and_deterministic() -> None:
    spec = importlib.util.spec_from_file_location(
        "benchmark_generator", Path("scripts/generate_retrieval_benchmark_corpus.py")
    )
    assert spec and spec.loader
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    manifest = _load(MANIFEST)
    assert manifest["sha256"] == generator.canonical_hash(manifest)
    assert (manifest["target_rows_per_relation"], manifest["decoy_rows_per_relation"]) == (
        25000,
        25000,
    )
    assert generator.identity(manifest, "source", 99) == generator.identity(manifest, "source", 99)
    vector = generator.vector(manifest, "source", 99)
    assert len(vector) == 1024
    assert abs(sum(value * value for value in vector) - 1.0) < 1e-9


def test_benchmark_loader_isolates_decoy_parents_per_operational_workspace() -> None:
    spec = importlib.util.spec_from_file_location(
        "benchmark_generator", Path("scripts/generate_retrieval_benchmark_corpus.py")
    )
    assert spec and spec.loader
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    manifest = _load(MANIFEST)

    first, second = generator.loader_sql(manifest, uuid4()), generator.loader_sql(manifest, uuid4())

    # The labelled evidence mapping is pinned across arms, but decoy parents
    # must not share the (parent, chunk_index) unique namespace.
    assert generator.logical_id_map(manifest) == generator.logical_id_map(manifest)
    assert generator.decoy_parent_id(manifest, uuid4(), "source") != generator.decoy_parent_id(
        manifest, uuid4(), "source"
    )
    assert "benchmark filler" in first and first != second
    assert "generate_series(1,24988) g on conflict (raw_source_id,chunk_index) do nothing" in first


def test_benchmark_cleanup_removes_only_the_fixed_workspace_rows() -> None:
    spec = importlib.util.spec_from_file_location(
        "benchmark_generator", Path("scripts/generate_retrieval_benchmark_corpus.py")
    )
    assert spec and spec.loader
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    workspace = uuid4()
    cleanup = generator.loader_sql(_load(MANIFEST), workspace, cleanup=True)

    assert "delete from public.source_chunks" in cleanup
    assert "delete from public.wiki_embeddings" in cleanup
    assert "delete from public.workspaces" in cleanup
    assert str(workspace) in cleanup
    assert "delete from public.source_chunks;" not in cleanup


def test_operational_arms_share_one_manifest_pinned_workspace() -> None:
    module = _benchmark_module()
    manifest = module.load_manifest()

    assert module.benchmark_workspace(manifest) == module.benchmark_workspace(manifest)


def test_policy_content_hash_detects_policy_change_without_version_change() -> None:
    module = _benchmark_module()
    from nexuswiki_core.retrieval_policy import RetrievalPolicy

    baseline = module.policy_content_sha256()
    changed = RetrievalPolicy(
        channel_weights={
            "wiki_vector": 2.0,
            "source_vector": 1.0,
            "wiki_lexical": 1.0,
            "source_lexical": 1.0,
        }
    )
    assert changed.version == RetrievalPolicy().version
    assert module.policy_content_sha256(changed) != baseline


def test_default_enabled_channels_keep_the_recorded_policy_hash() -> None:
    """`enabled_channels` 추가 전 hybrid-rrf-v2 기록의 해시와 같아야 기존 비교가 이어진다."""
    module = _benchmark_module()
    from nexuswiki_core.retrieval_policy import RetrievalPolicy

    recorded_v2 = "1c1b7673054415a5f6ffff3f93c59c1244683f73a8fc134bc68be32b8c8044c5"
    assert module.policy_content_sha256() == recorded_v2
    assert "enabled_channels" not in module.policy_content()

    scoped = RetrievalPolicy(enabled_channels={"source_vector", "source_lexical"})
    assert module.policy_content(scoped)["enabled_channels"] == ["source_lexical", "source_vector"]
    assert module.policy_content_sha256(scoped) != recorded_v2


def test_enabled_channels_must_be_a_non_empty_first_wave_subset() -> None:
    from nexuswiki_core.retrieval_policy import RetrievalPolicy

    with pytest.raises(ValueError, match="enabled channels"):
        RetrievalPolicy(enabled_channels=set())
    with pytest.raises(ValueError, match="enabled channels"):
        RetrievalPolicy(enabled_channels={"graph"})


def test_operational_validator_accepts_observed_empty_retrieval_result_only() -> None:
    """An empty service result is evidence; an empty label-built result is not."""
    module = _benchmark_module()
    channels = {
        name: {
            "status": "ok" if name != "graph" else "disabled",
            "requested": 1,
            "returned": 0,
            "underfill": True,
            "elapsed_ms": 0.1,
            "error_code": None,
            "raw_hit_ids": [],
            "raw_uuid_ids": [],
            "logical_ids": [],
            "contribution": 0,
        }
        for name in ("wiki_vector", "source_vector", "wiki_lexical", "source_lexical", "graph")
    }
    record = {
        "run_kind": "full_path_retrieval_measurement",
        "order_mode": "strict_order",
        "policy_content": module.policy_content(),
        "policy_content_sha256": module.policy_content_sha256(),
        "query_results": [
            {
                "retrieval_observation": "retrieval_service_channel_envelopes_v1",
                "ranked_uuid_evidence": [],
                "ranked_logical_evidence": [],
                "evaluation": {"id": "empty", "passed": False, "checks": []},
                "channels": channels,
            }
        ],
    }

    module._validate_record(record)

    del record["query_results"][0]["retrieval_observation"]
    with pytest.raises(module.VerificationError, match="fabricated_or_label_only_evaluation"):
        module._validate_record(record)


def _explain_evidence(*, decision: str = "inconclusive_escalate_scale") -> dict[str, object]:
    """Small but complete scoped-plan fixture for record-schema contracts."""
    captures = []
    for channel, function, relation in (
        ("source_vector", "search_chunks", "source_chunks"),
        ("wiki_vector", "search_wiki_embeddings", "wiki_embeddings"),
    ):
        captures.append(
            {
                "channel": channel,
                "rpc_function": function,
                "relation": relation,
                "query_id": "golden-01",
                "requested_k": 20,
                "order_mode": "strict_order",
                "graph_enabled": False,
                "plan": [{"Plan": {"Node Type": "Sort", "Plans": []}}],
            }
        )
    return {
        "schema": "retrieval-hnsw-explain-v1",
        "captures": captures,
        "hnsw_observed": False,
        "observed_index_names": [],
        "decision": decision,
    }


def test_explain_evidence_accepts_complete_inconclusive_and_hnsw_captures() -> None:
    module = _benchmark_module()
    inconclusive = _explain_evidence()
    module._validate_explain_evidence(inconclusive, order_mode="strict_order", graph_enabled=False)

    observed = _explain_evidence(decision="representative_hnsw_observed")
    observed["hnsw_observed"] = True
    observed["observed_index_names"] = [
        "source_chunks_embedding_hnsw_idx",
        "wiki_embeddings_embedding_hnsw_idx",
    ]
    for capture, index_name in zip(
        observed["captures"], observed["observed_index_names"], strict=True
    ):
        capture["plan"] = [
            {"Plan": {"Node Type": "Index Scan", "Index Name": index_name, "Plans": []}}
        ]
    module._validate_explain_evidence(observed, order_mode="strict_order", graph_enabled=False)


@pytest.mark.parametrize(
    ("mutate", "error"),
    (
        (lambda evidence: evidence.pop("captures"), "explain_captures_invalid"),
        (
            lambda evidence: evidence["captures"][0].update({"relation": "wiki_embeddings"}),
            "explain_capture_scope_mismatch",
        ),
        (
            lambda evidence: evidence["captures"][0].update({"plan": {"Plan": {}}}),
            "explain_plan_invalid",
        ),
        (
            lambda evidence: evidence.update(
                {
                    "decision": "representative_hnsw_observed",
                    "hnsw_observed": True,
                    "observed_index_names": ["not_hnsw"],
                }
            ),
            "explain_hnsw_decision_unconfirmed",
        ),
    ),
)
def test_explain_evidence_rejects_unscoped_or_false_hnsw_claims(mutate, error: str) -> None:
    module = _benchmark_module()
    evidence = _explain_evidence()
    mutate(evidence)
    with pytest.raises(module.VerificationError, match=error):
        module._validate_explain_evidence(evidence, order_mode="strict_order", graph_enabled=False)


def test_compare_order_records_rejects_historical_invalid_v4_pair_with_mismatched_git_sha() -> None:
    """The exact defect 04-VERIFICATION.md found: _pins() must include git_sha.

    ``phase-04-rerun-v4-strict-order.json`` (git_sha 6adb0453d9cce3267a4d180e1dd95af65733442d)
    and ``phase-04-rerun-v4-relaxed-order.json`` (git_sha 466205625053b00d785312db84ae9f1c228ae1b2)
    were captured from two different runner revisions. Before the fix, the comparator
    accepted this pair as ``status: ok``; the fix must reject it.
    """
    module = _benchmark_module()
    left = _load(BENCHMARK_RECORDS / "phase-04-rerun-v4-strict-order.json")
    right = _load(BENCHMARK_RECORDS / "phase-04-rerun-v4-relaxed-order.json")
    assert left["git_sha"] == "6adb0453d9cce3267a4d180e1dd95af65733442d"
    assert right["git_sha"] == "466205625053b00d785312db84ae9f1c228ae1b2"
    with pytest.raises(module.VerificationError, match="order_pair_pin_or_policy_mismatch"):
        module.compare_order_records(left, right)


def test_compare_order_records_rejects_matching_order_mode_pair() -> None:
    """A pair sharing one order_mode must be rejected, independent of pin equality.

    This proves the new order-mode-pair assertion is not redundant with the pin
    check: both records here are byte-identical copies (all pins, including
    git_sha, agree) yet still share one order_mode.
    """
    module = _benchmark_module()
    left = _load(BENCHMARK_RECORDS / "phase-04-rerun-v4-graph-off.json")
    right = json.loads(json.dumps(left))
    assert left.get("order_mode") == right.get("order_mode") == "strict_order"
    with pytest.raises(module.VerificationError, match="order_pair_mode_invalid"):
        module.compare_order_records(left, right)


def test_compare_graph_records_still_accepts_historical_valid_v4_graph_pair() -> None:
    """The shared _pins() change must not regress the graph comparator."""
    module = _benchmark_module()
    off = _load(BENCHMARK_RECORDS / "phase-04-rerun-v4-graph-off.json")
    on = _load(BENCHMARK_RECORDS / "phase-04-rerun-v4-graph-on.json")
    assert off["git_sha"] == on["git_sha"] == "466205625053b00d785312db84ae9f1c228ae1b2"
    result = module.compare_graph_records(off, on)
    assert result["status"] == "ok"


# --- #195 B: 융합 방식 비교기 ------------------------------------------------------------------


def _as_best_rank(module, record: dict) -> dict:
    """필드가 생기기 전(v1, 합산) 기록을 같은 핀의 best_rank 기록처럼 바꾼다."""
    after = json.loads(json.dumps(record))
    after["policy_content"]["version"] = "hybrid-rrf-v2"
    after["policy_content"]["same_channel_aggregation"] = "best_rank"
    after["policy_content_sha256"] = module.policy_content_sha256_of(after["policy_content"])
    return after


def _historical_sum_record() -> dict:
    return _load(BENCHMARK_RECORDS / "phase-04-rerun-v4-graph-off.json")


def test_compare_fusion_records_accepts_aggregation_only_pair() -> None:
    module = _benchmark_module()
    before = _historical_sum_record()
    assert "same_channel_aggregation" not in before["policy_content"]  # 없음 = 합산
    result = module.compare_fusion_records(before, _as_best_rank(module, before))
    assert result["status"] == "ok"
    assert set(result) >= {"quality_delta", "recall_delta", "mrr_delta", "underfill_delta"}


def test_compare_fusion_records_rejects_a_second_policy_change() -> None:
    module = _benchmark_module()
    before = _historical_sum_record()
    after = _as_best_rank(module, before)
    after["policy_content"]["rrf_k"] = 30
    after["policy_content_sha256"] = module.policy_content_sha256_of(after["policy_content"])
    with pytest.raises(module.VerificationError, match="fusion_policy_diff_invalid"):
        module.compare_fusion_records(before, after)


def test_compare_fusion_records_rejects_pin_mismatch() -> None:
    module = _benchmark_module()
    before = _historical_sum_record()
    after = _as_best_rank(module, before)
    after["git_sha"] = "0" * 40
    with pytest.raises(module.VerificationError, match="fusion_pair_pin_mismatch"):
        module.compare_fusion_records(before, after)


def test_compare_fusion_records_rejects_reversed_or_unversioned_pair() -> None:
    module = _benchmark_module()
    before = _historical_sum_record()
    after = _as_best_rank(module, before)
    with pytest.raises(module.VerificationError, match="fusion_policy_diff_invalid"):
        module.compare_fusion_records(after, before)
    same_version = json.loads(json.dumps(after))
    same_version["policy_content"]["version"] = before["policy_content"]["version"]
    same_version["policy_content_sha256"] = module.policy_content_sha256_of(
        same_version["policy_content"]
    )
    with pytest.raises(module.VerificationError, match="fusion_policy_diff_invalid"):
        module.compare_fusion_records(before, same_version)


def test_operational_policy_reproduces_v1_version_for_sum_arm() -> None:
    import argparse

    module = _benchmark_module()
    sum_arm = module._operational_policy(argparse.Namespace(graph="off", fusion="sum"))
    best = module._operational_policy(argparse.Namespace(graph="off", fusion="best_rank"))
    assert (sum_arm.version, sum_arm.same_channel_aggregation) == ("hybrid-rrf-v1", "sum")
    assert best.same_channel_aggregation == "best_rank"
    assert module.policy_content(sum_arm)["same_channel_aggregation"] == "sum"


def test_benchmark_embedding_client_accepts_the_service_call_signature() -> None:
    """서비스가 `workspace_id`를 넘겨도 임베딩이 실패하지 않아야 벡터 채널이 측정된다."""
    import asyncio

    module = _benchmark_module()
    vector = asyncio.run(module.BenchmarkEmbeddingClient().embed("질의", workspace_id="ws"))
    assert vector == module.text_vector("질의")


def test_compare_fusion_records_rejects_records_with_failed_channels() -> None:
    module = _benchmark_module()
    before = _historical_sum_record()
    after = _as_best_rank(module, before)
    broken = json.loads(json.dumps(after))
    broken["query_results"][0]["channels"]["wiki_vector"]["status"] = "failed"
    with pytest.raises(module.VerificationError, match="fusion_pair_channel_failure"):
        module.compare_fusion_records(before, broken)
