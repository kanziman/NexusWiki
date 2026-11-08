#!/usr/bin/env python3
"""같은 수집 결과 위에서 검색 근거 범위와 임베딩 입력을 교차 비교한다.

계약: openspec/changes/archive/2026-11-08-retrieval-evidence-ablation/ (spec · design.md)

쓰는 순서:
    # 0. 검색 전에 답변 재생 선택 규칙과 비용 상한을 먼저 기록한다(설계 D7).
    uv run python scripts/retrieval_ablation.py register --cap-micros 3000000 --out reg.json

    # 1. 검색만 잰다. 답변 모델을 부르지 않는다. 질의 벡터는 처음 한 번만 만들어 고정한다.
    #    제목 벡터 · 질의 벡터 · 모델 확인의 유료 임베딩은 --embed-cap-micros 안에서만 한다.
    uv run python scripts/retrieval_ablation.py retrieve --state state.json \\
        --query-vectors query-vectors.json --embed-cap-micros 100000 --out retrieve.json

    # 2. 사전 등록 규칙이 고른 조건만 답변을 재생한다.
    uv run python scripts/retrieval_ablation.py answer --state state.json --registration reg.json \\
        --retrieval retrieve.json --query-vectors query-vectors.json --out answer.json

    # 3. 비교하고 실험 스키마를 지운다.
    uv run python scripts/retrieval_ablation.py compare retrieve.json answer.json
    uv run python scripts/retrieval_ablation.py cleanup

⚠️ 로컬 스택 전용이다. 루프백이 아닌 주소는 요청 전에 거부한다.
⚠️ 원문만 · 위키만 조건은 진단 실험이다. 이중 인용이 구조적으로 불가능하므로 그 수치를 제품
   성적표의 이중 인용 통과율과 나란히 놓으면 안 된다.
⚠️ 합성 문서로 잰 샘플 수치다. 운영 효과로 인용하지 않는다.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import sys
from collections.abc import Awaitable, Callable, Iterable, Mapping
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID, uuid4

import httpx

from api.db.user import UserDb
from api.services.retrieval import RetrievalService
from nexuswiki_core.retrieval_policy import (
    DEFAULT_RETRIEVAL_POLICY,
    FIRST_WAVE_CHANNELS,
    RetrievalPolicy,
)
from nexuswiki_core.tokenizer import normalize

_SCRIPTS = Path(__file__).resolve().parent


def _load_script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(f"_ablation_{name}", _SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise SystemExit(f"retrieval_ablation: 스크립트를 불러오지 못했다: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# 판정 규칙과 안전장치는 재생 스크립트의 것을 그대로 쓴다. 두 곳에 두면 정답 판정이 어긋난다.
replay = _load_script("ask_replay")
benchmark = _load_script("benchmark_retrieval")

SCHEMA = "retrieval-ablation-v1"
EXPERIMENT = "retrieval-evidence-ablation"
QUERY_VECTORS_SCHEMA = "retrieval-ablation-query-vectors-v1"
REQUESTED_K = replay.RETRIEVAL_K
# select_dual_evidence의 기본값. 답변 단계 컨텍스트 예산의 일부라 고정 입력으로 기록한다.
PER_SOURCE_LIMIT = 3

SCOPES: dict[str, frozenset[str]] = {
    "source_only": frozenset({"source_vector", "source_lexical"}),
    "wiki_only": frozenset({"wiki_vector", "wiki_lexical"}),
    "both": FIRST_WAVE_CHANNELS,
}
INPUTS: tuple[str, ...] = ("body", "title_body")
# 실험 벡터의 입력 형식 버전. 형식을 바꾸면(예: 섹션 추가) 새 버전을 쓰고
# 이전 벡터를 재사용하지 않는다.
INPUT_FORMATS: dict[str, str] = {"body": "body-v1", "title_body": "title_body-v1"}
DEFAULT_DB_CONTAINER = "supabase_db_NexusWikiReplay"
# 같은 모델이면 같은 텍스트의 벡터는 거의 같다. 공급자 비결정성 여유를 둔 하한이다.
MODEL_IDENTITY_MIN_COSINE = 0.999

RetrieveFn = Callable[[str, str, str], Awaitable[tuple[list[dict[str, Any]], dict[str, Any]]]]


def canonical_sha256(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def embedding_text(embedding_input: str, *, title: str, body: str) -> str:
    """임베딩에 넣을 텍스트. 머리말은 여기에만 붙고 저장 본문·좌표·어휘 색인은 그대로다.

    ⚠️ 제목이 비면 본문만으로 대체하지 않는다. 그 청크만 `body`가 되어 조건이 섞인다.
    ⚠️ 이 형식은 실험 SQL의 현재 텍스트 해시 계산과 정확히 같아야 한다(`_ABLATION_DDL`).
    """
    if embedding_input == "body":
        return body
    if embedding_input == "title_body":
        if not title.strip():
            raise ValueError("title_missing")
        return f"문서: {title}\n{body}"
    raise ValueError(f"알 수 없는 임베딩 입력: {embedding_input}")


def scope_policy(scope: str, base: RetrievalPolicy = DEFAULT_RETRIEVAL_POLICY) -> RetrievalPolicy:
    if scope not in SCOPES:
        raise ValueError(f"알 수 없는 근거 범위: {scope}")
    return replace(base, enabled_channels=SCOPES[scope])


def snapshot_inputs(
    *,
    raw_sources: list[dict[str, Any]],
    source_chunks: list[dict[str, Any]],
    wiki_pages: list[dict[str, Any]],
    wiki_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """수집 스냅샷과 청크 경계를 해시로 고정한다. 본문은 기록에 남기지 않는다.

    ⚠️ 제목도 스냅샷에 든다. 제목 머리말 입력은 제목에 의존하므로, 제목이 바뀐 수집과 비교하면
       입력 효과와 데이터 변경이 섞인다.
    """
    snapshot = {
        "raw_sources": sorted((str(r["id"]), str(r.get("title") or "")) for r in raw_sources),
        "source_chunks": sorted(
            (
                str(c["raw_source_id"]),
                int(c["chunk_index"]),
                str(c["id"]),
                _text_sha256(str(c.get("content") or "")),
            )
            for c in source_chunks
        ),
        "wiki_pages": sorted(
            (
                str(p["id"]),
                str(p.get("title") or ""),
                _text_sha256(str(p.get("content") or "")),
                sorted(str(s) for s in (p.get("sources") or [])),
            )
            for p in wiki_pages
        ),
        "wiki_chunks": sorted(
            (
                str(c["wiki_id"]),
                int(c["chunk_index"]),
                _text_sha256(str(c.get("chunk_content") or "")),
            )
            for c in wiki_chunks
        ),
    }
    boundaries = {
        "source": sorted(
            (
                str(c["raw_source_id"]),
                int(c["chunk_index"]),
                int(c["char_start"]),
                int(c["char_end"]),
            )
            for c in source_chunks
        ),
        "wiki": sorted(
            (str(c["wiki_id"]), int(c["chunk_index"]), len(str(c.get("chunk_content") or "")))
            for c in wiki_chunks
        ),
    }
    versions = sorted({str(c.get("embedding_version")) for c in [*source_chunks, *wiki_chunks]})
    return {
        "snapshot_sha256": canonical_sha256(snapshot),
        "chunk_boundaries_sha256": canonical_sha256(boundaries),
        "embedding_versions": versions,
        "counts": {
            "raw_sources": len(raw_sources),
            "source_chunks": len(source_chunks),
            "wiki_pages": len(wiki_pages),
            "wiki_chunks": len(wiki_chunks),
        },
    }


def fixed_inputs(
    *,
    snapshot: Mapping[str, Any],
    sample: Mapping[str, Any],
    query_vectors: Mapping[str, Any],
) -> dict[str, Any]:
    """조건들이 공유해야 하는 입력. 하나라도 다르면 비교를 거부한다(설계 D5).

    정책은 근거 범위로 끄는 채널을 뺀 기본 내용으로 해시한다. 조건마다 다른 것은 범위뿐이다.
    답변 프롬프트는 검색 단계에서 쓰지 않으므로 답변 기록이 따로 고정한다.
    """
    base = replace(DEFAULT_RETRIEVAL_POLICY, enabled_channels=FIRST_WAVE_CHANNELS)
    return {
        "snapshot_sha256": snapshot["snapshot_sha256"],
        "chunk_boundaries_sha256": snapshot["chunk_boundaries_sha256"],
        "embedding_versions": list(snapshot["embedding_versions"]),
        "fixture_sha256": canonical_sha256(sample),
        "query_vectors_sha256": query_vectors_sha256(query_vectors),
        "policy_version": base.version,
        "policy_content_sha256": benchmark.policy_content_sha256(base),
        "graph_enabled": base.graph_enabled,
        "input_formats": dict(INPUT_FORMATS),
        "requested_k": REQUESTED_K,
        "context_budget": {"requested_k": REQUESTED_K, "per_source_limit": PER_SOURCE_LIMIT},
    }


def query_vectors_sha256(query_vectors: Mapping[str, Any]) -> str:
    return canonical_sha256(
        {qid: entry["vector"] for qid, entry in sorted(query_vectors["vectors"].items())}
    )


class FixedQueryEmbeddingClient:
    """질의 벡터를 파일에서 돌려준다. 조건마다 질의 임베딩이 달라지면 차이가 섞인다."""

    def __init__(self, query_vectors: Mapping[str, Any]) -> None:
        self._by_text: dict[str, list[float] | None] = {
            str(entry["normalized"]): entry.get("vector")
            for entry in query_vectors["vectors"].values()
        }

    async def embed(self, text: str, *, workspace_id: str) -> list[float]:
        vector = self._by_text.get(text)
        if vector is None:
            # 고정 파일에 없거나 생성 때 실패한 질의다. 새로 만들지 않고 장애로 드러낸다.
            raise RuntimeError("query_vector_missing")
        return vector


async def build_query_vectors(
    questions: Iterable[Mapping[str, Any]],
    embed: Callable[[str], Awaitable[list[float]]],
) -> dict[str, Any]:
    """질문마다 한 번 임베딩한다. 실패한 질문은 벡터 없이 남겨 모든 조건에서 실행 장애가 된다."""
    vectors: dict[str, dict[str, Any]] = {}
    for question in questions:
        normalized = normalize(str(question["query"]))
        try:
            vector: list[float] | None = await embed(normalized)
            error = None
        except BudgetExceeded:
            # 상한은 장애가 아니라 중단 사유다. 질문별 실패로 삼키면 상한을 넘겨 계속 부른다.
            raise
        except Exception as exc:  # noqa: BLE001 - 장애 종류만 남기고 계속 간다
            vector, error = None, type(exc).__name__
        vectors[str(question["id"])] = {
            "normalized": normalized,
            "vector": vector,
            "error": error,
        }
    return {
        "schema": QUERY_VECTORS_SCHEMA,
        "created_at": datetime.now(UTC).isoformat(),
        "vectors": vectors,
    }


def failed_query_vectors(query_vectors: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {"id": qid, "error": str(entry.get("error"))}
        for qid, entry in sorted(query_vectors["vectors"].items())
        if entry.get("vector") is None
    ]


def classify(row: Mapping[str, Any]) -> str:
    """질문 하나의 분류. 순서가 의미다: 장애가 있으면 미적중 판정보다 먼저 장애로 센다(설계 D6)."""
    if row.get("doc") == "none":
        return "unanswerable"
    if row.get("status") == "unmapped_expected":
        return "measurement_failure"
    if row.get("failed_channels"):
        return "execution_failure"
    if row.get("status") != "ok":
        return "measurement_failure"
    result = row.get("result") or {}
    return "hit" if result.get("first_relevant_rank") else "retrieval_miss"


def _single_scope_result(result: dict[str, Any], scope: str) -> dict[str, Any]:
    """단일 근거 범위에서는 이중 적중이 구조적으로 불가능하다. 실패가 아니라 의도로 표시한다."""
    if scope == "both":
        return result
    return {**result, "dual_hit": None, "dual_hit_note": "intended_single_evidence"}


def summarize_condition(rows: list[dict[str, Any]], scope: str) -> dict[str, Any]:
    summary = replay.summarize_retrieval(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["classification"]] = counts.get(row["classification"], 0) + 1
    summary["classification_counts"] = counts
    if scope != "both":
        summary["dual_hit_at_8"] = None
    return summary


async def evaluate_condition(
    *,
    scope: str,
    embedding_input: str,
    questions: list[dict[str, Any]],
    expected_by_question: Mapping[str, set[str] | None],
    retrieve: RetrieveFn,
    wiki_sources: Mapping[str, set[str]],
    chunk_sources: Mapping[str, str],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for question in questions:
        qid, doc = str(question["id"]), str(question.get("doc"))
        expected = expected_by_question.get(qid)
        if expected is None and doc != "none":
            row: dict[str, Any] = {
                "id": qid,
                "doc": doc,
                "status": "unmapped_expected",
                "evidence_count": 0,
                "result": None,
            }
        else:
            evidence, meta = await retrieve(scope, embedding_input, str(question["query"]))
            failed = replay.channel_failures(meta)
            disabled = sorted(
                name
                for name, value in meta.items()
                if isinstance(value, dict) and value.get("status") == "disabled"
            )
            succeeded = sorted(
                name
                for name, value in meta.items()
                if isinstance(value, dict) and value.get("status") == "ok"
            )
            unresolved = [
                str(e.get("id"))
                for e in evidence
                if e.get("kind") == "source"
                and not (e.get("metadata") or {}).get("raw_source_id")
                and str(e.get("id")) not in chunk_sources
            ]
            result = replay.retrieval_question_result(
                evidence, expected or set(), dict(wiki_sources), dict(chunk_sources)
            )
            row = {
                "id": qid,
                "doc": doc,
                "status": (
                    "channel_failed" if failed else "unresolved_evidence" if unresolved else "ok"
                ),
                "failed_channels": failed,
                "disabled_channels": disabled,
                "succeeded_channels": succeeded,
                "evidence_count": len(evidence),
                "result": _single_scope_result(result, scope),
            }
        row["classification"] = classify(row)
        rows.append(row)
    return {
        "scope": scope,
        "embedding_input": embedding_input,
        "condition": f"{scope}x{embedding_input}",
        "diagnostic": scope != "both",
        "enabled_channels": sorted(SCOPES[scope]),
        "rows": rows,
        "summary": summarize_condition(rows, scope),
    }


def build_record(
    *,
    label: str,
    git_sha: str | None,
    fixed: Mapping[str, Any],
    snapshot_counts: Mapping[str, int],
    conditions: list[dict[str, Any]],
    checks: Mapping[str, Any] | None = None,
    cost: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    record = {
        "schema": SCHEMA,
        # 재검색 OFF/ON 실험과 다른 실험이다. 요약·비교는 이 값이 같은 기록끼리만 한다.
        "experiment": EXPERIMENT,
        "phase": "retrieval",
        "label": label,
        "git_sha": git_sha,
        "created_at": datetime.now(UTC).isoformat(),
        "fixed_inputs": dict(fixed),
        "snapshot_counts": dict(snapshot_counts),
        # 모델 동일성 · 벡터 준비 · 동등성 검사 결과. 통과하지 못하면 측정 자체를 하지 않는다.
        "checks": dict(checks or {}),
        "cost": dict(cost or {"embedding_micros": 0, "answer_micros": 0}),
        "conditions": conditions,
        "transitions": transitions(conditions),
        "limitations": [
            "합성 문서와 고정 질문으로 잰 샘플 수치이며 운영 트래픽 효과가 아니다.",
            "원문만 · 위키만 조건은 진단 실험이며 제품 성적표의 이중 인용 통과율과 비교할 수 없다.",
        ],
    }
    record["publishable"] = publishable(record)
    return record


def transitions(conditions: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """같은 질문이 조건을 바꿨을 때 복구됐는지 회귀했는지.

    스펙: Append-only reusable experiment record.

    장애나 측정 실패가 한쪽에라도 있으면 복구·회귀로 세지 않고 따로 둔다. 장애로 떨어진 질문을
    회귀로 세면 입력 효과가 아니라 실행 사고가 결론이 된다.
    """
    by: dict[tuple[str, str], dict[str, str]] = {
        (str(c["scope"]), str(c["embedding_input"])): {
            str(r["id"]): str(r["classification"]) for r in c["rows"]
        }
        for c in conditions
    }
    pairs: list[tuple[str, tuple[str, str], tuple[str, str]]] = [
        (f"{scope}: body -> title_body", (scope, "body"), (scope, "title_body")) for scope in SCOPES
    ]
    for embedding_input in INPUTS:
        for single in ("source_only", "wiki_only"):
            pairs.append(
                (
                    f"{embedding_input}: {single} -> both",
                    (single, embedding_input),
                    ("both", embedding_input),
                )
            )
    broken = {"execution_failure", "measurement_failure"}
    out: list[dict[str, Any]] = []
    for name, left, right in pairs:
        if left not in by or right not in by:
            continue
        a, b = by[left], by[right]
        common = sorted(q for q in a if q in b and a[q] != "unanswerable")
        out.append(
            {
                "comparison": name,
                "from": "x".join(left),
                "to": "x".join(right),
                "recovered": [q for q in common if a[q] == "retrieval_miss" and b[q] == "hit"],
                "regressed": [q for q in common if a[q] == "hit" and b[q] == "retrieval_miss"],
                "excluded_failures": [q for q in common if a[q] in broken or b[q] in broken],
            }
        )
    return out


# ---------------------------------------------------------------------------
# 실험 전용 벡터 저장소 (설계 D1 · D2 · D4)
# ---------------------------------------------------------------------------

# ⚠️ 이 SQL은 로컬 재생 스택에만 스크립트가 만든다. 마이그레이션에 넣지 않는다. 운영 함수와
#    RLS 정책 어디에서도 `ablation` 스키마를 참조하지 않으므로 운영 요청은 실험 벡터를 읽을 수 없다.
# ⚠️ 검색 함수 본문은 운영 `search_chunks` · `search_wiki_embeddings`(0011)와 같은 정렬·한도·
#    hnsw 설정을 따른다. 어긋나면 입력 효과와 SQL 차이가 섞이므로 측정 전 동등성 검사로 막는다.
_ABLATION_DDL = """
create schema if not exists ablation;
revoke all on schema ablation from public, anon, authenticated;

