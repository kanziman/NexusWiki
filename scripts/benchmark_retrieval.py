#!/usr/bin/env python3
"""Append-only full-path retrieval benchmark for the controlled local corpus."""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import subprocess
import sys
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from uuid import UUID, uuid5

from api.services.retrieval import RetrievalService
from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY, POLICY_VERSION

import importlib.util

_spec = importlib.util.spec_from_file_location("generate_retrieval_benchmark_corpus", Path(__file__).with_name("generate_retrieval_benchmark_corpus.py")); assert _spec and _spec.loader
_generator = importlib.util.module_from_spec(_spec); sys.modules[_spec.name] = _generator; _spec.loader.exec_module(_generator)
MANIFEST_PATH, canonical_hash, identity, load_manifest, loader_sql, load_corpus, logical_id_map, text_vector = (_generator.MANIFEST_PATH, _generator.canonical_hash, _generator.identity, _generator.load_manifest, _generator.loader_sql, _generator.load_corpus, _generator.logical_id_map, _generator.text_vector)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "packages/core/tests/fixtures/retrieval"; CORPUS_PATH = FIXTURE_DIR / "representative_corpus.v1.json"; GOLDEN_PATH = FIXTURE_DIR / "golden_queries.v1.json"; NS = UUID("87f8d58f-61a8-4f57-94d3-1c3da5be7e04")
CHANNELS = ("wiki_vector", "source_vector", "wiki_lexical", "source_lexical", "graph")


class VerificationError(ValueError): pass


def _load_json(path: Path) -> dict:
    try: return json.loads(path.read_text())
    except Exception as error: raise VerificationError(f"unreadable_input:{path}") from error


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def policy_content(policy=DEFAULT_RETRIEVAL_POLICY) -> dict:
    values = {name: getattr(policy, name) for name in ("version", "rrf_k", "channel_weights", "channel_overfetch", "requested_k", "vector_sql_max_candidates", "lexical_sql_max_candidates", "graph_enabled", "graph_weight", "graph_seed_limit", "graph_depth", "graph_fanout", "graph_total_limit")}
    values["channel_weights"] = dict(values["channel_weights"])
    values["channel_overfetch"] = dict(values["channel_overfetch"])
    return values


def policy_content_sha256(policy=DEFAULT_RETRIEVAL_POLICY) -> str:
    return hashlib.sha256(_canonical(policy_content(policy)).encode()).hexdigest()


def benchmark_workspace(manifest: dict) -> UUID:
    """One controlled dataset identity, shared by every comparable arm."""
    return uuid5(NS, f"{manifest['sha256']}:controlled-retrieval-workspace-v1")


def _validate_inputs(corpus: dict, golden: dict) -> None:
    if corpus.get("version") != "representative-corpus-v1" or corpus.get("sha256") != canonical_hash(corpus): raise VerificationError("corpus_hash_or_version_mismatch")
    if golden.get("version") != "golden-queries-v1" or golden.get("sha256") != canonical_hash(golden): raise VerificationError("golden_hash_or_version_mismatch")
    if (golden.get("corpus_version"), golden.get("corpus_sha256")) != (corpus["version"], corpus["sha256"]): raise VerificationError("golden_corpus_pin_mismatch")
    evidence = {f"source:{row['id']}" for row in corpus["source_chunks"]} | {f"wiki:{row['id']}" for row in corpus["wiki_pages"]}
    if not 30 <= len(golden.get("queries", [])) <= 50: raise VerificationError("golden_query_count_invalid")
    for query in golden["queries"]:
        if not isinstance(query.get("query"), str) or not query["query"] or query.get("language") not in {"ko", "en", "mixed"}: raise VerificationError("golden_query_input_invalid")
        labels = query.get("required_evidence")
        if not isinstance(labels, list) or not labels or not {label.get("id") for label in labels} <= evidence: raise VerificationError("golden_required_evidence_invalid")
        required = {label["id"] for label in labels}
        if any(not isinstance(item, dict) or item.get("for") not in required or item.get("id") not in evidence or item.get("id") in required for item in query.get("allowed_alternatives", [])): raise VerificationError("golden_alternative_invalid")


def _evaluate_query(query: dict, ranked: list[str]) -> dict:
    positions = {value: index for index, value in enumerate(ranked, 1)}; checks = []
    for label in query["required_evidence"]:
        candidates = [label["id"]] + [item["id"] for item in query.get("allowed_alternatives", []) if item["for"] == label["id"]]
        rank = min((positions[item] for item in candidates if item in positions), default=None)
        checks.append({"required_id": label["id"], "rank": rank, "max_rank": label["max_rank"], "passed": rank is not None and rank <= label["max_rank"]})
    return {"id": query["id"], "passed": all(item["passed"] for item in checks), "checks": checks}


