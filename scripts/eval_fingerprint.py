"""평가 기록이 공유하는 고정 입력 지문. 순수 함수만 둔다(네트워크 · DB · 무거운 import 없음).

`ask_replay.py`(답변 재생 · 검색 채점)와 `retrieval_ablation.py`(#232 6조건 실험)가 같은 정의를
써야 같은 수집 위의 기록끼리 묶거나 비교할 수 있다. 두 곳에 따로 두면 정의가 조용히 어긋나고,
같은 수집인데도 지문이 달라 묶음이 거부된다.

⚠️ 이 파일의 해시 정의를 바꾸면 이미 남긴 기록(#232 `fixed_inputs.snapshot_sha256` 등)과
   지문이 달라진다. 정의를 바꿔야 한다면 새 이름의 함수를 더하고 기존 함수는 그대로 둔다.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_sha256(value: Any) -> str:
    """키 정렬 · 공백 없는 JSON의 sha256. 같은 값이면 dict 순서와 무관하게 같은 해시다."""
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def fixture_sha256(sample: Any) -> str:
    """질문 fixture 전체(문서 · 질문 · 기대 사실)의 해시. 질문 하나만 바뀌어도 다르다."""
    return canonical_sha256(sample)


def snapshot_inputs(
    *,
    raw_sources: list[dict[str, Any]],
    source_chunks: list[dict[str, Any]],
    wiki_pages: list[dict[str, Any]],
    wiki_chunks: list[dict[str, Any]],
) -> dict[str, Any]:
    """수집 스냅샷과 청크 경계를 해시로 고정한다. 본문은 기록에 남기지 않는다.

    입력 행의 열은 `ask_replay.SNAPSHOT_COLUMNS`가 정한다. 열 목록이 곧 해시 대상이다.

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
                text_sha256(str(c.get("content") or "")),
            )
            for c in source_chunks
        ),
        "wiki_pages": sorted(
            (
                str(p["id"]),
                str(p.get("title") or ""),
                text_sha256(str(p.get("content") or "")),
                sorted(str(s) for s in (p.get("sources") or [])),
            )
            for p in wiki_pages
        ),
        "wiki_chunks": sorted(
            (
                str(c["wiki_id"]),
                int(c["chunk_index"]),
                text_sha256(str(c.get("chunk_content") or "")),
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