create table if not exists ablation.vectors (
  kind              text not null check (kind in ('source', 'wiki')),
  -- source_chunks.id 또는 wiki_embeddings.id. 운영 행이 지워지면 검색 join에서 빠진다.
  chunk_ref         uuid not null,
  workspace_id      uuid not null,
  input_format      text not null,
  embedding_version text not null,
  -- 임베딩한 텍스트 그대로의 해시. 제목만 바뀌어도 달라져 이전 벡터가 재사용되지 않는다.
  text_sha256       text not null,
  embedding         extensions.vector(1024) not null,
  -- 이 벡터를 만들 때 실측한 비용. 재사용한 실행의 기록에서도 비용이 사라지지 않게 한다.
  cost_micros       bigint not null default 0,
  created_at        timestamptz not null default now(),
  primary key (kind, chunk_ref, input_format, embedding_version, text_sha256)
);

-- 비용 열이 생기기 전에 만든 로컬 테이블도 같은 모양으로 맞춘다.
alter table ablation.vectors add column if not exists cost_micros bigint not null default 0;

-- 운영과 같은 인덱스 종류. 정확 탐색으로 두면 HNSW인 운영과 순위가 달라질 수 있다.
create index if not exists vectors_embedding_idx
  on ablation.vectors using hnsw (embedding extensions.vector_cosine_ops);

create or replace function ablation.search_chunks(
  p_workspace_id uuid,
  p_query extensions.vector(1024),
  p_k int,
  p_input_format text,
  p_embedding_version text
)
returns table (
  id uuid, raw_source_id uuid, chunk_index int, content text, distance double precision
)
language sql
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select c.id, c.raw_source_id, c.chunk_index, c.content,
         (v.embedding operator(extensions.<=>) p_query)::double precision as distance
    from ablation.vectors v
    join public.source_chunks c on c.id = v.chunk_ref and c.workspace_id = v.workspace_id
    join public.raw_sources r on r.id = c.raw_source_id and r.workspace_id = c.workspace_id
   where v.workspace_id = p_workspace_id
     and v.kind = 'source'
     and v.input_format = p_input_format
     and v.embedding_version = p_embedding_version
     -- 현재 제목·본문으로 만든 벡터만 쓴다. 제목이 바뀌기 전의 행이 남아 있어도 섞이지 않는다.
     and v.text_sha256 = encode(sha256(convert_to(
           case p_input_format
             when 'title_body-v1' then '문서: ' || r.title || chr(10) || c.content
             else c.content
           end, 'UTF8')), 'hex')
   order by v.embedding operator(extensions.<=>) p_query
   limit least(greatest(p_k, 1), 100);
$$;

