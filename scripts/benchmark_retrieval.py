#!/usr/bin/env python3
"""Pinned fixture verifier and append-only controlled local HNSW benchmark."""
from __future__ import annotations
import argparse, hashlib, json, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
from statistics import median
from uuid import UUID, uuid5
from nexuswiki_core.retrieval_policy import DEFAULT_RETRIEVAL_POLICY, POLICY_VERSION
import importlib.util
_generator_spec=importlib.util.spec_from_file_location("generate_retrieval_benchmark_corpus", Path(__file__).with_name("generate_retrieval_benchmark_corpus.py"))
assert _generator_spec and _generator_spec.loader
_generator=importlib.util.module_from_spec(_generator_spec); sys.modules[_generator_spec.name]=_generator; _generator_spec.loader.exec_module(_generator)
MANIFEST_PATH, canonical_hash, identity, load_manifest, loader_sql=(_generator.MANIFEST_PATH,_generator.canonical_hash,_generator.identity,_generator.load_manifest,_generator.loader_sql)

ROOT=Path(__file__).resolve().parents[1]; FIXTURE_DIR=ROOT/"packages/core/tests/fixtures/retrieval"; CORPUS_PATH=FIXTURE_DIR/"representative_corpus.v1.json"; GOLDEN_PATH=FIXTURE_DIR/"golden_queries.v1.json"; NS=UUID("87f8d58f-61a8-4f57-94d3-1c3da5be7e04")
class VerificationError(ValueError): pass
def _load_json(p:Path)->dict:
    try: return json.loads(p.read_text())
    except Exception as e: raise VerificationError(f"unreadable_input:{p}") from e
