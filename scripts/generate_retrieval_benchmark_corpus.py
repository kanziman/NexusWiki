#!/usr/bin/env python3
"""Deterministic, scoped corpus used by the full-path retrieval benchmark.

The labelled fixture is loaded before the large non-matching corpus.  Labels are
never used to build a ranking: they only name the rows that were inserted.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
from uuid import UUID, uuid5

from nexuswiki_core.tokenizer import TSV_TOKENIZER_VERSION, bigram, normalize

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "packages/core/tests/fixtures/retrieval"
MANIFEST_PATH = FIXTURE_DIR / "benchmark_hnsw_corpus.v1.json"
CORPUS_PATH = FIXTURE_DIR / "representative_corpus.v1.json"
NAMESPACE = UUID("6e786575-7377-696b-692d-62656e636830")


def canonical_hash(doc: dict) -> str:
    return hashlib.sha256(json.dumps({k: v for k, v in doc.items() if k != "sha256"}, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def load_manifest() -> dict:
    doc = json.loads(MANIFEST_PATH.read_text())
    if doc.get("sha256") != canonical_hash(doc):
        raise ValueError("benchmark_manifest_hash_mismatch")
    if (doc.get("dimension"), doc.get("target_rows_per_relation"), doc.get("decoy_rows_per_relation")) != (1024, 25000, 25000):
        raise ValueError("benchmark_manifest_cardinality_mismatch")
    return doc


def load_corpus() -> dict:
    doc = json.loads(CORPUS_PATH.read_text())
    if doc.get("sha256") != canonical_hash(doc):
        raise ValueError("benchmark_corpus_hash_mismatch")
    return doc


def counter_bytes(seed: str, relation: str, ordinal: int) -> bytes:
    return hashlib.sha256(f"{seed}:{relation}:{ordinal}".encode()).digest()


def identity(manifest: dict, relation: str, ordinal: int, kind: str = "target") -> UUID:
    return uuid5(NAMESPACE, f"{kind}:{relation}:{counter_bytes(manifest['seed'], relation, ordinal).hex()}")


def logical_uuid(manifest: dict, logical_id: str) -> UUID:
    """Stable checked-in logical evidence ID -> DB UUID mapping."""
    return uuid5(NAMESPACE, f"fixture:{manifest['sha256']}:{logical_id}")


def logical_id_map(manifest: dict, corpus: dict | None = None) -> dict[str, str]:
    corpus = corpus or load_corpus()
    rows = [f"source:{row['id']}" for row in corpus["source_chunks"]]
    rows += [f"wiki:{row['id']}" for row in corpus["wiki_pages"]]
    return {logical: str(logical_uuid(manifest, logical)) for logical in rows}


def decoy_parent_id(manifest: dict, workspace: UUID, relation: str) -> UUID:
    """Keep large generated parents unique per benchmark arm.

    Logical fixture evidence is deliberately stable between arms, whereas each
    generated parent's chunk-index namespace belongs to one local workspace.
    """
    return uuid5(NAMESPACE, f"decoy-parent:{manifest['sha256']}:{workspace}:{relation}")


def vector(manifest: dict, relation: str, ordinal: int) -> list[float]:
    raw = b""; counter = 0
    while len(raw) < 4096:
        raw += hashlib.sha256(counter_bytes(manifest["seed"], relation, ordinal) + counter.to_bytes(4, "big")).digest(); counter += 1
    values = [(int.from_bytes(raw[index:index + 4], "big") / 2**32) * 2 - 1 for index in range(0, 4096, 4)]
    norm = math.sqrt(sum(value * value for value in values))
    return [value / norm for value in values]


def text_vector(text: str) -> list[float]:
    """A test-only embedding contract shared by fixture rows and query text."""
    values = [0.0] * 1024
    for token in bigram(normalize(text)).split():
        digest = hashlib.sha256(token.encode()).digest()
        slot = int.from_bytes(digest[:2], "big") % 1024
        values[slot] += -1.0 if digest[2] & 1 else 1.0
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def _quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _vector_literal(values: list[float]) -> str:
    return _quote("[" + ",".join(f"{value:.12g}" for value in values) + "]") + "::extensions.vector(1024)"


def loader_sql(manifest: dict, workspace: UUID, cleanup: bool = False) -> str:
    """Return transaction-safe SQL; cleanup is restricted to the fixed workspace."""
    corpus = load_corpus(); mapping = logical_id_map(manifest, corpus)
    if cleanup:
        return f"delete from public.workspaces where id = {_quote(str(workspace))}::uuid;"
    marker = manifest["sha256"]
    statements = [
        "begin;",
        f"insert into auth.users(id,email) values ({_quote(str(workspace))}::uuid,{_quote('benchmark-' + str(workspace) + '@example.test')}) on conflict do nothing;",
        f"insert into public.workspaces(id,name,owner_id) values ({_quote(str(workspace))}::uuid,'retrieval benchmark',{_quote(str(workspace))}::uuid) on conflict do nothing;",
    ]
    for row in corpus["source_chunks"]:
        logical = f"source:{row['id']}"; source_id = logical_uuid(manifest, f"raw:{logical}"); chunk_id = mapping[logical]
        text = row["text"]; lexical = bigram(normalize(text))
        statements += [
            f"insert into public.raw_sources(id,workspace_id,created_by,title,source_type,content,content_hash) values ({_quote(str(source_id))}::uuid,{_quote(str(workspace))}::uuid,{_quote(str(workspace))}::uuid,{_quote(row['title'])},'text',{_quote(text)},{_quote(marker + ':' + logical)}) on conflict do nothing;",
            f"insert into public.source_chunks(id,raw_source_id,workspace_id,chunk_index,content,char_start,char_end,embedding,search_tsv,tsv_tokenizer_version) values ({_quote(chunk_id)}::uuid,{_quote(str(source_id))}::uuid,{_quote(str(workspace))}::uuid,0,{_quote(text)},0,{len(text)},{_vector_literal(text_vector(text))},to_tsvector('simple',{_quote(lexical)}),{_quote(TSV_TOKENIZER_VERSION)}) on conflict do nothing;",
        ]
    for row in corpus["wiki_pages"]:
        logical = f"wiki:{row['id']}"; wiki_id = mapping[logical]; embed_id = str(logical_uuid(manifest, f"embedding:{logical}")); text = row["text"]
        statements += [
            f"insert into public.wiki_pages(id,workspace_id,created_by,slug,title,category,content,search_tsv,tsv_tokenizer_version) values ({_quote(wiki_id)}::uuid,{_quote(str(workspace))}::uuid,{_quote(str(workspace))}::uuid,{_quote(row['slug'])},{_quote(row['title'])},'concepts',{_quote(text)},to_tsvector('simple',{_quote(bigram(normalize(text)))}),{_quote(TSV_TOKENIZER_VERSION)}) on conflict do nothing;",
            f"insert into public.wiki_embeddings(id,wiki_id,workspace_id,chunk_index,chunk_content,embedding) values ({_quote(embed_id)}::uuid,{_quote(wiki_id)}::uuid,{_quote(str(workspace))}::uuid,0,{_quote(text)},{_vector_literal(text_vector(text))}) on conflict do nothing;",
        ]
    wiki = {row["id"]: mapping[f"wiki:{row['id']}"] for row in corpus["wiki_pages"]}
    for edge in corpus.get("wiki_links", []):
        statements.append(f"insert into public.wiki_links(workspace_id,from_wiki_id,target_slug,to_wiki_id) values ({_quote(str(workspace))}::uuid,{_quote(wiki[edge['from']])}::uuid,{_quote(edge['to'])},{_quote(wiki[edge['to']])}::uuid) on conflict do nothing;")
    # Decoys retain the manifest's 25k target/foreign-row contract yet cannot
    # lexical-match fixture queries (the token is never present in the fixture).
    unit = _vector_literal([1.0] + [0.000001] * 1023)
    for table, parent, content in (("source_chunks", "raw_sources", "benchmark-nonmatching-decoy"), ("wiki_embeddings", "wiki_pages", "benchmark-nonmatching-decoy")):
        if table == "source_chunks":
            source = decoy_parent_id(manifest, workspace, "source")
            statements += [f"insert into public.raw_sources(id,workspace_id,created_by,title,source_type,content,content_hash) values ({_quote(str(source))}::uuid,{_quote(str(workspace))}::uuid,{_quote(str(workspace))}::uuid,'benchmark filler','text','benchmark filler',{_quote(marker+':fill')}) on conflict do nothing;",
                f"insert into public.source_chunks(raw_source_id,workspace_id,chunk_index,content,char_start,char_end,embedding) select {_quote(str(source))}::uuid,{_quote(str(workspace))}::uuid,g,{_quote(content)},0,{len(content)},{unit} from generate_series(1,24988) g;"]
        else:
            page = decoy_parent_id(manifest, workspace, "wiki")
            statements += [f"insert into public.wiki_pages(id,workspace_id,created_by,slug,title,category,content) values ({_quote(str(page))}::uuid,{_quote(str(workspace))}::uuid,{_quote(str(workspace))}::uuid,'benchmark-filler','benchmark filler','concepts','benchmark filler') on conflict do nothing;",
                f"insert into public.wiki_embeddings(wiki_id,workspace_id,chunk_index,chunk_content,embedding) select {_quote(str(page))}::uuid,{_quote(str(workspace))}::uuid,g,{_quote(content)},{unit} from generate_series(1,24988) g;"]
    statements += ["analyze public.source_chunks;", "analyze public.wiki_embeddings;", "commit;"]
    return "\n".join(statements)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--workspace-id", type=UUID, required=True); parser.add_argument("--cleanup", action="store_true"); parser.add_argument("--sql", action="store_true")
    args = parser.parse_args()
    try:
        manifest = load_manifest(); output = loader_sql(manifest, args.workspace_id, args.cleanup)
        print(output if args.sql else json.dumps({"manifest_sha256": manifest["sha256"], "workspace_id": str(args.workspace_id), "logical_id_to_uuid": logical_id_map(manifest), "source_rows": 25000, "wiki_rows": 25000}))
    except ValueError as error:
        print(error, file=__import__("sys").stderr); return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