create or replace function ablation.search_wiki_embeddings(
  p_workspace_id uuid,
  p_query extensions.vector(1024),
  p_k int,
  p_input_format text,
  p_embedding_version text
)
returns table (
  id uuid, wiki_id uuid, chunk_index int, chunk_content text, distance double precision
)
language sql
stable
set search_path = public
set hnsw.iterative_scan = 'strict_order'
set hnsw.ef_search = '200'
set hnsw.max_scan_tuples = '40000'
as $$
  select e.id, e.wiki_id, e.chunk_index, e.chunk_content,
         (v.embedding operator(extensions.<=>) p_query)::double precision as distance
    from ablation.vectors v
    join public.wiki_embeddings e on e.id = v.chunk_ref and e.workspace_id = v.workspace_id
    join public.wiki_pages w on w.id = e.wiki_id and w.workspace_id = e.workspace_id
   where v.workspace_id = p_workspace_id
     and v.kind = 'wiki'
     and v.input_format = p_input_format
     and v.embedding_version = p_embedding_version
     and v.text_sha256 = encode(sha256(convert_to(
           case p_input_format
             when 'title_body-v1' then '문서: ' || w.title || chr(10) || e.chunk_content
             else e.chunk_content
           end, 'UTF8')), 'hex')
   order by v.embedding operator(extensions.<=>) p_query
   limit least(greatest(p_k, 1), 100);
$$;
"""


def _lit(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _uuid_lit(value: str) -> str:
    return _lit(str(UUID(value)))


def _vector_lit(vector: Iterable[float]) -> str:
    return _lit("[" + ",".join(repr(float(v)) for v in vector) + "]") + "::extensions.vector"


class LocalDb:
    """로컬 재생 DB에 `docker exec psql`로 SQL을 보낸다.

    ⚠️ postgres 슈퍼유저라 RLS를 건너뛴다. 모든 SQL이 workspace_id를 직접 건다.
    """

    def __init__(self, container: str, runner: Callable[..., Any] | None = None) -> None:
        import subprocess

        self._container = container
        self._runner = runner or subprocess.run

    def run(self, sql: str) -> str:
        completed = self._runner(
            [  # noqa: S607 - 로컬 docker CLI
                "docker",
                "exec",
                "-i",
                self._container,
                "psql",
                "-U",
                "postgres",
                "-d",
                "postgres",
                "-v",
                "ON_ERROR_STOP=1",
                "-At",
                "-q",
            ],
            input=sql,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"retrieval_ablation: psql 실패: {completed.stderr.strip()[:500]}")
        return str(completed.stdout)

    def json(self, sql: str) -> Any:
        # ⚠️ json_agg는 원소 사이에 줄바꿈을 넣는다. 마지막 줄만 읽으면 배열이 잘린다.
        #    호출부는 결과 한 개를 내는 단일 select만 보낸다.
        out = self.run(sql).strip()
        return json.loads(out) if out else None


def ensure_ablation_schema(db: LocalDb) -> None:
    db.run(_ABLATION_DDL)


def drop_ablation_schema(db: LocalDb) -> None:
    db.run("drop schema if exists ablation cascade;")


def copy_body_vectors(db: LocalDb, *, workspace: str, embedding_version: str) -> None:
    """운영 본문 벡터를 실험 저장소에 복사한다. 동등성 검사의 기준이자 `body` 조건의 사본이다."""
    fmt, version, ws = _lit(INPUT_FORMATS["body"]), _lit(embedding_version), _uuid_lit(workspace)
    db.run(
        f"""
insert into ablation.vectors
  (kind, chunk_ref, workspace_id, input_format, embedding_version, text_sha256, embedding)
select 'source', c.id, c.workspace_id, {fmt}, {version},
       encode(sha256(convert_to(c.content, 'UTF8')), 'hex'), c.embedding
  from public.source_chunks c
 where c.workspace_id = {ws} and c.embedding is not null
on conflict do nothing;
insert into ablation.vectors
  (kind, chunk_ref, workspace_id, input_format, embedding_version, text_sha256, embedding)
select 'wiki', e.id, e.workspace_id, {fmt}, {version},
       encode(sha256(convert_to(e.chunk_content, 'UTF8')), 'hex'), e.embedding
  from public.wiki_embeddings e
 where e.workspace_id = {ws} and e.embedding is not null
on conflict do nothing;
"""  # noqa: S608 - 모든 값은 _lit/_uuid_lit/int로 이스케이프한다
    )


def existing_vector_keys(
    db: LocalDb, *, workspace: str, input_format: str, embedding_version: str
) -> dict[tuple[str, str, str], int]:
    """이미 있는 실험 벡터의 키와 그 벡터를 만들 때 든 비용."""
    rows = db.json(
        f"""
select coalesce(
         json_agg(json_build_array(kind, chunk_ref, text_sha256, cost_micros)), '[]'::json)
  from ablation.vectors
 where workspace_id = {_uuid_lit(workspace)}
   and input_format = {_lit(input_format)}
   and embedding_version = {_lit(embedding_version)};
"""  # noqa: S608 - 모든 값은 _lit/_uuid_lit/int로 이스케이프한다
    )
    keys: dict[tuple[str, str, str], int] = {}
    for kind, ref, sha, *rest in rows or []:
        keys[(str(kind), str(ref), str(sha))] = int(rest[0] or 0) if rest else 0
    return keys


def insert_vectors(
    db: LocalDb,
    *,
    workspace: str,
    input_format: str,
    embedding_version: str,
    rows: list[tuple[str, str, str, list[float], int]],
) -> None:
    if not rows:
        return
    values = ",\n".join(
        f"({_lit(kind)}, {_uuid_lit(ref)}, {_uuid_lit(workspace)}, {_lit(input_format)}, "
        f"{_lit(embedding_version)}, {_lit(sha)}, {_vector_lit(vector)}, {int(cost)})"
        for kind, ref, sha, vector, cost in rows
    )
    db.run(
        "insert into ablation.vectors (kind, chunk_ref, workspace_id, input_format, "
        "embedding_version, text_sha256, embedding, cost_micros) values\n"
        f"{values}\non conflict do nothing;"
    )


def vector_items(
    embedding_input: str,
    *,
    raw_sources: list[dict[str, Any]],
    source_chunks: list[dict[str, Any]],
    wiki_pages: list[dict[str, Any]],
    wiki_chunks: list[dict[str, Any]],
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """임베딩할 청크와 실패한 청크. 제목이 없는 청크는 실패로 남긴다(설계 D4)."""
    source_titles = {str(r["id"]): str(r.get("title") or "") for r in raw_sources}
    wiki_titles = {str(p["id"]): str(p.get("title") or "") for p in wiki_pages}
    items: list[dict[str, str]] = []
    failures: list[dict[str, str]] = []
    sources = [
        ("source", str(c["id"]), source_titles.get(str(c["raw_source_id"]), ""), str(c["content"]))
        for c in source_chunks
    ]
    wikis = [
        ("wiki", str(c["id"]), wiki_titles.get(str(c["wiki_id"]), ""), str(c["chunk_content"]))
        for c in wiki_chunks
    ]
    for kind, ref, title, body in [*sources, *wikis]:
        try:
            text = embedding_text(embedding_input, title=title, body=body)
        except ValueError as exc:
            failures.append({"kind": kind, "chunk_ref": ref, "reason": str(exc)})
            continue
        items.append(
            {"kind": kind, "chunk_ref": ref, "text": text, "text_sha256": _text_sha256(text)}
        )
    return items, failures


class BudgetExceeded(RuntimeError):
    pass


class EmbedBudget:
    """모든 유료 임베딩 호출을 하나의 상한 아래에 둔다(스펙: 상한 없는 유료 호출 금지).

    사용액은 재생 DB의 `usage_events`에서 실측한다. 다음 호출이 지금까지 본 가장 비싼 호출만큼
    들어도 상한을 넘지 않을 때만 부른다.
    """

    def __init__(
        self,
        *,
        cap_micros: int | None,
        embed: Callable[[str], Awaitable[list[float]]] | None,
        usage_total: Callable[[], int],
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        max_rate_retries: int = 60,
    ) -> None:
        self._cap, self._embed, self._usage_total = cap_micros, embed, usage_total
        self._sleep, self._max_rate_retries = sleep, max_rate_retries
        self._start: int | None = None
        self.spent_micros = 0
        self.calls = 0
        self.last_cost_micros = 0
        self._max_unit = 1

    async def embed(self, text: str) -> list[float]:
        if self._cap is None or self._embed is None:
            raise SystemExit(
                "retrieval_ablation: 유료 임베딩이 필요하다. --embed-cap-micros와 워커 토큰을 준다"
            )
        if self._start is None:
            self._start = self._usage_total()
        if self.spent_micros + self._max_unit > self._cap:
            raise BudgetExceeded(f"embedding cap {self._cap} micros reached")
        for _ in range(self._max_rate_retries):
            try:
                vector = await self._embed(text)
                break
            except RuntimeError as exc:
                # 워커 레이트 제한(429)은 공급자 호출 전에 막히므로 비용 없이 다시 시도한다.
                if "rate_limited" not in str(exc):
                    raise
                await self._sleep(1.1)
        else:
            raise RuntimeError("rate_limited")
        self.calls += 1
        before = self.spent_micros
        self.spent_micros = self._usage_total() - self._start
        self.last_cost_micros = self.spent_micros - before
        self._max_unit = max(self._max_unit, self.last_cost_micros)
        return vector


async def prepare_title_vectors(
    db: LocalDb,
    *,
    workspace: str,
    embedding_version: str,
    items: list[dict[str, str]],
    budget: EmbedBudget,
) -> dict[str, Any]:
    """없는 실험 벡터만 만든다. 키 다섯 개가 모두 같은 벡터만 재사용한다(스펙: Distinguishable)."""
    fmt = INPUT_FORMATS["title_body"]
    existing = existing_vector_keys(
        db, workspace=workspace, input_format=fmt, embedding_version=embedding_version
    )
    missing = [i for i in items if (i["kind"], i["chunk_ref"], i["text_sha256"]) not in existing]
    reused_micros = sum(
        existing[key]
        for key in ((i["kind"], i["chunk_ref"], i["text_sha256"]) for i in items)
        if key in existing
    )
    created = 0
    created_micros = 0
    pending: list[tuple[str, str, str, list[float], int]] = []
    failures: list[dict[str, str]] = []
    stopped: str | None = None

    def flush() -> None:
        insert_vectors(
            db,
            workspace=workspace,
            input_format=fmt,
            embedding_version=embedding_version,
            rows=pending,
        )
        pending.clear()

    for index, item in enumerate(missing):
        try:
            vector = await budget.embed(item["text"])
        except BudgetExceeded as exc:
            stopped = str(exc)
            failures.extend(
                {"kind": i["kind"], "chunk_ref": i["chunk_ref"], "reason": "not_run_cap"}
                for i in missing[index:]
            )
            break
        except RuntimeError as exc:
            failures.append(
                {"kind": item["kind"], "chunk_ref": item["chunk_ref"], "reason": str(exc)}
            )
            continue
        created += 1
        created_micros += budget.last_cost_micros
        pending.append(
            (item["kind"], item["chunk_ref"], item["text_sha256"], vector, budget.last_cost_micros)
        )
        # 중간에 멈춰도 이미 비용을 낸 벡터는 남긴다. 다시 실행하면 재사용된다.
        if len(pending) >= 16:
            flush()
    flush()
    return {
        "input_format": fmt,
        "embedding_version": embedding_version,
        "total": len(items),
        "reused": len(items) - len(missing),
        "reused_micros": reused_micros,
        "created": created,
        "created_micros": created_micros,
        "failures": failures,
        "stopped": stopped,
    }


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = (sum(x * x for x in a) ** 0.5) * (sum(y * y for y in b) ** 0.5)
    return dot / norm if norm else 0.0


async def model_identity_check(
    db: LocalDb, *, workspace: str, budget: EmbedBudget
) -> dict[str, Any]:
    """제목 벡터를 만들 워커가 수집 때와 같은 모델인지 본다.

    다르면 입력 효과가 아니라 모델 차이를 재게 된다.
    """
    row = db.json(
        f"""