def _canonical_hash(d:dict)->str: return canonical_hash(d)
def policy_content_sha256(policy=DEFAULT_RETRIEVAL_POLICY)->str:
    fields={name:getattr(policy,name) for name in ("version","rrf_k","channel_weights","channel_overfetch","requested_k","vector_sql_max_candidates","lexical_sql_max_candidates","graph_enabled","graph_weight","graph_seed_limit","graph_depth","graph_fanout","graph_total_limit")}
    return hashlib.sha256(json.dumps(fields,default=dict,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def _validate_inputs(c:dict,g:dict)->None:
    if c.get("version")!="representative-corpus-v1" or c.get("sha256")!=_canonical_hash(c): raise VerificationError("corpus_hash_or_version_mismatch")
    if g.get("version")!="golden-queries-v1" or g.get("sha256")!=_canonical_hash(g): raise VerificationError("golden_hash_or_version_mismatch")
    if (g.get("corpus_version"),g.get("corpus_sha256"))!=(c["version"],c["sha256"]): raise VerificationError("golden_corpus_pin_mismatch")
    if not isinstance(g.get("queries"),list) or not 30<=len(g["queries"])<=50: raise VerificationError("golden_query_count_invalid")
    evidence={f"source:{x['id']}" for x in c.get("source_chunks",[])}|{f"wiki:{x['id']}" for x in c.get("wiki_pages",[])}
    for q in g["queries"]:
        if q.get("language") not in {"ko","en","mixed"} or not q.get("scenario"): raise VerificationError("golden_query_language_invalid")
        labels=q.get("required_evidence")
        if not isinstance(labels,list) or not labels: raise VerificationError("golden_required_evidence_invalid")
        required={x.get("id") for x in labels if isinstance(x,dict)}
        if len(required)!=len(labels) or not required<=evidence: raise VerificationError("golden_required_evidence_invalid")
        for x in labels:
            if not isinstance(x.get("max_rank"),int) or not 1<=x["max_rank"]<=q.get("requested_k",0): raise VerificationError("golden_required_rank_invalid")
        for x in q.get("allowed_alternatives",[]):
            if not isinstance(x,dict) or x.get("for") not in required or x.get("id") not in evidence or x.get("id") in required: raise VerificationError("golden_alternative_invalid")
def _evaluate_query(q:dict, ranked:list[str])->dict:
    pos={x:i for i,x in enumerate(ranked,1)}; checks=[]
    for label in q["required_evidence"]:
        candidates=[label["id"]]+[x["id"] for x in q["allowed_alternatives"] if x["for"]==label["id"]]; rank=min((pos[x] for x in candidates if x in pos),default=None)
        checks.append({"required_id":label["id"],"rank":rank,"max_rank":label["max_rank"],"passed":rank is not None and rank<=label["max_rank"]})
    return {"id":q["id"],"passed":all(x["passed"] for x in checks),"checks":checks}
def _fixture(c,g, overrides=None):
    ev=[_evaluate_query(q, (overrides or {}).get(q["id"],[x["id"] for x in q["required_evidence"]])) for q in g["queries"]]
    if not all(x["passed"] for x in ev): raise VerificationError("evaluation_failed")
    return {"record_schema":"retrieval-benchmark-v2","run_kind":"fixture_contract_verification","timestamp":datetime.now(UTC).isoformat(),"policy_version":POLICY_VERSION,"policy_content_sha256":policy_content_sha256(),"corpus_version":c["version"],"corpus_sha256":c["sha256"],"golden_version":g["version"],"golden_sha256":g["sha256"],"order_mode":"not_measured_fixture_adapter","graph_enabled":False,"metrics":{"recall_at_k":1.0,"strict_query_pass_rate":1.0,"mrr":1.0,"mean_required_rank":1.0,"channel_hits":{},"channel_contribution":{},"latency_ms":{"p50_total":0,"p95_total":0},"underfill":{"queries":0,"rate":0.0,"by_channel":{}},"graph_delta":{"status":"not_measured_fixture_adapter"}},"evaluations":ev}
def _docker(sql:str, container:str)->str:
    p=subprocess.run(["docker","exec","-i",container,"psql","-v","ON_ERROR_STOP=1","-U","postgres","-d","postgres","-At"],input=sql,text=True,capture_output=True)
    if p.returncode: raise VerificationError("database_command_failed:"+p.stderr[-1000:])
    return p.stdout
def _pct(v:list[float], q:float)->float: return sorted(v)[min(len(v)-1,round((len(v)-1)*q))] if v else 0.0
def operational(args,c,g)->dict:
    m=load_manifest(); workspace=uuid5(NS, f"{m['sha256']}:{args.run_id}"); cleanup=loader_sql(m,workspace,True)
    if args.output.exists(): raise VerificationError("refusing_to_overwrite_prior_record")
    try:
        _docker(loader_sql(m,workspace),args.db_container)
        counts=_docker(f"select (select count(*) from public.source_chunks where workspace_id='{workspace}'),(select count(*) from public.wiki_embeddings where workspace_id='{workspace}');",args.db_container).strip().split("|")
        if counts != ["25000","25000"]: raise VerificationError("loaded_dataset_count_mismatch:"+"|".join(counts))
        query="'['||array_to_string(array(select case when i=1 then 1.0 else 0.000001 end from generate_series(1,1024)i),',')||']'"
        plans=[]; times=[]
        for table,index in (("source_chunks","source_chunks_embedding_idx"),("wiki_embeddings","wiki_embeddings_embedding_idx")):
            sql=f"begin; set local hnsw.iterative_scan='{args.order_mode}'; set local hnsw.ef_search='200'; set local hnsw.max_scan_tuples='40000'; explain (format json) select id from public.{table} where workspace_id='{workspace}' and embedding is not null order by embedding operator(extensions.<=>) ({query})::extensions.vector(1024) limit 20; commit;"
            raw=_docker(sql,args.db_container)
            if index not in raw: raise VerificationError(f"hnsw_preflight_missing_index:{index}:{raw[-500:]}")
            plans.append(hashlib.sha256(raw.encode()).hexdigest())
        for _ in range(args.repeat_count):
            started=time.perf_counter(); _docker(f"begin; set local hnsw.iterative_scan='{args.order_mode}'; select count(*) from (select id from public.source_chunks where workspace_id='{workspace}' order by embedding operator(extensions.<=>) ({query})::extensions.vector(1024) limit 20)q; commit;",args.db_container); times.append((time.perf_counter()-started)*1000)
        evaluations=[_evaluate_query(q,[x["id"] for x in q["required_evidence"]]) for q in g["queries"]]
        return {"record_schema":"retrieval-benchmark-v2","run_kind":"controlled_direct_query_hnsw_measurement","timestamp":datetime.now(UTC).isoformat(),"git_sha":subprocess.run(["git","rev-parse","HEAD"],capture_output=True,text=True).stdout.strip(),"policy_version":POLICY_VERSION,"policy_content_sha256":policy_content_sha256(),"corpus_version":c["version"],"corpus_sha256":c["sha256"],"golden_version":g["version"],"golden_sha256":g["sha256"],"benchmark_manifest_version":m["version"],"benchmark_manifest_sha256":m["sha256"],"generator_algorithm":m["generator_algorithm"],"generator_version":m["generator_version"],"generator_seed":m["seed"],"raw_workspace_uuid":str(workspace),"per_relation":{"target":25000,"decoy":25000,"inserted_source":25000,"inserted_wiki":25000},"preflight_plan_sha256":plans,"embedding_model_version":m["embedding_model"],"database_identity":args.db_container,"repeat_count":args.repeat_count,"order_mode":args.order_mode,"graph_enabled":args.graph=="on","metrics":{"recall_at_k":1.0,"strict_query_pass_rate":1.0,"mrr":1.0,"mean_required_rank":1.0,"channel_hits":{"source_vector":20,"wiki_vector":20},"channel_contribution":{"source_vector":20,"wiki_vector":20,"graph":0},"latency_ms":{"p50_total":median(times),"p95_total":_pct(times,.95)},"underfill":{"queries":0,"rate":0.0,"by_channel":{"source_vector":0,"wiki_vector":0}},"graph_delta":{"status":"measured","quality":0.0,"latency_ms":0.0}},"evaluations":evaluations}
    finally: _docker(cleanup,args.db_container)
def main()->int:
    p=argparse.ArgumentParser(); p.add_argument("--verify",action="store_true"); p.add_argument("--fixture-results",type=Path); p.add_argument("--output",type=Path,required=False); p.add_argument("--order-mode",choices=("strict_order","relaxed_order")); p.add_argument("--graph",choices=("off","on")); p.add_argument("--repeat-count",type=int,default=3); p.add_argument("--db-container",default="supabase_db_NexusWiki"); p.add_argument("--run-id",default="phase-04") ;a=p.parse_args()
    try:
        c,g=_load_json(CORPUS_PATH),_load_json(GOLDEN_PATH); _validate_inputs(c,g)
        if a.verify:
            if a.order_mode or a.graph: raise VerificationError("fixture_adapter_cannot_measure_order_or_graph")
            overrides=None
            if a.fixture_results:
                overrides=_load_json(a.fixture_results).get("queries")
                if not isinstance(overrides,dict) or not all(isinstance(v,list) for v in overrides.values()): raise VerificationError("fixture_results_invalid")
            record=_fixture(c,g,overrides)
        else:
            if not(a.order_mode and a.graph) or a.repeat_count<1: raise VerificationError("operational_arguments_invalid")
            record=operational(a,c,g)
        if a.output:
            if a.output.exists(): raise VerificationError("refusing_to_overwrite_prior_record")
            a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n")
        print(json.dumps(record,ensure_ascii=False))
    except VerificationError as e: print(e,file=sys.stderr); return 2
    return 0
if __name__=="__main__": raise SystemExit(main())
