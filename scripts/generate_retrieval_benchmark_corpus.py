#!/usr/bin/env python3
"""Deterministic manifest validator and SQL loader for controlled HNSW runs."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "packages/core/tests/fixtures/retrieval/benchmark_hnsw_corpus.v1.json"
NAMESPACE = UUID("6e786575-7377-696b-692d-62656e636830")

def canonical_hash(doc: dict) -> str:
    return hashlib.sha256(json.dumps({k:v for k,v in doc.items() if k != "sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def load_manifest() -> dict:
    doc = json.loads(MANIFEST_PATH.read_text())
    if doc.get("sha256") != canonical_hash(doc): raise ValueError("benchmark_manifest_hash_mismatch")
    if (doc.get("dimension"), doc.get("target_rows_per_relation"), doc.get("decoy_rows_per_relation")) != (1024, 25000, 25000): raise ValueError("benchmark_manifest_cardinality_mismatch")
    return doc

def counter_bytes(seed: str, relation: str, ordinal: int) -> bytes:
    return hashlib.sha256(f"{seed}:{relation}:{ordinal}".encode()).digest()

def identity(manifest: dict, relation: str, ordinal: int, kind: str="target") -> UUID:
    return uuid5(NAMESPACE, f"{kind}:{relation}:{counter_bytes(manifest['seed'],relation,ordinal).hex()}")

def vector(manifest: dict, relation: str, ordinal: int) -> list[float]:
    raw=b""; c=0
    while len(raw)<4096: raw += hashlib.sha256(counter_bytes(manifest['seed'],relation,ordinal)+c.to_bytes(4,'big')).digest(); c += 1
    values=[(int.from_bytes(raw[i:i+4],'big')/2**32)*2-1 for i in range(0,4096,4)]
    norm=math.sqrt(sum(v*v for v in values)); return [v/norm for v in values]

def loader_sql(manifest: dict, workspace: UUID, cleanup: bool=False) -> str:
    decoy=identity(manifest,"decoy",0,"workspace"); marker=manifest["sha256"]
    if cleanup: return f"delete from public.workspaces where id in ('{workspace}','{decoy}');"
    v="('['||array_to_string(array(select case when i=1 then 1.0 else 0.000001 end from generate_series(1,1024)i),',')||']')::extensions.vector(1024)"
    source, dsource, wiki, dwiki=(identity(manifest,x,0) for x in ("source","decoysource","wiki","decoywiki"))
    return f"""insert into auth.users(id,email) values ('{workspace}','benchmark-{workspace}@example.test'),('{decoy}','benchmark-{decoy}@example.test') on conflict do nothing;
insert into public.workspaces(id,name,owner_id) values ('{workspace}','hnsw benchmark','{workspace}'),('{decoy}','hnsw benchmark decoy','{decoy}') on conflict do nothing;
insert into public.raw_sources(id,workspace_id,created_by,title,source_type,content,content_hash) values ('{source}','{workspace}','{workspace}','benchmark','text','benchmark','{marker}'),('{dsource}','{decoy}','{decoy}','benchmark','text','benchmark','{marker}-decoy') on conflict do nothing;
insert into public.wiki_pages(id,workspace_id,created_by,slug,title,category,content) values ('{wiki}','{workspace}','{workspace}','benchmark','benchmark','concepts','benchmark'),('{dwiki}','{decoy}','{decoy}','benchmark','benchmark','concepts','benchmark') on conflict do nothing;
insert into public.source_chunks(raw_source_id,workspace_id,chunk_index,content,char_start,char_end,embedding) select '{source}','{workspace}',g,'benchmark target '||g,0,18,{v} from generate_series(0,24999)g union all select '{dsource}','{decoy}',g,'benchmark decoy '||g,0,17,{v} from generate_series(0,24999)g;
insert into public.wiki_embeddings(wiki_id,workspace_id,chunk_index,chunk_content,embedding) select '{wiki}','{workspace}',g,'benchmark target '||g,{v} from generate_series(0,24999)g union all select '{dwiki}','{decoy}',g,'benchmark decoy '||g,{v} from generate_series(0,24999)g;
analyze public.source_chunks; analyze public.wiki_embeddings;"""

def main() -> int:
    p=argparse.ArgumentParser(); p.add_argument("--workspace-id",type=UUID,required=True); p.add_argument("--cleanup",action="store_true"); p.add_argument("--sql",action="store_true"); a=p.parse_args()
    try:
        m=load_manifest(); out=loader_sql(m,a.workspace_id,a.cleanup)
        print(out if a.sql else json.dumps({"manifest_sha256":m["sha256"],"workspace_id":str(a.workspace_id),"source_rows":25000,"wiki_rows":25000}))
    except ValueError as e: print(e, file=__import__('sys').stderr); return 2
    return 0
if __name__ == "__main__": raise SystemExit(main())