select json_build_object('id', c.id, 'content', c.content, 'embedding', c.embedding::text)
  from public.source_chunks c
 where c.workspace_id = {_uuid_lit(workspace)} and c.embedding is not null
 order by c.id
 limit 1;
"""  # noqa: S608 - 모든 값은 _lit/_uuid_lit/int로 이스케이프한다
    )
    if not row:
        return {"passed": False, "reason": "no_embedded_chunk"}
    fresh = await budget.embed(str(row["content"]))
    cosine = _cosine(fresh, [float(v) for v in json.loads(row["embedding"])])
    return {
        "chunk_id": str(row["id"]),
        "cosine": round(cosine, 6),
        "min_cosine": MODEL_IDENTITY_MIN_COSINE,
        "passed": cosine >= MODEL_IDENTITY_MIN_COSINE,
    }


class AblationRoutingDb:
    """벡터 채널 RPC만 실험 저장소로 보내고 어휘 채널은 운영 RPC를 그대로 쓴다(설계 D1)."""

    _FUNCTIONS = frozenset({"search_chunks", "search_wiki_embeddings"})

    def __init__(
        self, user_db: Any, local_db: LocalDb, *, input_format: str, embedding_version: str
    ) -> None:
        self._user_db, self._local_db = user_db, local_db
        self._input_format, self._embedding_version = input_format, embedding_version

    def __getattr__(self, name: str) -> Any:
        # 답변 재생은 템플릿 조회 · 근거 본문 조회 · 턴 저장도 이 객체로 한다.
        # 전부 요청자 JWT로 간다.
        return getattr(self._user_db, name)

    async def rpc(self, function: str, *, params: Mapping[str, Any]) -> list[dict[str, Any]]:
        if function not in self._FUNCTIONS:
            return await self._user_db.rpc(function, params=params)
        # 모든 값은 _lit/_uuid_lit/int로 이스케이프한다.
        sql = (
            "select coalesce(json_agg(t), '[]'::json) from ablation."  # noqa: S608
            f"{function}({_uuid_lit(str(params['p_workspace_id']))}, "
            f"{_vector_lit(params['p_query'])}, {int(params['p_k'])}, "
            f"{_lit(self._input_format)}, {_lit(self._embedding_version)}) t;"
        )
        rows = await asyncio.to_thread(self._local_db.json, sql)
        return [
            {k: (str(v) if k in {"id", "wiki_id", "raw_source_id"} else v) for k, v in r.items()}
            for r in rows or []
        ]


def _ranking(rows: list[Mapping[str, Any]]) -> list[tuple[str, float]]:
    return [(str(r["id"]), round(float(r["distance"]), 12)) for r in rows]


async def equivalence_check(
    *,
    workspace: str,
    query_vectors: Mapping[str, Any],
    product_db: Any,
    experiment_db: Any,
    limit: int,
) -> dict[str, Any]:
    """`body` 사본을 실험 함수로 검색해 운영 RPC와 순위·거리가 같은지 본다(설계 D2)."""
    mismatches: list[dict[str, str]] = []
    checked = 0
    for qid, entry in sorted(query_vectors["vectors"].items()):
        vector = entry.get("vector")
        if vector is None:
            continue
        checked += 1
        for function in ("search_chunks", "search_wiki_embeddings"):
            params = {"p_workspace_id": workspace, "p_query": vector, "p_k": limit}
            product = await product_db.rpc(function, params=params)
            experiment = await experiment_db.rpc(function, params=params)
            if _ranking(product) != _ranking(experiment):
                mismatches.append({"question": qid, "function": function})
    return {
        "checked_questions": checked,
        "limit": limit,
        "mismatches": mismatches,
        "passed": checked > 0 and not mismatches,
    }


def _differing_fixed_inputs(records: list[Mapping[str, Any]]) -> list[str]:
    base = records[0]["fixed_inputs"]
    keys = set(base)
    for record in records[1:]:
        keys |= set(record["fixed_inputs"])
    return sorted(
        key
        for key in keys
        if any(record["fixed_inputs"].get(key) != base.get(key) for record in records[1:])
    )


def merge_records(
    records: list[Mapping[str, Any]], phase: str = "retrieval"
) -> list[dict[str, Any]]:
    """비교 가능한 기록들의 조건을 모은다.

    실험 식별자나 고정 입력이 다르면 거부한다(설계 D5 · D8).
    """
    if not records:
        raise SystemExit("retrieval_ablation: 비교할 기록이 없다")
    others = sorted(
        {str(r.get("experiment")) for r in records if r.get("experiment") != EXPERIMENT}
    )
    if others:
        raise SystemExit(f"retrieval_ablation: 다른 실험의 기록과는 합치지 않는다: {others}")
    differing = _differing_fixed_inputs(records)
    prompts = {str(r.get("answer_prompt_sha256")) for r in records if r.get("phase") == "answer"}
    if len(prompts) > 1:
        differing.append("answer_prompt_sha256")
    if differing:
        raise SystemExit(
            f"retrieval_ablation: 고정 입력이 다른 기록은 비교하지 않는다: {differing}"
        )
    merged: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("phase", "retrieval") != phase:
            continue
        for condition in record.get("conditions") or []:
            name = str(condition["condition"])
            if name in merged:
                raise SystemExit(f"retrieval_ablation: 같은 조건이 두 기록에 있다: {name}")
            merged[name] = dict(condition)
    return list(merged.values())


_COMPARE_ROWS: tuple[tuple[str, str], ...] = (
    ("hit_at_1", "hit@1"),
    ("hit_at_3", "hit@3"),
    ("hit_at_8", "hit@8"),
    ("mrr", "MRR"),
    ("source_hit_at_8", "원문 적중@8"),
    ("wiki_hit_at_8", "위키 적중@8"),
    ("dual_hit_at_8", "이중 적중@8"),
)


_ANSWER_ROWS: tuple[tuple[str, str], ...] = (
    ("answered", "재생 문항"),
    ("not_run", "상한으로 미실행"),
    ("fact_included_rate", "기대 사실 포함"),
    ("product_pass_rate", "제품 통과율(이중 인용 포함)"),
    ("diagnostic_pass_rate", "진단 통과율(사실 기준)"),
    ("fabricated_anchors", "위조 앵커"),
    ("refusal_correct", "정확한 거절"),
    ("cost_micros", "비용(micros)"),
)


def _ordered(conditions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    order = {f"{s}x{i}": n for n, (s, i) in enumerate((s, i) for s in SCOPES for i in INPUTS)}
    return sorted(conditions, key=lambda c: order.get(str(c["condition"]), 99))


def _header(conditions: list[dict[str, Any]]) -> list[str]:
    return [f"{c['condition']}{' (진단)' if c.get('diagnostic') else ''}" for c in conditions]


def compare_markdown(records: list[Mapping[str, Any]]) -> str:
    conditions = _ordered(merge_records(records, "retrieval"))
    answers = _ordered(merge_records(records, "answer"))
    lines = [
        "합성 샘플로 잰 수치이며 운영 트래픽 효과가 아니다. (진단) 조건은 이중 인용이 구조적으로 "
        "불가능해 제품 성적표의 이중 인용 통과율과 비교하지 않는다.",
    ]
    if answers:
        lines += [
            "",
            "답변 재생. `both`의 통과율만 제품 성적표 규칙(이중 인용 포함)이다.",
            "",
            "| 지표 | " + " | ".join(_header(answers)) + " |",
            "| --- |" + " --- |" * len(answers),
        ]
        for key, label in _ANSWER_ROWS:
            cells = [replay._format(c["summary"].get(key)) for c in answers]
            lines.append(f"| {label} | " + " | ".join(cells) + " |")
    if not conditions:
        return "\n".join(lines)
    header = _header(conditions)
    lines += [
        "",
        "검색만 잰 결과.",
        "",
        "| 지표 | " + " | ".join(header) + " |",
        "| --- |" + " --- |" * len(conditions),
    ]
    for key, label in _COMPARE_ROWS:
        cells = [replay._format(c["summary"].get(key)) for c in conditions]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    for kind in ("hit", "retrieval_miss", "execution_failure", "measurement_failure"):
        cells = [
            str(c["summary"].get("classification_counts", {}).get(kind, 0)) for c in conditions
        ]
        lines.append(f"| {kind} | " + " | ".join(cells) + " |")
    lines += ["", "| 비교 | 복구 | 회귀 | 장애로 제외 |", "| --- | --- | --- | --- |"]
    for item in transitions(conditions):
        lines.append(
            f"| {item['comparison']} | {', '.join(item['recovered']) or '-'} | "
            f"{', '.join(item['regressed']) or '-'} | "
            f"{', '.join(item['excluded_failures']) or '-'} |"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 사전 등록 · 답변 재생 · 진단 판정 (설계 D6 · D7 · D8)
# ---------------------------------------------------------------------------

REGISTRATION_SCHEMA = "retrieval-ablation-registration-v1"
SELECTION_RULE: dict[str, Any] = {
    # 위키 기여를 답변 수준에서 재는 핵심 비교라 항상 재생한다.
    "always": ["source_onlyxbody", "bothxbody"],
    # 검색 단계에서 기본 대비 나빠지지 않은 경우에만 재생한다.
    "conditional": {
        "bothxtitle_body": {"baseline": "bothxbody", "min_hit_at_8_delta": 0.0, "max_new_misses": 1}
    },
    "retrieval_only": ["wiki_onlyxbody", "wiki_onlyxtitle_body", "source_onlyxtitle_body"],
}
# 2026-11-08 재생 실측 문항당 약 $0.027의 두 배. 첫 턴 전에는 이 값으로 상한을 지킨다.
DEFAULT_TURN_ESTIMATE_MICROS = 60_000


def build_registration(*, cap_micros: int, turn_estimate_micros: int) -> dict[str, Any]:
    if cap_micros <= 0 or turn_estimate_micros <= 0:
        raise SystemExit("retrieval_ablation: 비용 상한과 턴 추정치는 양수여야 한다")
    return {
        "schema": REGISTRATION_SCHEMA,
        "experiment": EXPERIMENT,
        "created_at": datetime.now(UTC).isoformat(),
        "rule": SELECTION_RULE,
        "rule_sha256": canonical_sha256(SELECTION_RULE),
        "answer_cap_micros": cap_micros,
        "turn_estimate_micros": turn_estimate_micros,
    }


def check_registration(registration: Mapping[str, Any], retrieval: Mapping[str, Any]) -> None:
    """사전 등록이 검색 결과보다 먼저였는지, 상한이 있는지, 규칙이 바뀌지 않았는지 본다."""
    if registration.get("schema") != REGISTRATION_SCHEMA:
        raise SystemExit("retrieval_ablation: 사전 등록 파일 형식이 아니다")
    if registration.get("experiment") != EXPERIMENT or retrieval.get("experiment") != EXPERIMENT:
        raise SystemExit("retrieval_ablation: 다른 실험의 등록이나 기록이다")
    cap = registration.get("answer_cap_micros")
    if not isinstance(cap, int) or cap <= 0:
        raise SystemExit("retrieval_ablation: 비용 상한이 없는 답변 재생은 하지 않는다")
    if registration.get("rule_sha256") != canonical_sha256(registration.get("rule")):
        raise SystemExit("retrieval_ablation: 사전 등록 규칙이 등록 뒤에 바뀌었다")
    registered = datetime.fromisoformat(str(registration["created_at"]))
    measured = datetime.fromisoformat(str(retrieval["created_at"]))
    # ⚠️ 결과를 본 뒤 규칙을 고르면 유리한 조건만 재생하게 된다. 그 순서를 기계적으로 막는다.
    if registered >= measured:
        raise SystemExit("retrieval_ablation: 사전 등록이 검색 기록보다 늦다. 재생하지 않는다")


def select_conditions(
    rule: Mapping[str, Any], conditions: list[Mapping[str, Any]]
) -> tuple[list[str], dict[str, str]]:
    by = {str(c["condition"]): c for c in conditions}
    selected: list[str] = []
    reasons: dict[str, str] = {}
    for name in rule["always"]:
        if name not in by:
            raise SystemExit(f"retrieval_ablation: 필수 조건의 검색 기록이 없다: {name}")
        selected.append(name)
        reasons[name] = "always"
    for name, spec in rule["conditional"].items():
        base = by.get(spec["baseline"])
        target = by.get(name)
        if base is None or target is None:
            reasons[name] = "skipped: retrieval record missing"
            continue
        delta = (target["summary"].get("hit_at_8") or 0.0) - (
            base["summary"].get("hit_at_8") or 0.0
        )
        base_class = {str(r["id"]): r["classification"] for r in base["rows"]}
        new_misses = sorted(
            str(r["id"])
            for r in target["rows"]
            if r["classification"] == "retrieval_miss" and base_class.get(str(r["id"])) == "hit"
        )
        if delta >= spec["min_hit_at_8_delta"] and len(new_misses) <= spec["max_new_misses"]:
            selected.append(name)
            reasons[name] = f"selected: hit@8 delta {delta:+.4f}, new misses {new_misses}"
        else:
            reasons[name] = f"skipped: hit@8 delta {delta:+.4f}, new misses {new_misses}"
    return selected, reasons


def answer_verdict(row: Mapping[str, Any], scope: str) -> dict[str, Any]:
    """답변 판정. 이중 인용은 `both`에만 묻는다(스펙: Diagnostic verdicts per condition)."""
    status = str(row.get("status"))
    answerable = row.get("doc") != "none"
    if status == "not_run":
        return {"pass": None, "classification": "not_run_cap", "reason": "비용 상한"}
    if not answerable:
        # 거절 판정은 범위와 무관하게 제품 성적표 규칙 그대로다. 정상 문항과 따로 보고한다.
        result = replay.verdict(dict(row))
        return {
            **result,
            "classification": "refusal_correct" if result["pass"] else "refusal_wrong",
        }
    if status not in {"resolved", "fallback", "no-evidence"}:
        return {"pass": False, "classification": "execution_failure", "reason": f"상태 {status}"}
    # ⚠️ 켜 둔 채널이 실패한 턴은 답이 맞든 틀리든 그 조건을 잰 것이 아니다. 판정보다 먼저 거른다.
    if row.get("failed_channels"):
        return {
            "pass": False,
            "classification": "execution_failure",
            "reason": f"검색 채널 실패 {row['failed_channels']}",
        }
    if scope == "both":
        result = replay.verdict(dict(row))
        if result["pass"]:
            return {**result, "classification": "pass"}
        missing_fact = row.get("keyword_hit") is False
        return {**result, "classification": "fact_missing" if missing_fact else "fail"}
    # 단일 근거: 사실 포함과 위조 앵커만 본다. 반대 종류 인용이 없는 것은 의도된 결과다.
    fabricated = int(row.get("fabricated_anchor_count") or 0)
    if status != "resolved":
        return {"pass": False, "classification": "fail", "reason": f"상태 {status}"}
    if fabricated:
        return {"pass": False, "classification": "fail", "reason": f"위조 앵커 {fabricated}건"}
    if row.get("keyword_hit") is False:
        return {
            "pass": False,
            "classification": "fact_missing",
            "reason": "기대 사실이 답변에 없다",
        }
    return {
        "pass": True,
        "classification": "fact_included",
        "reason": None,
        "dual_citation": None,
        "dual_citation_note": "intended_single_evidence",
    }


def summarize_answers(rows: list[Mapping[str, Any]], scope: str) -> dict[str, Any]:
    answerable = [r for r in rows if r.get("doc") != "none"]
    run = [r for r in answerable if r.get("status") != "not_run"]
    counts: dict[str, int] = {}
    for row in rows:
        kind = str(row["verdict"]["classification"])
        counts[kind] = counts.get(kind, 0) + 1
    with_fact = [r for r in run if r.get("keyword_hit") is not None]
    unanswerable = [r for r in rows if r.get("doc") == "none" and r.get("status") != "not_run"]
    summary = {
        "diagnostic": scope != "both",
        "answerable": len(answerable),
        "answered": len(run),
        "not_run": sum(1 for r in rows if r.get("status") == "not_run"),
        "fact_included_rate": (
            sum(1 for r in with_fact if r.get("keyword_hit")) / len(with_fact)
            if with_fact
            else None
        ),
        # `both`만 제품 성적표 규칙(이중 인용 포함)의 통과율이다. 단일 근거는 진단 통과율이다.
        "pass_rate": (sum(1 for r in run if r["verdict"]["pass"]) / len(run) if run else None),
        "verdict_rule": "product_dual_citation" if scope == "both" else "diagnostic_fact_only",
        # ⚠️ 두 통과율은 규칙이 달라 같은 행에 두지 않는다. 해당하지 않는 쪽은 None이다.
        "product_pass_rate": None,
        "diagnostic_pass_rate": None,
        "fabricated_anchors": sum(int(r.get("fabricated_anchor_count") or 0) for r in rows),
        "refusal_correct": sum(1 for r in unanswerable if r["verdict"]["pass"]),
        "refusal_total": len(unanswerable),
        "classification_counts": counts,
        "cost_micros": sum(int(r.get("cost_micros") or 0) for r in rows),
    }
    key = "product_pass_rate" if scope == "both" else "diagnostic_pass_rate"
    summary[key] = summary["pass_rate"]
    return summary


async def run_answers(
    *,
    plan: list[tuple[str, str, dict[str, Any]]],
    run_turn: Callable[[str, str, dict[str, Any]], Awaitable[dict[str, Any]]],
    cap_micros: int,
    turn_estimate_micros: int,
) -> tuple[list[dict[str, Any]], int, str | None]:
    """계획한 턴을 상한 안에서만 돌린다. 다음 턴이 상한을 넘길 수 있으면 그 전에 멈춘다."""
    rows: list[dict[str, Any]] = []
    spent = 0
    unit = turn_estimate_micros
    stopped: str | None = None
    for condition, scope, question in plan:
        if stopped is None and spent + unit > cap_micros:
            stopped = f"answer cap {cap_micros} micros: spent {spent}, next turn estimate {unit}"
        if stopped is not None:
            rows.append(
                {
                    "condition": condition,
                    "id": question["id"],
                    "doc": question.get("doc"),
                    "status": "not_run",
                    "cost_micros": 0,
                }
            )
            continue
        row = await run_turn(condition, scope, question)
        cost = int(row.get("cost_micros") or 0)
        spent += cost
        unit = max(unit, cost)
        rows.append({"condition": condition, **row})
    return rows, spent, stopped


def turn_row(
    question: Mapping[str, Any],
    events: list[tuple[str, dict[str, Any]]],
    message: Mapping[str, Any],
    usage: list[Mapping[str, Any]],
    elapsed_ms: int,
) -> dict[str, Any]:
    """재생 스크립트 `_ask_once`와 같은 필드. 판정 함수가 그 필드를 읽는다."""
    answer = replay.answer_text(events)
    citations = next((p for name, p in reversed(events) if name == "citations"), {})
    # Ask는 검색 장애를 `meta` 이벤트의 `missing_channels`로만 알린다. 꺼 둔 채널은 들지 않는다.
    failed_channels = sorted(
        {
            str(name)
            for event, payload in events
            if event == "meta"
            for name in (payload.get("missing_channels") or [])
        }
    )
    return {
        "id": question["id"],
        "doc": question.get("doc"),
        "status": message.get("status") or "unknown",
        "failed_channels": failed_channels,
        "elapsed_ms": elapsed_ms,
        "model": next((u["model"] for u in usage if u.get("model")), None),
        "prompt_tokens": sum(int(u.get("prompt_tokens") or 0) for u in usage) if usage else None,
        "completion_tokens": (
            sum(int(u.get("completion_tokens") or 0) for u in usage) if usage else None
        ),
        "cost_micros": sum(int(u.get("cost_micros") or 0) for u in usage),
        "fabricated_anchor_count": citations.get("fabricated_anchor_count"),
        "cited_anchor_count": citations.get("cited_anchor_count"),
        "cited_wiki_count": replay._count_kind(citations, "wiki"),
        "cited_source_count": replay._count_kind(citations, "source"),
        "dual_citation_rate": citations.get("dual_citation_rate"),
        "keyword_hit": replay.keyword_hit(answer, list(question.get("expect_any") or [])),
        "answer": answer,
    }


_PUBLISHABLE_SUMMARY_KEYS = (
    "answerable",
    "answered",
    "not_run",
    "hit_at_1",
    "hit_at_3",
    "hit_at_8",
    "mrr",
    "source_hit_at_8",
    "wiki_hit_at_8",
    "dual_hit_at_8",
    "fact_included_rate",
    "product_pass_rate",
    "diagnostic_pass_rate",
    "verdict_rule",
    "fabricated_anchors",
    "refusal_correct",
    "refusal_total",
    "classification_counts",
    "cost_micros",
)


def publishable(record: Mapping[str, Any]) -> dict[str, Any]:
    """#230이 가져갈 수 있는 필드만. 질문 · 답변 · 근거 본문 · 워크스페이스 id · 토큰은 없다."""
    conditions = []
    for condition in record.get("conditions") or []:
        summary = condition.get("summary") or {}
        conditions.append(
            {
                "condition": condition["condition"],
                "diagnostic": bool(condition.get("diagnostic")),
                "summary": {k: summary[k] for k in _PUBLISHABLE_SUMMARY_KEYS if k in summary},
                "questions": {
                    str(r["id"]): {
                        "classification": (r.get("verdict") or {}).get("classification")
                        or r.get("classification"),
                        "pass": (r.get("verdict") or {}).get("pass"),
                        "fact_included": r.get("keyword_hit"),
                        "first_relevant_rank": (r.get("result") or {}).get("first_relevant_rank"),
                    }
                    for r in condition.get("rows") or []
                },
            }
        )
    return {
        "experiment": record.get("experiment"),
        "phase": record.get("phase"),
        "git_sha": record.get("git_sha"),
        "conditions": conditions,
        "transitions": record.get("transitions") or [],
        # 비용 기록에는 식별자나 본문이 없다. 부분 집계 여부(`embedding_scope`, 재사용 비용)를
        # 함께 내보내야 공개 쪽에서 합계로 오해하지 않는다.
        "cost": dict(record.get("cost") or {}),
        "limitations": list(record.get("limitations") or []),
    }


