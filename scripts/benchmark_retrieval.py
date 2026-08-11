#!/usr/bin/env python3
"""Fail-closed evaluator for the pinned hybrid-retrieval golden set.

The default ``--verify`` adapter is deliberately local and deterministic: it
loads only the repository fixture and evaluates an evidence-ranked fixture
baseline. It is a contract gate, not an HNSW tuning result. Operational order
and graph decisions require the separate local-Supabase benchmark preconditions
recorded in the Phase 04 plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from typing import Any

from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY, POLICY_VERSION

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "packages/core/tests/fixtures/retrieval"
CORPUS_PATH = FIXTURE_DIR / "representative_corpus.v1.json"
GOLDEN_PATH = FIXTURE_DIR / "golden_queries.v1.json"


class VerificationError(ValueError):
    """Pinned benchmark input or evaluation was not trustworthy."""


def _canonical_hash(document: dict[str, Any]) -> str:
    payload = {key: value for key, value in document.items() if key != "sha256"}
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise VerificationError(f"unreadable_input:{path}") from exc
    if not isinstance(value, dict):
        raise VerificationError(f"invalid_document:{path}")
    return value


def _validate_inputs(corpus: dict[str, Any], golden: dict[str, Any]) -> None:
    if corpus.get("version") != "representative-corpus-v1" or corpus.get(
        "sha256"
    ) != _canonical_hash(corpus):
        raise VerificationError("corpus_hash_or_version_mismatch")
    if golden.get("version") != "golden-queries-v1" or golden.get("sha256") != _canonical_hash(
        golden
    ):
        raise VerificationError("golden_hash_or_version_mismatch")
    if (
        golden.get("corpus_version") != corpus["version"]
        or golden.get("corpus_sha256") != corpus["sha256"]
    ):
        raise VerificationError("golden_corpus_pin_mismatch")
    queries = golden.get("queries")
    if not isinstance(queries, list) or not 30 <= len(queries) <= 50:
        raise VerificationError("golden_query_count_invalid")
    languages = {query.get("language") for query in queries if isinstance(query, dict)}
    if not {"ko", "en", "mixed"} <= languages:
        raise VerificationError("golden_language_mix_invalid")
    evidence_ids = {
        f"source:{item.get('id')}" for item in corpus.get("source_chunks", [])
    } | {f"wiki:{item.get('id')}" for item in corpus.get("wiki_pages", [])}
    for query in queries:
        if not isinstance(query, dict) or query.get("language") not in {"ko", "en", "mixed"}:
            raise VerificationError("golden_query_language_invalid")
        if not isinstance(query.get("scenario"), str) or not query["scenario"].strip():
            raise VerificationError("golden_query_scenario_invalid")
        requested_k = query.get("requested_k")
        labels = query.get("required_evidence")
        alternatives = query.get("allowed_alternatives")
        if not isinstance(requested_k, int) or requested_k <= 0:
            raise VerificationError("golden_requested_k_invalid")
        if not isinstance(labels, list) or not labels:
            raise VerificationError("golden_required_evidence_invalid")
        if not isinstance(alternatives, list):
            raise VerificationError("golden_alternatives_invalid")
        required_ids: set[str] = set()
        for label in labels:
            if not isinstance(label, dict) or label.get("id") not in evidence_ids:
                raise VerificationError("golden_required_evidence_invalid")
            rank = label.get("max_rank")
            if not isinstance(rank, int) or not 1 <= rank <= requested_k:
                raise VerificationError("golden_required_rank_invalid")
            required_ids.add(label["id"])
        for alternative in alternatives:
            if (
                not isinstance(alternative, dict)
                or alternative.get("for") not in required_ids
                or alternative.get("id") not in evidence_ids
                or alternative["id"] in required_ids
            ):
                raise VerificationError("golden_alternative_invalid")
    if DEFAULT_RETRIEVAL_POLICY.version != POLICY_VERSION:
        raise VerificationError("policy_version_mismatch")


def _baseline_results(golden: dict[str, Any]) -> dict[str, list[str]]:
    """Local fixture adapter: each reviewed label is returned at its threshold.

    This exercises every golden predicate without pretending the result is an
    operational database/HNSW comparison.
    """
    return {
        query["id"]: [label["id"] for label in query["required_evidence"]]
        for query in golden["queries"]
    }


def _evaluate_query(query: dict[str, Any], ranked_ids: list[str]) -> dict[str, Any]:
    positions = {evidence_id: index for index, evidence_id in enumerate(ranked_ids, start=1)}
    checks: list[dict[str, Any]] = []
    for label in query["required_evidence"]:
        permitted = [label["id"]] + [
            alternative["id"]
            for alternative in query["allowed_alternatives"]
            if alternative["for"] == label["id"]
        ]
        ranks = [positions[candidate] for candidate in permitted if candidate in positions]
        rank = min(ranks) if ranks else None
        checks.append(
            {
                "required_id": label["id"],
                "rank": rank,
                "max_rank": label["max_rank"],
                "passed": rank is not None
                and rank <= query["requested_k"]
                and rank <= label["max_rank"],
            }
        )
    return {"id": query["id"], "passed": all(check["passed"] for check in checks), "checks": checks}


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * percentile))
    return ordered[index]


def _git_sha() -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],  # noqa: S607 -- git is a required repository tool
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() or None


def _record(
    corpus: dict[str, Any], golden: dict[str, Any], evaluations: list[dict[str, Any]]
) -> dict[str, Any]:
    labels = [check for evaluation in evaluations for check in evaluation["checks"]]
    found = [check for check in labels if check["rank"] is not None]
    ranks = [check["rank"] for check in found]
    query_count = len(evaluations)
    channels = {
        "wiki_vector": 0,
        "source_vector": 0,
        "wiki_lexical": 0,
        "source_lexical": 0,
        "graph": 0,
    }
    for evaluation in evaluations:
        for check in evaluation["checks"]:
            if check["required_id"].startswith("wiki:"):
                channels["wiki_lexical"] += int(check["passed"])
            else:
                channels["source_lexical"] += int(check["passed"])
    latencies = [0.0 for _ in evaluations]
    return {
        "record_schema": "retrieval-benchmark-v1",
        "timestamp": datetime.now(UTC).isoformat(),
        "run_kind": "fixture_contract_verification",
        "git_sha": _git_sha(),
        "policy_version": POLICY_VERSION,
        "corpus_version": corpus["version"],
        "corpus_sha256": corpus["sha256"],
        "golden_version": golden["version"],
        "golden_sha256": golden["sha256"],
        "embedding_model_version": "fixture-oracle-v1",
        "requested_k": max(query["requested_k"] for query in golden["queries"]),
        "returned_limit": max(query["requested_k"] for query in golden["queries"]),
        "order_mode": "not_measured_fixture_adapter",
        "graph_enabled": False,
        "metrics": {
            "recall_at_k": len(found) / len(labels) if labels else 0.0,
            "strict_query_pass_rate": sum(item["passed"] for item in evaluations) / query_count,
            "mrr": sum(1 / rank for rank in ranks) / len(labels) if labels else 0.0,
            "mean_required_rank": sum(ranks) / len(ranks) if ranks else None,
            "channel_hits": channels,
            "channel_contribution": channels,
            "latency_ms": {
                "p50_total": median(latencies),
                "p95_total": _percentile(latencies, 0.95),
                "per_channel": {name: {"p50": 0.0, "p95": 0.0} for name in channels},
            },
            "underfill": {"queries": 0, "rate": 0.0, "by_channel": {name: 0 for name in channels}},
            "graph_delta": {
                "quality": 0.0,
                "latency_ms": 0.0,
                "status": "not_measured_fixture_adapter",
            },
        },
        "evaluations": evaluations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--verify", action="store_true", help="validate and evaluate the pinned fixture"
    )
    parser.add_argument(
        "--fixture-results", type=Path, help="ranked fixture evidence overrides for tests"
    )
    parser.add_argument("--output", type=Path, help="write an immutable JSON record")
    args = parser.parse_args()
    if not args.verify:
        parser.error(
            "--verify is required; operational comparisons require the local Supabase harness"
        )
    try:
        corpus, golden = _load_json(CORPUS_PATH), _load_json(GOLDEN_PATH)
        _validate_inputs(corpus, golden)
        results = _baseline_results(golden)
        if args.fixture_results:
            override = _load_json(args.fixture_results).get("queries")
            if not isinstance(override, dict):
                raise VerificationError("fixture_results_invalid")
            for query_id, ranked in override.items():
                if (
                    not isinstance(query_id, str)
                    or not isinstance(ranked, list)
                    or not all(isinstance(item, str) for item in ranked)
                ):
                    raise VerificationError("fixture_results_invalid")
                results[query_id] = ranked
        evaluations = [_evaluate_query(query, results[query["id"]]) for query in golden["queries"]]
        if not all(item["passed"] for item in evaluations):
            raise VerificationError("evaluation_failed")
        record = _record(corpus, golden, evaluations)
        rendered = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
        if args.output:
            if args.output.exists():
                raise VerificationError("refusing_to_overwrite_prior_record")
            args.output.write_text(rendered)
        print(rendered, end="")
    except VerificationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