class BenchmarkEmbeddingClient:
    async def embed(self, text: str) -> list[float]: return text_vector(text)


def _sql_literal(value: object) -> str:
    if isinstance(value, list): return "array[" + ",".join(_sql_literal(item) for item in value) + "]::uuid[]"
    if isinstance(value, int): return str(value)
    return "'" + str(value).replace("'", "''") + "'"


class LocalRetrievalDb:
    """A tiny async RPC adapter.  It calls the deployed SQL functions directly.

    The relaxed vector path is deliberately a controlled caller-session query;
    the regular strict path invokes the immutable deployed function unchanged.
    """
    def __init__(self, container: str, order_mode: str) -> None: self.container, self.order_mode, self.calls = container, order_mode, []
    def _run(self, sql: str) -> list[dict]:
        result = subprocess.run(["docker", "exec", "-i", self.container, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", "postgres", "-At"], input=sql, text=True, capture_output=True)
        if result.returncode: raise RuntimeError(result.stderr[-1000:])
        line = result.stdout.strip()
        # Mutation/cleanup statements intentionally have no JSON result.
        return json.loads(line) if line.startswith(("[", "{")) else []
    async def rpc(self, function: str, *, params: dict[str, object]) -> list[dict]:
        self.calls.append((function, params)); workspace = _sql_literal(params["p_workspace_id"])
        if function in {"search_chunks", "search_wiki_embeddings"} and self.order_mode == "relaxed_order":
            table, fields = ("source_chunks", "id, raw_source_id, chunk_index") if function == "search_chunks" else ("wiki_embeddings", "id, wiki_id, chunk_index, chunk_content")
            vector = "'[' || array_to_string(array[" + ",".join(str(float(x)) for x in params["p_query"]) + "], ',') || ']'"
            sql = f"begin; set local hnsw.iterative_scan='relaxed_order'; set local hnsw.ef_search='200'; set local hnsw.max_scan_tuples='40000'; select coalesce(jsonb_agg(to_jsonb(row)), '[]'::jsonb) from (select {fields} from public.{table} where workspace_id={workspace}::uuid and embedding is not null order by embedding operator(extensions.<=>) ({vector})::extensions.vector(1024) limit least(greatest({_sql_literal(params['p_k'])},1),100)) row; commit;"
        else:
            def argument(key: str, value: object) -> str:
                if key == "p_query":
                    return "('[' || array_to_string(array[" + ",".join(str(float(item)) for item in value) + "], ',') || ']')::extensions.vector(1024)"
                return _sql_literal(value)
            arguments = ",".join(f"{key} => {argument(key, value)}" for key, value in params.items())
            sql = f"select coalesce(jsonb_agg(to_jsonb(row)), '[]'::jsonb) from (select * from public.{function}({arguments})) row;"
        return await asyncio.to_thread(self._run, sql)


def _channel_record(meta: dict, uuid_to_logical: dict[str, str]) -> dict:
    result = dict(meta); raw = result.get("raw_hit_ids", [])
    result["raw_uuid_ids"] = raw; result["logical_ids"] = [uuid_to_logical.get(value, value) for value in raw]
    return result


def _metrics(results: list[dict]) -> dict:
    evaluations = [item["evaluation"] for item in results]; total_checks = [check for item in evaluations for check in item["checks"]]
    ranks = [check["rank"] for check in total_checks if check["rank"] is not None]
    latencies = sorted(item["total_latency_ms"] for item in results); n = len(latencies)
    channels = {name: [item["channels"][name] for item in results] for name in CHANNELS}
    return {"recall_at_k": sum(check["passed"] for check in total_checks) / len(total_checks), "strict_query_pass_rate": sum(item["passed"] for item in evaluations) / len(evaluations), "mrr": sum(1 / rank for rank in ranks) / len(total_checks), "mean_required_rank": sum(ranks) / len(ranks) if ranks else None, "channel_hits": {name: sum(channel["returned"] for channel in rows) for name, rows in channels.items()}, "channel_contribution": {name: sum(channel.get("contribution", 0) for channel in rows) for name, rows in channels.items()}, "latency_ms": {"p50_total": median(latencies), "p95_total": latencies[min(n - 1, round((n - 1) * .95))]}, "underfill": {"queries": sum(item["underfill"] for item in results), "rate": sum(item["underfill"] for item in results) / len(results), "by_channel": {name: sum(channel["underfill"] for channel in rows) for name, rows in channels.items()}}}


def _validate_record(record: dict) -> None:
    if record.get("run_kind") != "full_path_retrieval_measurement" or record.get("order_mode") == "not_measured_fixture_adapter": raise VerificationError("not_measured_fixture_adapter")
    if record.get("policy_content_sha256") != hashlib.sha256(_canonical(record.get("policy_content")).encode()).hexdigest(): raise VerificationError("policy_content_sha_mismatch")
    for result in record.get("query_results", []):
        if set(result.get("channels", {})) != set(CHANNELS): raise VerificationError("missing_five_channel_envelopes")
        if "evaluation" not in result or not _observed_retrieval_result(result): raise VerificationError("fabricated_or_label_only_evaluation")


def _observed_retrieval_result(result: dict) -> bool:
    """Recognize a serialized RetrievalService observation, including an empty ranking.

    The explicit provenance marker and complete channel envelopes are emitted in the
    same loop that calls ``RetrievalService.retrieve``.  Labels are deliberately
    absent from this check, so a label-only evaluation cannot masquerade as an
    observed empty result.
    """
    if result.get("retrieval_observation") != "retrieval_service_channel_envelopes_v1":
        return False
    ranked = result.get("ranked_uuid_evidence")
    if not isinstance(ranked, list) or not all(isinstance(item, str) for item in ranked):
        return False
    for channel in result["channels"].values():
        if not isinstance(channel, dict) or not {"status", "requested", "returned", "underfill", "raw_uuid_ids", "logical_ids", "contribution"} <= set(channel):
            return False
        raw = channel["raw_uuid_ids"]
        if not isinstance(raw, list) or channel["returned"] != len(raw):
            return False
        if channel["underfill"] != (channel["returned"] < channel["requested"]):
            return False
    return True


def _fixture(corpus: dict, golden: dict, overrides: dict[str, list[str]] | None = None) -> dict:
    evaluations = [_evaluate_query(query, (overrides or {}).get(query["id"], [label["id"] for label in query["required_evidence"]])) for query in golden["queries"]]
    if not all(item["passed"] for item in evaluations): raise VerificationError("evaluation_failed")
    return {"record_schema": "retrieval-benchmark-v3", "run_kind": "fixture_contract_verification", "policy_version": POLICY_VERSION, "policy_content": policy_content(), "policy_content_sha256": policy_content_sha256(), "order_mode": "not_measured_fixture_adapter", "graph_enabled": False, "corpus_sha256": corpus["sha256"], "golden_sha256": golden["sha256"], "evaluations": evaluations, "metrics": {"recall_at_k": 1.0, "strict_query_pass_rate": 1.0, "mrr": 1.0, "mean_required_rank": 1.0, "channel_hits": {}, "channel_contribution": {}, "latency_ms": {"p50_total": 0.0, "p95_total": 0.0}, "underfill": {"queries": 0, "rate": 0.0, "by_channel": {}}, "graph_delta": {"status": "not_measured_fixture_adapter"}}}


def operational(args, corpus: dict, golden: dict) -> dict:
    manifest = load_manifest(); workspace = benchmark_workspace(manifest); cleanup = loader_sql(manifest, workspace, True)
    if args.output.exists(): raise VerificationError("refusing_to_overwrite_prior_record")
    try:
        # A prior interrupted arm may have left only this deterministic workspace;
        # remove it before loading, never broad workspace data.
        LocalRetrievalDb(args.db_container, args.order_mode)._run(cleanup)
        LocalRetrievalDb(args.db_container, args.order_mode)._run(loader_sql(manifest, workspace))
        mapping = logical_id_map(manifest, corpus); reverse = {value: key for key, value in mapping.items()}
        policy = replace(DEFAULT_RETRIEVAL_POLICY, graph_enabled=args.graph == "on")
        service = RetrievalService(BenchmarkEmbeddingClient(), policy=policy); db = LocalRetrievalDb(args.db_container, args.order_mode); results = []
        for query in golden["queries"]:
            started = time.perf_counter(); response = asyncio.run(service.retrieve(workspace, query["query"], query["requested_k"], db)); elapsed = round((time.perf_counter() - started) * 1000, 3)
            ranked_uuid = [hit.document_id if hit.kind == "wiki" else hit.evidence_id for hit in response.evidence]; ranked_logical = [reverse.get(item, item) for item in ranked_uuid]
            channels = {name: _channel_record(response.meta[name], reverse) for name in CHANNELS}
            results.append({"query_id": query["id"], "query_text": query["query"], "language": query["language"], "retrieval_observation": "retrieval_service_channel_envelopes_v1", "ranked_uuid_evidence": ranked_uuid, "ranked_logical_evidence": ranked_logical, "evaluation": _evaluate_query(query, ranked_logical), "total_latency_ms": elapsed, "underfill": response.meta["underfill"], "channels": channels})
        record = {"record_schema": "retrieval-benchmark-v3", "run_kind": "full_path_retrieval_measurement", "timestamp": datetime.now(UTC).isoformat(), "git_sha": subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(), "policy_version": POLICY_VERSION, "policy_content": policy_content(policy), "policy_content_sha256": policy_content_sha256(policy), "corpus_version": corpus["version"], "corpus_sha256": corpus["sha256"], "golden_version": golden["version"], "golden_sha256": golden["sha256"], "benchmark_manifest_sha256": manifest["sha256"], "generator_seed": manifest["seed"], "raw_workspace_uuid": str(workspace), "logical_id_to_uuid": mapping, "embedding_model_version": "fixture-token-hash-l2-v1", "database_identity": args.db_container, "repeat_count": args.repeat_count, "order_mode": args.order_mode, "graph_enabled": args.graph == "on", "query_results": results, "metrics": _metrics(results)}
        _validate_record(record); return record
    finally:
        try: LocalRetrievalDb(args.db_container, args.order_mode)._run(cleanup)
        except Exception: pass


def _pins(record: dict) -> dict: return {key: record.get(key) for key in ("corpus_sha256", "golden_sha256", "benchmark_manifest_sha256", "generator_seed", "raw_workspace_uuid", "embedding_model_version", "database_identity", "repeat_count")}
def compare_order_records(left: dict, right: dict) -> dict:
    _validate_record(left); _validate_record(right)
    if _pins(left) != _pins(right) or left["policy_content"] != right["policy_content"] or left["policy_content_sha256"] != right["policy_content_sha256"]: raise VerificationError("order_pair_pin_or_policy_mismatch")
    return {"status": "ok", "quality_delta": right["metrics"]["strict_query_pass_rate"] - left["metrics"]["strict_query_pass_rate"]}
def compare_graph_records(off: dict, on: dict) -> dict:
    _validate_record(off); _validate_record(on)
    if _pins(off) != _pins(on): raise VerificationError("graph_pair_pin_mismatch")
    a, b = dict(off["policy_content"]), dict(on["policy_content"]); a.pop("graph_enabled", None); b.pop("graph_enabled", None)
    if off["policy_content"].get("graph_enabled") or not on["policy_content"].get("graph_enabled") or a != b: raise VerificationError("graph_policy_diff_invalid")
    return {"status": "ok", "quality_delta": on["metrics"]["strict_query_pass_rate"] - off["metrics"]["strict_query_pass_rate"], "contribution_delta": on["metrics"]["channel_contribution"]["graph"] - off["metrics"]["channel_contribution"]["graph"], "underfill_delta": on["metrics"]["underfill"]["queries"] - off["metrics"]["underfill"]["queries"], "latency_ms_delta": on["metrics"]["latency_ms"]["p50_total"] - off["metrics"]["latency_ms"]["p50_total"]}


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command")
    for name in ("compare-order-records", "compare-graph-records"):
        item = sub.add_parser(name); item.add_argument("--left" if name.startswith("compare-order") else "--off", type=Path, required=True); item.add_argument("--right" if name.startswith("compare-order") else "--on", type=Path, required=True)
    parser.add_argument("--verify", action="store_true"); parser.add_argument("--fixture-results", type=Path); parser.add_argument("--output", type=Path); parser.add_argument("--order-mode", choices=("strict_order", "relaxed_order")); parser.add_argument("--graph", choices=("off", "on")); parser.add_argument("--repeat-count", type=int, default=3); parser.add_argument("--db-container", default="supabase_db_NexusWiki"); parser.add_argument("--run-id", default="phase-04")
    args = parser.parse_args()
    try:
        if args.command == "compare-order-records": output = compare_order_records(_load_json(args.left), _load_json(args.right))
        elif args.command == "compare-graph-records": output = compare_graph_records(_load_json(args.off), _load_json(args.on))
        else:
            corpus, golden = _load_json(CORPUS_PATH), _load_json(GOLDEN_PATH); _validate_inputs(corpus, golden)
            if args.verify:
                fixture_rows = _load_json(args.fixture_results).get("queries") if args.fixture_results else None
                if fixture_rows is not None and not isinstance(fixture_rows, dict): raise VerificationError("fixture_results_invalid")
                output = _fixture(corpus, golden, fixture_rows)
            else:
                if not args.order_mode or not args.graph: raise VerificationError("operational_arguments_invalid")
                output = operational(args, corpus, golden)
            if args.output:
                if args.output.exists(): raise VerificationError("refusing_to_overwrite_prior_record")
                args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(output, ensure_ascii=False))
    except VerificationError as error: print(error, file=sys.stderr); return 2
    return 0

if __name__ == "__main__": raise SystemExit(main())