def build_answer_record(
    *,
    label: str,
    git_sha: str | None,
    retrieval: Mapping[str, Any],
    registration: Mapping[str, Any],
    selected: list[str],
    reasons: Mapping[str, str],
    prompt_sha256: str | None,
    rows: list[dict[str, Any]],
    spent: int,
    stopped: str | None,
) -> dict[str, Any]:
    scope_of = {str(c["condition"]): str(c["scope"]) for c in retrieval["conditions"]}
    retrieval_class = {
        str(c["condition"]): {str(r["id"]): r["classification"] for r in c["rows"]}
        for c in retrieval["conditions"]
    }
    conditions = []
    for name in selected:
        scope = scope_of[name]
        mine = [r for r in rows if r["condition"] == name]
        for row in mine:
            row["verdict"] = answer_verdict(row, scope)
            # Ask는 실패 채널만 알린다. 성공 채널은 켜 둔 채널에서 실패를 뺀 파생 값이다.
            row["succeeded_channels"] = (
                []
                if row.get("status") == "not_run"
                else sorted(set(SCOPES[scope]) - set(row.get("failed_channels") or []))
            )
            row["retrieval_classification"] = retrieval_class[name].get(str(row["id"]))
        conditions.append(
            {
                "condition": name,
                "scope": scope,
                "embedding_input": name.split("x", 1)[1],
                "diagnostic": scope != "both",
                "enabled_channels": sorted(SCOPES[scope]),
                "rows": mine,
                "summary": summarize_answers(mine, scope),
            }
        )
    record = {
        "schema": SCHEMA,
        "experiment": EXPERIMENT,
        "phase": "answer",
        "label": label,
        "git_sha": git_sha,
        "created_at": datetime.now(UTC).isoformat(),
        # 검색 기록과 같은 고정 입력. 답변 프롬프트는 검색 기록에 없으므로 따로 두고,
        # 비교 명령이 답변 기록끼리만 대조한다(`merge_records`).
        "fixed_inputs": dict(retrieval["fixed_inputs"]),
        "answer_prompt_sha256": prompt_sha256,
        "registration": {
            "created_at": registration["created_at"],
            "rule_sha256": registration["rule_sha256"],
            "answer_cap_micros": registration["answer_cap_micros"],
        },
        "selection": {"selected": selected, "reasons": dict(reasons)},
        "retrieval_record_created_at": retrieval["created_at"],
        "cost": {"answer_micros": spent, "answer_cap_micros": registration["answer_cap_micros"]},
        "stopped": stopped,
        "conditions": conditions,
        "limitations": [
            *retrieval.get("limitations", []),
            "LLM 답변은 매번 달라 한 번의 재생 차이는 잡음일 수 있다. 검색 단계 지표를 우선한다.",
            "단일 근거 조건은 컨텍스트 k는 같지만 근거 종류 구성이 다르다.",
        ],
    }
    record["publishable"] = publishable(record)
    return record


