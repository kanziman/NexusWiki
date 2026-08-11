"""parse 잡 — 원문을 청크로 잘라 `source_chunks`에 쓰고 compile로 체인한다.

관련 태스크: P2-ING-02 (ING-05, COMP-04, COMP-07)
설계 근거: 03-04-PLAN.md > D-P10 (잡 4종과 dedup 키 규약)
설계 근거: 03-03-PLAN.md > D-P4, D-P5 (청킹 파라미터)
설계 근거: checklists.json > decisions.db_access, decisions.job_queue

  parse ──complete_job_and_chain(next_type='compile')──> compile

⚠️ 이 핸들러는 재시도 판정을 하지 않는다. 실패는 예외로 던지고 `worker.queue`가
`fail_job`으로 넘긴다 — 핸들러가 스스로 재시도하면 큐의 attempts 회계가 거짓이 된다.

⚠️ 멱등성: 잡은 at-least-once다. 두 번 돌아도 청크 행 수가 늘지 않는 것은
`source_chunks_source_index_key (raw_source_id, chunk_index)` 업서트 키가 보장한다.

소비자: `worker.handlers.HANDLERS`
"""

from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, Final

import httpx

from nexuswiki_core.chunking import CHUNKER_VERSION, chunk_text
from nexuswiki_core.citations import strip_forged_anchors
from nexuswiki_core.domain import SourceType
from nexuswiki_core.extract import ExtractionQualityError, assert_extraction_quality, extract_text
from nexuswiki_core.logging import get_logger
from nexuswiki_core.tokenizer import TSV_TOKENIZER_VERSION, bigram, normalize
from worker.db.service import ServiceDb, service_client
from worker.errors import StorageObjectMissing
from worker.fetch import fetch_source
from worker.settings import WorkerSettings
from worker.storage import download_source_object, storage_client

__all__ = ["PARSE_JOB_TYPE", "SourceNotExtractedError", "handle_parse", "run_parse"]

PARSE_JOB_TYPE: Final[str] = "parse"

_logger = get_logger(__name__)


class SourceNotExtractedError(RuntimeError):
    """원문 평문이 아직 없다 — 추출 단계가 앞에 필요하다.

    ⚠️ `NotImplementedError`가 아니라 자체 예외인 이유: 이것은 "코드가 없다"가 아니라
    **"이 소스는 아직 추출되지 않았다"는 데이터 상태**다. 텍스트 소스는 라우터가
    `content`를 채워 넣으므로 이 분기에 오지 않는다.
    """


async def handle_parse(*, job_id: str, workspace_id: str, payload: dict[str, Any]) -> None:
    """`JobHandler` 계약 진입점 — 자기 수명 동안만 service key 클라이언트를 연다.

    ⚠️ 모듈 전역 클라이언트를 두지 않는다. 두는 순간 import가 키를 읽으려 시도하게 되어
    02-CONTEXT.md > D-06의 인과가 흐려진다. 실제 작업은 `run_parse`가 하고 그쪽은 `db`를
    주입받으므로 네트워크 없이 테스트할 수 있다.
    """
    settings = WorkerSettings()
    async with AsyncExitStack() as stack:
        client = await stack.enter_async_context(service_client(settings))
        fetch_client = await stack.enter_async_context(
            httpx.AsyncClient(timeout=httpx.Timeout(settings.FETCH_TIMEOUT_SECONDS))
        )
        object_client = await stack.enter_async_context(storage_client(settings))
        await run_parse(
            ServiceDb(client),
            job_id=job_id,
            workspace_id=workspace_id,
            payload=payload,
            settings=settings,
            fetch_client=fetch_client,
            object_client=object_client,
        )