def _write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(value, ensure_ascii=False))


def write_record(path: Path, record: Mapping[str, Any]) -> None:
    # "x" 모드: 실행 중에 같은 경로가 생겼어도 덮어쓰지 않는다. 기준선이 조용히 사라지면 안 된다.
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, indent=2))


def _evidence_json(hit: Any) -> dict[str, Any]:
    """검색 라우터 응답과 같은 모양. 판정 함수가 그 모양을 읽는다."""
    return {
        "id": hit.evidence_id,
        "kind": hit.kind,
        "document_id": hit.document_id,
        "channels": list(hit.channels),
        "contributions": dict(hit.contributions),
        "metadata": dict(hit.metadata),
    }


POSTGREST_MAX_ROWS = 1000


def _select_all(
    client: httpx.Client, stack: str, table: str, workspace: str, columns: str, token: str
) -> list[dict[str, Any]]:
    rows = replay._select(
        client,
        stack,
        table,
        {"workspace_id": f"eq.{workspace}", "select": columns, "order": "id"},
        token=token,
    )
    # ⚠️ PostgREST는 max_rows(1000)에서 오류 없이 자른다. 잘린 스냅샷의 해시는 조용히 틀린다.
    if len(rows) >= POSTGREST_MAX_ROWS:
        raise SystemExit(
            f"retrieval_ablation: {table}가 {POSTGREST_MAX_ROWS}행 이상이라 잘렸을 수 있다"
        )
    return rows


def _git_sha() -> str | None:
    """기록용 커밋. 커밋되지 않은 변경이 있으면 `+dirty`를 붙인다(ask_replay_serve.sh와 같다)."""
    import subprocess

    try:
        dirty = subprocess.run(
            ["git", "diff", "--quiet", "HEAD"],  # noqa: S607 - 로컬 개발 도구
            check=False,
        ).returncode
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard", "scripts"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        suffix = "+dirty" if dirty or untracked else ""
        return _head_sha() + suffix
    except OSError:
        return None


def _head_sha() -> str:
    import subprocess

    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],  # noqa: S607 - 로컬 개발 도구, 기록용 커밋 식별만 읽는다
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def worker_embedder(
    client: httpx.AsyncClient, *, url: str, token: str, workspace: str
) -> Callable[[str], Awaitable[list[float]]]:
    """워커 내부 임베딩 경로. 운영 질의 임베딩과 같은 모델·공급자·사용량 회계를 탄다.

    429는 공급자 호출 전에 막힌 것이라 비용이 없다. 예산이 다시 시도할 수 있게 구분해 올린다.
    """

    async def embed(text: str) -> list[float]:
        response = await client.post(
            f"{url.rstrip('/')}/internal/query-embedding",
            json={"text": text},
            headers={"Authorization": f"Bearer {token}", "X-Workspace-Id": workspace},
            timeout=30,
        )
        if response.status_code == 429:
            raise RuntimeError("rate_limited")
        if response.is_error:
            raise RuntimeError(f"embedding_unavailable_{response.status_code}")
        vector = response.json().get("vector")
        if not isinstance(vector, list) or len(vector) != 1024:
            raise RuntimeError("embedding_malformed")
        return [float(v) for v in vector]

    return embed


def load_query_vectors(path: Path, questions: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not path.exists():
        return None
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if loaded.get("schema") != QUERY_VECTORS_SCHEMA:
        raise SystemExit(f"retrieval_ablation: 질의 벡터 형식이 다르다: {path}")
    missing = [str(q["id"]) for q in questions if str(q["id"]) not in loaded["vectors"]]
    if missing:
        raise SystemExit(f"retrieval_ablation: 고정 질의 벡터에 없는 질문: {missing}")
    failed = failed_query_vectors(loaded)
    if failed:
        raise SystemExit(f"retrieval_ablation: 고정 질의 벡터에 실패한 질문이 있다: {failed[:5]}")
    return loaded


def _questions_for(state: Mapping[str, Any], sample: Mapping[str, Any], limit: int) -> list[dict]:
    seeded = set(state["documents"])
    questions = [
        q
        for q in sample["questions"]
        if q.get("doc") == "none" or set(str(q.get("doc")).split("+")) <= seeded
    ]
    return questions[:limit] if limit else questions


def _single_embedding_version(snapshot: Mapping[str, Any]) -> str:
    versions = [v for v in snapshot["embedding_versions"] if v not in {"None", ""}]
    # ⚠️ 버전이 섞인 수집은 운영 검색 자체가 두 모델을 섞어 쓰는 상태다. 그 위의 비교는 무의미하다.
    if len(versions) != 1 or len(snapshot["embedding_versions"]) != 1:
        raise SystemExit(
            f"retrieval_ablation: 임베딩 버전이 하나가 아니다: {snapshot['embedding_versions']}"
        )
    return versions[0]


def load_corpus(
    stack: str, state: Mapping[str, Any], sample: Mapping[str, Any], questions: list[dict]
) -> dict[str, Any]:
    """요청자 JWT로 수집 결과를 읽어 정답 매핑과 스냅샷 해시를 만든다."""
    workspace = str(state["workspace_id"])
    titles = {d["id"]: d["title"] for d in sample["documents"]}
    with httpx.Client(timeout=60) as client:
        token = replay._login(client, stack, state)
        raw_sources = _select_all(client, stack, "raw_sources", workspace, "id,title", token)
        source_chunks = _select_all(
            client,
            stack,
            "source_chunks",
            workspace,
            "id,raw_source_id,chunk_index,content,char_start,char_end,embedding_version",
            token,
        )
        wiki_pages = _select_all(
            client, stack, "wiki_pages", workspace, "id,title,content,sources", token
        )
        wiki_chunks = _select_all(
            client,
            stack,
            "wiki_embeddings",
            workspace,
            "id,wiki_id,chunk_index,chunk_content,embedding_version",
            token,
        )
    raw_by_title: dict[str, str] = {}
    for source in raw_sources:
        title = str(source["title"])
        if title in raw_by_title:
            raise SystemExit(f"retrieval_ablation: 제목이 같은 원문이 둘 이상이다: {title}")
        raw_by_title[title] = str(source["id"])
    expected_by_question: dict[str, set[str] | None] = {}
    for question in questions:
        doc = str(question.get("doc"))
        docs = [] if doc == "none" else doc.split("+")
        if any(titles.get(d) not in raw_by_title for d in docs):
            expected_by_question[str(question["id"])] = None
        else:
            expected_by_question[str(question["id"])] = {raw_by_title[titles[d]] for d in docs}
    tables = {
        "raw_sources": raw_sources,
        "source_chunks": source_chunks,
        "wiki_pages": wiki_pages,
        "wiki_chunks": wiki_chunks,
    }
    return {
        "token": token,
        "tables": tables,
        "expected_by_question": expected_by_question,
        "wiki_sources": {
            str(p["id"]): {str(x) for x in (p.get("sources") or [])} for p in wiki_pages
        },
        "chunk_sources": {str(c["id"]): str(c["raw_source_id"]) for c in source_chunks},
        "snapshot": snapshot_inputs(**tables),
    }


def cmd_retrieve(args: argparse.Namespace) -> int:
    out = Path(args.out)
    # ⚠️ 요청보다 먼저 검사한다. 덮어쓰기 거부와 루프백 거부는 아무 요청도 하기 전에 멈춰야 한다.
    if out.exists():
        raise SystemExit(f"retrieval_ablation: 이미 있는 기록은 덮어쓰지 않는다: {out}")
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    stack = replay.assert_loopback(state["stack_url"])
    worker = replay.assert_loopback(args.worker_url)
    sample = replay._load_sample(Path(args.sample))
    questions = _questions_for(state, sample, args.limit)
    workspace = str(state["workspace_id"])
    inputs = args.inputs or list(INPUTS)
    scopes = args.scopes or list(SCOPES)

    corpus = load_corpus(stack, state, sample, questions)
    token, snapshot = corpus["token"], corpus["snapshot"]
    raw_sources, source_chunks = corpus["tables"]["raw_sources"], corpus["tables"]["source_chunks"]
    wiki_pages, wiki_chunks = corpus["tables"]["wiki_pages"], corpus["tables"]["wiki_chunks"]
    expected_by_question = corpus["expected_by_question"]
    wiki_sources, chunk_sources = corpus["wiki_sources"], corpus["chunk_sources"]
    embedding_version = _single_embedding_version(snapshot)
    if args.expect_snapshot and args.expect_snapshot != snapshot["snapshot_sha256"]:
        raise SystemExit(
            "retrieval_ablation: 수집 스냅샷이 기대값과 다르다. 새로 수집하지 않고 멈춘다: "
            f"{snapshot['snapshot_sha256']}"
        )

    def usage_total() -> int:
        with httpx.Client(timeout=30) as client:
            return int(replay._usage_total(client, stack, workspace))

    async def run() -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=60) as http:
            embed = (
                worker_embedder(
                    http, url=worker, token=args.query_embedding_token, workspace=workspace
                )
                if args.query_embedding_token
                else None
            )
            budget = EmbedBudget(
                cap_micros=args.embed_cap_micros, embed=embed, usage_total=usage_total
            )
            query_path = Path(args.query_vectors)
            query_vectors = load_query_vectors(query_path, questions)
            reused_query_vectors = query_vectors is not None
            if query_vectors is None:
                query_vectors = await build_query_vectors(questions, budget.embed)
                # 재사용될 때 비용이 사라지지 않게 만든 비용을 파일에 함께 둔다.
                query_vectors["embedding_micros"] = budget.spent_micros
                query_vectors["embedding_calls"] = budget.calls
                failed = failed_query_vectors(query_vectors)
                if failed:
                    # ⚠️ 실패를 담은 채 고정하면 일시 장애가 모든 조건의 실행 장애로 굳는다.
                    #    저장하지 않고 멈춘다. 다시 실행하면 처음부터 만든다.
                    raise SystemExit(
                        f"retrieval_ablation: 질의 벡터 {len(failed)}/{len(questions)}개를 만들지 "
                        f"못해 고정하지 않는다: {failed[:5]}"
                    )
                # 유료로 만든 벡터는 측정이 실패해도 남겨 재사용한다. 덮어쓰지 않는다.
                await asyncio.to_thread(_write_new, query_path, query_vectors)
            # 요청자 JWT로 운영과 같은 RPC를 부른다.
            # service_role을 쓰면 RLS가 빠진 다른 경로를 재게 된다.
            user_db = UserDb(
                http, supabase_url=stack, publishable_key=replay.LOCAL_ANON_KEY, access_token=token
            )
            dbs: dict[str, Any] = {"body": user_db}
            checks: dict[str, Any] = {}
            if "title_body" in inputs:
                local = LocalDb(args.db_container)
                ensure_ablation_schema(local)
                copy_body_vectors(local, workspace=workspace, embedding_version=embedding_version)
                checks["model_identity"] = await model_identity_check(
                    local, workspace=workspace, budget=budget
                )
                if not checks["model_identity"]["passed"]:
                    raise SystemExit(
                        "retrieval_ablation: 워커 임베딩 모델이 수집 때와 다르다: "
                        f"{checks['model_identity']}"
                    )
                items, title_failures = vector_items(
                    "title_body",
                    raw_sources=raw_sources,
                    source_chunks=source_chunks,
                    wiki_pages=wiki_pages,
                    wiki_chunks=wiki_chunks,
                )
                preparation = await prepare_title_vectors(
                    local,
                    workspace=workspace,
                    embedding_version=embedding_version,
                    items=items,
                    budget=budget,
                )
                preparation["failures"] = [*title_failures, *preparation["failures"]]
                checks["vector_preparation"] = preparation
                # ⚠️ 일부 청크만 벡터가 있으면 그 청크들은 title_body 검색에서 아예 빠진다.
                #    입력 효과가 아니라 색인 누락을 재게 되므로 측정하지 않는다.
                if preparation["failures"]:
                    raise SystemExit(
                        "retrieval_ablation: 제목 벡터를 모두 만들지 못했다. 다시 실행하면 만든 "
                        f"벡터는 재사용된다: {preparation['failures'][:5]} 외 "
                        f"{max(0, len(preparation['failures']) - 5)}건"
                    )
                limit = min(
                    DEFAULT_RETRIEVAL_POLICY.overfetch["source_vector"],
                    DEFAULT_RETRIEVAL_POLICY.vector_sql_max_candidates,
                )
                checks["equivalence"] = await equivalence_check(
                    workspace=workspace,
                    query_vectors=query_vectors,
                    product_db=user_db,
                    experiment_db=AblationRoutingDb(
                        user_db,
                        local,
                        input_format=INPUT_FORMATS["body"],
                        embedding_version=embedding_version,
                    ),
                    limit=limit,
                )
                if not checks["equivalence"]["passed"]:
                    raise SystemExit(
                        "retrieval_ablation: 실험 검색 함수가 운영 RPC와 다르다: "
                        f"{checks['equivalence']}"
                    )
                dbs["title_body"] = AblationRoutingDb(
                    user_db,
                    local,
                    input_format=INPUT_FORMATS["title_body"],
                    embedding_version=embedding_version,
                )
            embedder = FixedQueryEmbeddingClient(query_vectors)
            services = {s: RetrievalService(embedder, policy=scope_policy(s)) for s in scopes}

            async def retrieve(
                scope: str, embedding_input: str, query: str
            ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
                result = await services[scope].retrieve(
                    UUID(workspace), query, REQUESTED_K, dbs[embedding_input]
                )
                return [_evidence_json(hit) for hit in result.evidence], result.meta

            conditions = []
            for scope in scopes:
                for embedding_input in inputs:
                    conditions.append(
                        await evaluate_condition(
                            scope=scope,
                            embedding_input=embedding_input,
                            questions=questions,
                            expected_by_question=expected_by_question,
                            retrieve=retrieve,
                            wiki_sources=wiki_sources,
                            chunk_sources=chunk_sources,
                        )
                    )
                    print(
                        f"retrieval_ablation: {scope}x{embedding_input} "
                        f"hit@8={conditions[-1]['summary']['hit_at_8']}"
                    )
            return {
                "query_vectors": query_vectors,
                "query_vectors_reused": reused_query_vectors,
                "checks": checks,
                "conditions": conditions,
                "embedding_micros": budget.spent_micros,
                "embedding_calls": budget.calls,
            }

    outcome = asyncio.run(run())
    record = build_record(
        label=args.label,
        git_sha=_git_sha(),
        fixed=fixed_inputs(
            snapshot=snapshot, sample=sample, query_vectors=outcome["query_vectors"]
        ),
        snapshot_counts=snapshot["counts"],
        conditions=outcome["conditions"],
        checks=outcome["checks"],
        cost={
            # ⚠️ 이번 실행에서 낸 비용만이다. 재사용한 질의·제목 벡터의 비용은 그것을 만든 실행에
            #    들었다. 재사용 여부를 함께 적어 합계로 오해하지 않게 한다.
            "embedding_micros": outcome["embedding_micros"],
            "embedding_calls": outcome["embedding_calls"],
            "embedding_cap_micros": args.embed_cap_micros,
            "embedding_scope": "this_run_only",
            "reused_query_vectors": outcome["query_vectors_reused"],
            "reused_query_vectors_micros": (
                outcome["query_vectors"].get("embedding_micros")
                if outcome["query_vectors_reused"]
                else None
            ),
            "reused_title_vectors": (
                outcome["checks"].get("vector_preparation", {}).get("reused", 0)
            ),
            "reused_title_vectors_micros": (
                outcome["checks"].get("vector_preparation", {}).get("reused_micros", 0)
            ),
            "answer_micros": 0,
        },
    )
    write_record(out, record)
    print(compare_markdown([record]))
    return 0


def cmd_register(args: argparse.Namespace) -> int:
    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"retrieval_ablation: 이미 있는 등록은 덮어쓰지 않는다: {out}")
    registration = build_registration(
        cap_micros=args.cap_micros, turn_estimate_micros=args.turn_estimate_micros
    )
    _write_new(out, registration)
    print(f"retrieval_ablation: 사전 등록 {registration['rule_sha256'][:12]} → {out}")
    return 0


def _default_ask_prompt_sha256(stack: str, workspace: str, token: str) -> str | None:
    """답변에 쓰인 기본 Ask 템플릿의 해시. 조건 사이에 프롬프트가 바뀌면 비교가 깨진다."""
    columns = "id,system_prompt,template"
    with httpx.Client(timeout=30) as client:
        for scope in (f"eq.{workspace}", "is.null"):
            rows = replay._select(
                client,
                stack,
                "prompt_templates",
                {
                    "workspace_id": scope,
                    "target_type": "eq.ask",
                    "is_default": "eq.true",
                    "select": columns,
                },
                token=token,
            )
            if rows:
                return canonical_sha256(rows[0])
    return None


def _turn_message(stack: str, workspace: str, token: str, turn_id: str) -> dict[str, Any]:
    import time

    with httpx.Client(timeout=30) as client:
        # 마지막 프레임이 나간 뒤에 저장이 끝날 수 있어 잠시 기다린다(ask_replay와 같은 방식).
        for _ in range(10):
            rows = replay._select(
                client,
                stack,
                "ask_messages",
                {
                    "workspace_id": f"eq.{workspace}",
                    "client_turn_id": f"eq.{turn_id}",
                    "select": "status,trace_id",
                },
                token=token,
            )
            if rows:
                return dict(rows[0])
            time.sleep(0.5)
    return {}