async def run_parse(
    db: ServiceDb,
    *,
    job_id: str,
    workspace_id: str,
    payload: dict[str, Any],
    settings: WorkerSettings | None = None,
    fetch_client: httpx.AsyncClient | None = None,
    object_client: httpx.AsyncClient | None = None,
) -> None:
    raw_source_id = str(payload.get("raw_source_id") or payload.get("target_id") or "")
    if not raw_source_id:
        raise ValueError("parse 잡 payload에 raw_source_id가 없다")

    source = await db.get_raw_source(raw_source_id, workspace_id=workspace_id)
    if source is None:
        raise LookupError(f"raw_source를 찾을 수 없다: {raw_source_id}")

    try:
        source_type = SourceType(str(source["source_type"]))
    except (KeyError, ValueError) as error:
        raise ExtractionQualityError(reason="unsupported_source_type") from error

    content = str(source.get("content") or "")
    if source_type is SourceType.TEXT:
        if not content.strip():
            raise ExtractionQualityError(reason="empty_extraction")
    elif source_type is SourceType.FILE:
        storage_path = source.get("storage_path")
        if not isinstance(storage_path, str) or not storage_path:
            raise StorageObjectMissing()
        # ⚠️ service key는 0005의 Storage 정책을 지나지 않는다. 첫 세그먼트 대조가
        #    다른 워크스페이스 객체를 읽지 않는 유일한 테넌트 경계다.
        if storage_path.split("/", 1)[0] != workspace_id:
            raise StorageObjectMissing()
        if settings is None or object_client is None:
            raise RuntimeError("파일 parse에는 worker settings와 Storage client가 필요하다")
        result = extract_text(
            data=await download_source_object(object_client, path=storage_path),
            mime_type=str(source.get("mime_type") or ""),
        )
        assert_extraction_quality(result)
        content = result.text
        await db.update_raw_source_content(
            raw_source_id, workspace_id=workspace_id, content=content
        )
        _log_extraction(raw_source_id, result, mime_type=str(source.get("mime_type") or ""))
    elif source_type is SourceType.URL:
        metadata = source.get("metadata") or {}
        url = metadata.get("url") if isinstance(metadata, dict) else None
        if not isinstance(url, str) or not url:
            raise ExtractionQualityError(reason="unsupported_source_type")
        if settings is None or fetch_client is None:
            raise RuntimeError("URL parse에는 worker settings와 HTTP client가 필요하다")
        fetched = await fetch_source(fetch_client, url, settings=settings)
        result = extract_text(data=fetched.data, mime_type=fetched.mime_type)
        assert_extraction_quality(result)
        content = result.text
        await db.update_raw_source_content(
            raw_source_id,
            workspace_id=workspace_id,
            content=content,
            mime_type=fetched.mime_type,
            byte_size=len(fetched.data),
        )
        _log_extraction(raw_source_id, result, mime_type=fetched.mime_type)
        if fetched.final_url != url:
            _logger.info(
                "worker.parse_url_redirected", requested_url=url, final_url=fetched.final_url
            )
    else:
        raise ExtractionQualityError(reason="unsupported_source_type")

    # 05-CONTEXT.md > D-04/CITE-06: 모든 소스 유형이 합류한 뒤, 청킹 전에 한 번만 제거한다.
    content = strip_forged_anchors(content)
    chunks = chunk_text(content)
    rows = [
        {
            "chunk_index": chunk.index,
            "content": chunk.content,
            "char_start": chunk.char_start,
            "char_end": chunk.char_end,
            "chunker_version": CHUNKER_VERSION,
            # ⚠️ `search_tsv`와 `tsv_tokenizer_version`을 **의도적으로 비운다.**
            #    `search_tsv`는 `tsvector` 컬럼이고 그 값을 만드는 `to_tsvector`를
            #    애플리케이션이 부를 수 없다(PostgREST로는 문자열이 그대로 캐스팅되지
            #    않는다). 어휘 채널(RTV)은 Phase 4의 범위이며 그때 `0010`이 색인용 RPC를
            #    추가하는 것이 "검색 쿼리는 마이그레이션이 소유한다"
            #    (checklists.json > decisions.db_transport)와 일치한다.
            #    ⚠️ 그때까지 이 청크들은 **어휘 검색에 잡히지 않는다.** 조용히 비우면
            #    Phase 4가 "왜 한국어 검색이 0건인가"의 원인을 못 찾으므로 여기 남긴다.
        }
        for chunk in chunks
    ]

    stored_rows = await db.upsert_source_chunks(
        workspace_id=workspace_id, raw_source_id=raw_source_id, rows=rows
    )
    for row in stored_rows:
        chunk_id = row.get("id")
        content = row.get("content")
        if not isinstance(chunk_id, str) or not isinstance(content, str):
            raise RuntimeError(
                "source_chunks 업서트가 lexical 색인에 필요한 id/content를 돌려주지 않았다"
            )
        await db.index_source_chunk_lexical(
            workspace_id=workspace_id,
            source_chunk_id=chunk_id,
            bigrams=bigram(normalize(content)),
            tokenizer_version=TSV_TOKENIZER_VERSION,
        )
    # 축소 재처리 잔여 삭제 (COMP-07). 업서트는 있는 행을 덮을 뿐 없어진 행을 지우지 않는다.
    removed = await db.delete_source_chunks_from(
        workspace_id=workspace_id, raw_source_id=raw_source_id, from_index=len(rows)
    )

    _logger.info(
        "worker.parse_chunked",
        raw_source_id=raw_source_id,
        chunk_count=len(rows),
        removed_count=len(removed),
        chunker_version=CHUNKER_VERSION,
    )

    try:
        await db.enqueue_job(
            workspace_id=workspace_id,
            job_type="embed",
            payload={
                "target_id": f"{raw_source_id}:source",
                "raw_source_id": raw_source_id,
                "scope": "source",
            },
        )
    except Exception as error:
        if "23505" not in str(error):
            raise
    # ⚠️ 원문 임베딩 잡(`embed`, scope=source)의 직접 인큐는 여기서 하지 않는다.
    #    `embed` 핸들러가 아직 없고 03-08이 미등록 잡 type을 즉시 `dead`로 보내기로 했으므로
    #    지금 인큐하면 스모크가 죽은 잡을 만든다. 여기에 03-09(COMP-06)가
    #      await db.enqueue_job(
    #          workspace_id=workspace_id,
    #          job_type="embed",
    #          payload={"target_id": f"{raw_source_id}:source", "scope": "source"},
    #      )
    #    한 줄을 더한다 — D-P10의 dedup 키 규약(`<rsid>:source`)을 따르고 23505는
    #    "이미 큐에 있음"으로 정상 처리한다. 한 줄을 더하는 자리이지 구조를 바꾸는 자리가 아니다.
    await db.complete_job_and_chain(
        job_id,
        next_type="compile",
        next_payload={"target_id": raw_source_id, "raw_source_id": raw_source_id},
    )


def _log_extraction(raw_source_id: str, result: Any, *, mime_type: str) -> None:
    _logger.info(
        "worker.parse_extracted",
        raw_source_id=raw_source_id,
        pages=result.page_count,
        chars=len(result.text),
        mime_type=mime_type,
        extractor=result.extractor,
    )