def _turn_usage(stack: str, workspace: str, trace_id: str) -> list[dict[str, Any]]:
    with httpx.Client(timeout=30) as client:
        # usage_events는 service_role로만 읽힌다. workspace_id를 직접 건다.
        return replay._select(
            client,
            stack,
            "usage_events",
            {
                "workspace_id": f"eq.{workspace}",
                "trace_id": f"eq.{trace_id}",
                "kind": "neq.embedding",
                "select": "prompt_tokens,completion_tokens,cost_micros,model",
            },
        )


def cmd_answer(args: argparse.Namespace) -> int:
    from api.routers.ask import _start_ask_turn
    from api.services.ask import (
        AskService,
        HttpAskTurnExporter,
        HttpLlmStreamClient,
        drain_turn_exports,
    )
    from nexuswiki_core.trace import bind_trace, current_trace_id, new_trace_id

    out = Path(args.out)
    if out.exists():
        raise SystemExit(f"retrieval_ablation: 이미 있는 기록은 덮어쓰지 않는다: {out}")
    state = json.loads(Path(args.state).read_text(encoding="utf-8"))
    stack = replay.assert_loopback(state["stack_url"])
    worker = replay.assert_loopback(args.worker_url)
    registration = json.loads(Path(args.registration).read_text(encoding="utf-8"))
    retrieval = json.loads(Path(args.retrieval).read_text(encoding="utf-8"))
    check_registration(registration, retrieval)
    if retrieval.get("phase") != "retrieval":
        raise SystemExit("retrieval_ablation: --retrieval에는 검색 단계 기록을 준다")
    if not args.llm_token:
        raise SystemExit("retrieval_ablation: 답변 재생에 LLM_STREAM_INTERNAL_TOKEN이 필요하다")
    sample = replay._load_sample(Path(args.sample))
    questions = _questions_for(state, sample, args.limit)
    workspace = str(state["workspace_id"])
    corpus = load_corpus(stack, state, sample, questions)
    fixed = retrieval["fixed_inputs"]
    # ⚠️ 검색 기록과 다른 수집·질의 벡터 위에서 답하면 검색 판정과 답변 판정이 서로 다른 것을 잰다.
    if corpus["snapshot"]["snapshot_sha256"] != fixed["snapshot_sha256"]:
        raise SystemExit("retrieval_ablation: 수집 스냅샷이 검색 기록과 다르다")
    query_vectors = load_query_vectors(Path(args.query_vectors), questions)
    if (
        query_vectors is None
        or query_vectors_sha256(query_vectors) != fixed["query_vectors_sha256"]
    ):
        raise SystemExit("retrieval_ablation: 질의 벡터가 검색 기록과 다르다")
    selected, reasons = select_conditions(registration["rule"], retrieval["conditions"])
    print(f"retrieval_ablation: 재생 조건 {selected} · {reasons}")
    scope_of = {str(c["condition"]): str(c["scope"]) for c in retrieval["conditions"]}
    token = corpus["token"]
    prompt_sha = _default_ask_prompt_sha256(stack, workspace, token)
    embedding_version = _single_embedding_version(corpus["snapshot"])
    plan = [(name, scope_of[name], q) for name in selected for q in questions]

    async def run() -> tuple[list[dict[str, Any]], int, str | None]:
        async with httpx.AsyncClient(timeout=180) as http:
            user_db = UserDb(
                http, supabase_url=stack, publishable_key=replay.LOCAL_ANON_KEY, access_token=token
            )
            dbs: dict[str, Any] = {"body": user_db}
            if any(name.endswith("xtitle_body") for name in selected):
                local = LocalDb(args.db_container)
                items, failures = vector_items("title_body", **corpus["tables"])
                have = existing_vector_keys(
                    local,
                    workspace=workspace,
                    input_format=INPUT_FORMATS["title_body"],
                    embedding_version=embedding_version,
                )
                missing = [
                    i for i in items if (i["kind"], i["chunk_ref"], i["text_sha256"]) not in have
                ]
                if failures or missing:
                    raise SystemExit(
                        "retrieval_ablation: 검색 때의 제목 벡터가 모두 남아 있지 않다"
                    )
                dbs["title_body"] = AblationRoutingDb(
                    user_db,
                    local,
                    input_format=INPUT_FORMATS["title_body"],
                    embedding_version=embedding_version,
                )
            embedder = FixedQueryEmbeddingClient(query_vectors)
            llm = HttpLlmStreamClient(http, url=worker, token=args.llm_token, timeout_seconds=130)
            exporter = HttpAskTurnExporter(http, url=worker, token=args.llm_token)
            services = {
                name: AskService(
                    RetrievalService(embedder, policy=scope_policy(scope_of[name])),
                    llm,
                    exporter,
                    # 운영 기본과 같다. 단일 근거 조건에도 그대로 둔다(설계 Context).
                    quality_mode="enforce",
                )
                for name in selected
            }

            async def run_turn(name: str, scope: str, question: dict[str, Any]) -> dict[str, Any]:
                import time

                turn_id = uuid4()
                bind_trace(new_trace_id())
                thread_id = await _start_ask_turn(
                    db=user_db,
                    workspace_id=UUID(workspace),
                    thread_id=None,
                    client_turn_id=turn_id,
                    query=str(question["query"]),
                )
                trace_id = current_trace_id() or ""
                started = time.monotonic()
                events = [
                    event
                    async for event in services[name].ask(
                        workspace_id=UUID(workspace),
                        query=str(question["query"]),
                        requested_k=REQUESTED_K,
                        template_id=None,
                        user_db=dbs[name.split("x", 1)[1]],
                        thread_id=thread_id,
                        client_turn_id=turn_id,
                    )
                ]
                elapsed = round((time.monotonic() - started) * 1000)
                message = await asyncio.to_thread(
                    _turn_message, stack, workspace, token, str(turn_id)
                )
                usage = await asyncio.to_thread(_turn_usage, stack, workspace, trace_id)
                row = turn_row(question, events, message, usage, elapsed)
                print(
                    f"retrieval_ablation: {name} {row['id']} {row['status']} "
                    f"hit={row['keyword_hit']} cost={row['cost_micros']}"
                )
                return row

            result = await run_answers(
                plan=plan,
                run_turn=run_turn,
                cap_micros=int(registration["answer_cap_micros"]),
                turn_estimate_micros=int(registration["turn_estimate_micros"]),
            )
            await drain_turn_exports()
            return result

    rows, spent, stopped = asyncio.run(run())
    record = build_answer_record(
        label=args.label,
        git_sha=_git_sha(),
        retrieval=retrieval,
        registration=registration,
        selected=selected,
        reasons=reasons,
        prompt_sha256=prompt_sha,
        rows=rows,
        spent=spent,
        stopped=stopped,
    )
    write_record(out, record)
    print(compare_markdown([retrieval, record]))
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    records = [json.loads(Path(p).read_text(encoding="utf-8")) for p in args.records]
    print(compare_markdown(records))
    return 0


def cmd_cleanup(args: argparse.Namespace) -> int:
    drop_ablation_schema(LocalDb(args.db_container))
    print("retrieval_ablation: ablation 스키마를 지웠다")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    retrieve = sub.add_parser("retrieve", help="근거 범위 × 임베딩 입력 조건으로 검색만 잰다")
    retrieve.add_argument("--state", required=True, help="ask_replay seed가 만든 state 파일")
    retrieve.add_argument(
        "--query-vectors", required=True, help="고정 질의 벡터 파일(없으면 만든다)"
    )
    retrieve.add_argument("--out", required=True)
    retrieve.add_argument("--label", default="retrieve")
    retrieve.add_argument("--sample", default=str(replay.DEFAULT_SAMPLE))
    # ask_replay_serve.sh가 띄우는 워커 내부 리스너.
    retrieve.add_argument("--worker-url", default="http://127.0.0.1:8081")
    retrieve.add_argument("--query-embedding-token", default=None)
    retrieve.add_argument("--db-container", default=DEFAULT_DB_CONTAINER)
    retrieve.add_argument(
        "--embed-cap-micros",
        type=int,
        default=None,
        help="질의·제목 벡터와 모델 확인에 쓰는 유료 임베딩 상한. 없으면 유료 호출을 하지 않는다",
    )
    retrieve.add_argument("--expect-snapshot", default=None, help="기대 수집 스냅샷 해시")
    retrieve.add_argument("--scopes", nargs="*", choices=list(SCOPES))
    retrieve.add_argument("--inputs", nargs="*", choices=list(INPUTS))
    retrieve.add_argument("--limit", type=int, default=0)
    retrieve.set_defaults(func=cmd_retrieve)

    register = sub.add_parser("register", help="답변 재생 선택 규칙과 비용 상한을 먼저 기록한다")
    register.add_argument("--out", required=True)
    register.add_argument("--cap-micros", type=int, required=True)
    register.add_argument("--turn-estimate-micros", type=int, default=DEFAULT_TURN_ESTIMATE_MICROS)
    register.set_defaults(func=cmd_register)

    answer = sub.add_parser("answer", help="사전 등록 규칙이 고른 조건만 답변을 재생한다")
    answer.add_argument("--state", required=True)
    answer.add_argument("--registration", required=True)
    answer.add_argument("--retrieval", required=True, help="retrieve가 쓴 검색 기록")
    answer.add_argument("--query-vectors", required=True)
    answer.add_argument("--out", required=True)
    answer.add_argument("--label", default="answer")
    answer.add_argument("--sample", default=str(replay.DEFAULT_SAMPLE))
    answer.add_argument("--worker-url", default="http://127.0.0.1:8081")
    answer.add_argument("--llm-token", default=None)
    answer.add_argument("--db-container", default=DEFAULT_DB_CONTAINER)
    answer.add_argument("--limit", type=int, default=0)
    answer.set_defaults(func=cmd_answer)

    compare = sub.add_parser("compare", help="고정 입력이 같은 기록들의 조건을 비교한다")
    compare.add_argument("records", nargs="+")
    compare.set_defaults(func=cmd_compare)

    cleanup = sub.add_parser("cleanup", help="로컬 ablation 스키마를 지운다")
    cleanup.add_argument("--db-container", default=DEFAULT_DB_CONTAINER)
    cleanup.set_defaults(func=cmd_cleanup)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    import os

    if getattr(args, "query_embedding_token", "unset") is None:
        args.query_embedding_token = os.environ.get("QUERY_EMBEDDING_INTERNAL_TOKEN")
    if getattr(args, "llm_token", "unset") is None:
        args.llm_token = os.environ.get("LLM_STREAM_INTERNAL_TOKEN")
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
