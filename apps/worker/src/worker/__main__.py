"""SIGTERM을 직접 처리하는 worker 프로세스 진입점.

관련 태스크: P0-INIT-02, P2-BE-01, P2-JOB-01
설계 근거: 01-CONTEXT.md > D-03, D-13 · 02-CONTEXT.md > D-07, D-10, D-18
"""

import asyncio
import signal
from collections.abc import AsyncIterator, Iterable
from datetime import UTC, datetime
from typing import Any

import httpx
import uvicorn
from fastapi import FastAPI

from nexuswiki_core.deployment import resolve_git_sha
from nexuswiki_core.logging import (
    bind_job_context,
    clear_job_context,
    configure_logging,
    get_logger,
)
from nexuswiki_core.observability import configure_observability, flush_observability
from nexuswiki_core.trace import TraceMiddleware
from worker.ask_cost import AskCostAccounting
from worker.ask_turn_export import add_ask_turn_export_route
from worker.db.service import ServiceDb, service_client
from worker.llm import openrouter_client
from worker.llm_gateway import (
    LlmCallContext,
    LlmGateway,
    open_answer_stream,
    record_stream_usage,
)
from worker.llm_stream import LlmChatRequest, LlmStreamService, add_llm_stream_route
from worker.query_embedding import (
    QueryEmbeddingService,
    add_query_embedding_route,
    request_workspace_id,
)
from worker.queue import resolve_worker_id, run_queue_loop
from worker.queue_baseline import measure_queue_roundtrip
from worker.rtt import measure_rtt
from worker.schema_guard import assert_enums_match_db
from worker.settings import WorkerSettings
from worker.youtube import (
    YoutubeSearchRequest,
    YoutubeSearchResponse,
    YoutubeSearchService,
    YoutubeVideoListRequest,
    YoutubeVideoListResponse,
    YoutubeVideoListService,
    add_youtube_search_route,
    add_youtube_videos_route,
    list_channel_videos,
    search_channels,
)

# 응답 뒤에 끝나는 사용량 기록 태스크. 강한 참조가 없으면 GC가 완료 전에 거둬 갈 수 있다.
_pending_usage_writes: set[asyncio.Task[None]] = set()

# ⚠️ 큐의 잡 반납(`WORKER_GRACE_SECONDS`)과 동시에 돌므로 그 예산을 쓰지 않지만, 플랫폼의
#    SIGKILL 안에는 끝나야 한다. 사용량 INSERT 한 건은 이 시간이면 충분하다.
_USAGE_DRAIN_SECONDS = 2.0

# ⚠️ 없으면 uvicorn은 진행 중인 스트림이 끝날 때까지 기다린다. 스트림 상한은 130초이고 플랫폼의
#    SIGKILL은 30초라, 그 사이에 맞으면 사용량 기록과 관측 flush가 모두 사라진다. 시간이 지나면
#    스트림을 취소하고, 취소된 스트림은 `incomplete`로 기록된다. 아래 드레인과 flush를 더해도
#    `PLATFORM_GRACE_SECONDS` 안에 들어오도록 정한 값이다.
_LISTENER_SHUTDOWN_SECONDS = 15


class _QueryUsageSink:
    """질의 임베딩의 사용량을 응답과 분리해 기록한다.

    ⚠️ 기록을 기다리면 임베딩 타임아웃(`QUERY_EMBEDDING_TIMEOUT_SECONDS`) 안에 DB 왕복이 들어가고,
    기록 실패가 검색 실패가 된다. 스펙은 기록 실패가 질의를 실패시키지 않도록 요구한다.
    """

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings

    async def insert_usage_event(self, *, workspace_id: str, row: dict[str, Any]) -> None:
        if not workspace_id:
            # 이전 버전 API는 워크스페이스를 보내지 않는다. 귀속할 곳이 없으니 흔적만 남긴다.
            get_logger(__name__).warning("worker.query_embedding_usage_unattributed")
            return
        task = asyncio.create_task(self._write(workspace_id, row))
        _pending_usage_writes.add(task)
        task.add_done_callback(_pending_usage_writes.discard)

    async def _write(self, workspace_id: str, row: dict[str, Any]) -> None:
        try:
            async with service_client(self._settings) as client:
                await ServiceDb(client).insert_usage_event(workspace_id=workspace_id, row=row)
        except Exception:  # noqa: BLE001 - 응답은 이미 나갔다. 원인은 로그로 남긴다.
            get_logger(__name__).exception("worker.query_embedding_usage_failed")


async def _drain_usage_writes(
    timeout_seconds: float = _USAGE_DRAIN_SECONDS,
    *,
    stream_records: Iterable[asyncio.Task[None]] = (),
) -> None:
    """종료 전에 남은 사용량 기록을 기다린다. 취소된 스트림의 기록도 함께 기다린다.

    ⚠️ 그대로 두면 `asyncio.run`이 태스크를 취소하고, `CancelledError`는 `except Exception`에
    걸리지 않아 기록도 로그도 없이 사라진다. 그만큼의 비용이 월 상한에서 빠진다.
    """
    pending = _pending_usage_writes | set(stream_records)
    if not pending:
        return
    _, unfinished = await asyncio.wait(pending, timeout=timeout_seconds)
    if unfinished:
        get_logger(__name__).warning("worker.usage_writes_abandoned", count=len(unfinished))


async def _embed_query(settings: WorkerSettings, text: str) -> list[float]:
    async with openrouter_client(settings) as client:
        result = await LlmGateway(_QueryUsageSink(settings), client, settings).embed_texts(
            LlmCallContext(workspace_id=request_workspace_id() or "", call="query_embedding"),
            texts=[text],
        )
    return result.vectors[0]


async def _search_youtube_channels(
    settings: WorkerSettings, request: YoutubeSearchRequest
) -> YoutubeSearchResponse:
    """`_embed_query`와 같은 형태 — per-call client를 열고 검색 한 번에 닫는다.

    ⚠️ 키가 없으면 라우트 자체가 등록되지 않으므로(`_serve_internal_listeners`) 여기서는
    키가 있다고 단정한다. 그 단정이 깨지면 조용한 오동작이 아니라 예외로 드러나야 한다.
    """
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY 없이 검색 라우트가 등록됐다")
    async with httpx.AsyncClient() as client:
        return await search_channels(
            client,
            api_key=api_key,
            query=request.query,
            region_code=request.region_code,
            page_token=request.page_token,
            timeout_seconds=settings.YOUTUBE_SEARCH_TIMEOUT_SECONDS,
            order=request.order,
            relevance_language=request.relevance_language,
        )


async def _list_youtube_videos(
    settings: WorkerSettings, request: YoutubeVideoListRequest
) -> YoutubeVideoListResponse:
    """`_search_youtube_channels`와 같은 형태 — 키 단정도 같은 이유로 여기 둔다."""
    api_key = settings.YOUTUBE_API_KEY
    if not api_key:
        raise RuntimeError("YOUTUBE_API_KEY 없이 영상 목록 라우트가 등록됐다")
    async with httpx.AsyncClient() as client:
        return await list_channel_videos(
            client,
            api_key=api_key,
            channel_id=request.channel_id,
            page_token=request.page_token,
            timeout_seconds=settings.YOUTUBE_VIDEOS_TIMEOUT_SECONDS,
        )


async def _stream_llm_chat(
    settings: WorkerSettings, request: LlmChatRequest
) -> AsyncIterator[bytes]:
    """`_embed_query`와 같은 형태 — per-call client를 열고 스트림이 끝날 때까지 붙든다."""
    async with openrouter_client(settings) as client:
        kwargs = {}
        if request._cost_call is not None:
            kwargs = {
                "max_tokens": request._cost_call["max_tokens"],
                "on_generation": request._on_generation,
            }
        async for chunk in open_answer_stream(
            client, settings=settings, messages=request.messages, **kwargs
        ):
            yield chunk


async def _check_ask_budget(settings: WorkerSettings, workspace_id: str) -> bool:
    """Use the same inclusive monthly-cap boundary as ``enqueue_source_job``."""
    async with service_client(settings) as client:
        db = ServiceDb(client)
        cap = await db.get_workspace_budget_cap(workspace_id=workspace_id)
        if cap is None:
            return True
        now = datetime.now(UTC)
        since = datetime(now.year, now.month, 1, tzinfo=UTC).isoformat()
        spent = await db.sum_usage_events_since(workspace_id=workspace_id, since=since)
    return spent < cap


async def _record_ask_usage(
    settings: WorkerSettings,
    workspace_id: str,
    usage: dict[str, Any],
    *,
    incomplete: bool,
    duration_ms: int,
) -> None:
    """Persist one Ask call, marking a stream that ended before final usage arrived."""
    async with service_client(settings) as client:
        await record_stream_usage(
            ServiceDb(client),
            LlmCallContext(workspace_id=workspace_id, call="ask"),
            usage=usage,
            duration_ms=duration_ms,
            incomplete=incomplete,
        )


async def _serve_internal_listeners(settings: WorkerSettings, stop: asyncio.Event) -> None:
    """Run the private listener(s) until the queue process receives its stop signal.

    05-01-PLAN.md Task 1: query-embedding과 llm-chat 두 라우트를 **하나의** FastAPI
    앱/uvicorn.Server에 올린다 — 05-RESEARCH.md Pattern 1이 명시적으로 경고하는 대로,
    두 번째 `uvicorn.Server`를 추가하면 SIGTERM 종료 표면만 두 배가 되고 격리 이득은
    없다(`railway.json`의 private-networking 토글은 서비스 단위이지 포트 단위가 아니다).
    """
    if (
        not settings.QUERY_EMBEDDING_INTERNAL_TOKEN
        and not settings.LLM_STREAM_INTERNAL_TOKEN
        and not settings.YOUTUBE_SEARCH_INTERNAL_TOKEN
    ):
        # No listener is safer than an unauthenticated listener during local setup.
        return
    llm_service: LlmStreamService | None = None
    app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
    # 이 리스너는 내부 토큰으로 인증되는 사설망 전용이라 API가 보낸 trace를 신뢰한다.
    # 값이 없으면 이전 버전 API의 호출이므로 거부하지 않고 새로 발급한다 (design D2).
    app.add_middleware(
        TraceMiddleware, log_event="worker.internal_request_completed", trust_inbound=True
    )
    if settings.QUERY_EMBEDDING_INTERNAL_TOKEN:
        add_query_embedding_route(
            app,
            QueryEmbeddingService(
                lambda text: _embed_query(settings, text),
                internal_token=settings.QUERY_EMBEDDING_INTERNAL_TOKEN,
                max_text_chars=settings.QUERY_EMBEDDING_MAX_TEXT_CHARS,
                timeout_seconds=settings.QUERY_EMBEDDING_TIMEOUT_SECONDS,
                max_concurrency=settings.QUERY_EMBEDDING_MAX_CONCURRENCY,
                rate_capacity=settings.QUERY_EMBEDDING_RATE_CAPACITY,
                refill_tokens_per_second=settings.QUERY_EMBEDDING_RATE_REFILL_TOKENS_PER_SECOND,
            ),
        )
    if settings.LLM_STREAM_INTERNAL_TOKEN:
        llm_service = LlmStreamService(
            lambda request: _stream_llm_chat(settings, request),
            internal_token=settings.LLM_STREAM_INTERNAL_TOKEN,
            accounting=AskCostAccounting(settings),
            check_budget=lambda workspace_id: _check_ask_budget(settings, workspace_id),
            record_usage=lambda workspace_id, usage, *, incomplete, duration_ms: _record_ask_usage(
                settings,
                workspace_id,
                usage,
                incomplete=incomplete,
                duration_ms=duration_ms,
            ),
            max_concurrency=settings.LLM_STREAM_MAX_CONCURRENCY,
            rate_capacity=settings.LLM_STREAM_RATE_CAPACITY,
            refill_tokens_per_second=settings.LLM_STREAM_RATE_REFILL_TOKENS_PER_SECOND,
        )
        add_llm_stream_route(app, llm_service)
        # LLM 호출과 같은 호출자, 같은 경계이므로 토큰을 공유한다. API가 Langfuse 키를 갖지 않게
        # 하려고 턴 보고서를 여기서 내보낸다 (design D8).
        add_ask_turn_export_route(app, internal_token=settings.LLM_STREAM_INTERNAL_TOKEN)
    # ⚠️ 키가 없으면 라우트를 아예 등록하지 않는다. 등록해두고 호출 시점에 실패시키면
    #    쿼터 소진과 "키 미설정"이 같은 502로 뭉개져, 배포 설정 실수가 업스트림 장애로
    #    위장된다.
    if settings.YOUTUBE_SEARCH_INTERNAL_TOKEN and settings.YOUTUBE_API_KEY:
        add_youtube_search_route(
            app,
            YoutubeSearchService(
                lambda request: _search_youtube_channels(settings, request),
                internal_token=settings.YOUTUBE_SEARCH_INTERNAL_TOKEN,
                max_query_chars=settings.YOUTUBE_SEARCH_MAX_QUERY_CHARS,
                timeout_seconds=settings.YOUTUBE_SEARCH_TIMEOUT_SECONDS,
                max_concurrency=settings.YOUTUBE_SEARCH_MAX_CONCURRENCY,
                rate_capacity=settings.YOUTUBE_SEARCH_RATE_CAPACITY,
                refill_tokens_per_second=settings.YOUTUBE_SEARCH_RATE_REFILL_TOKENS_PER_SECOND,
            ),
        )
        add_youtube_videos_route(
            app,
            YoutubeVideoListService(
                lambda request: _list_youtube_videos(settings, request),
                internal_token=settings.YOUTUBE_SEARCH_INTERNAL_TOKEN,
                timeout_seconds=settings.YOUTUBE_VIDEOS_TIMEOUT_SECONDS,
                max_concurrency=settings.YOUTUBE_VIDEOS_MAX_CONCURRENCY,
                rate_capacity=settings.YOUTUBE_VIDEOS_RATE_CAPACITY,
                refill_tokens_per_second=settings.YOUTUBE_VIDEOS_RATE_REFILL_TOKENS_PER_SECOND,
            ),
        )
    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host="0.0.0.0",
            port=8081,
            log_level="warning",
            timeout_graceful_shutdown=_LISTENER_SHUTDOWN_SECONDS,
        )
    )
    server_task = asyncio.create_task(server.serve())
    await stop.wait()
    server.should_exit = True
    await server_task
    await _drain_usage_writes(
        stream_records=llm_service.pending_records() if llm_service is not None else ()
    )


async def _run_queue_baseline_probe(
    db: ServiceDb,
    *,
    settings: WorkerSettings,
    worker_id: str,
    git_sha: str | None,
) -> None:
    """큐 기준선 프로브를 기동 시 한 번만 돌린다 (기본은 꺼져 있다).

    ⚠️ 이 프로브는 200회가 넘는 잡을 만들고 그 행을 지우지 못한다. 큐 루프가
    시작되기 **전에** 돌려야 자기 프로브 잡과 루프가 서로 잡을 뺏지 않는다.
    근거: 02-CONTEXT.md > D-17.
    """
    logger = get_logger(__name__)
    if not settings.QUEUE_BASELINE_ENABLED:
        return
    if not settings.QUEUE_BASELINE_WORKSPACE_ID:
        logger.warning("worker.queue_baseline_skipped", reason="no_workspace_id", git_sha=git_sha)
        return
    try:
        result = await measure_queue_roundtrip(
            db,
            workspace_id=settings.QUEUE_BASELINE_WORKSPACE_ID,
            worker_id=worker_id,
        )
        logger.info(
            "worker.queue_baseline_measured",
            cold_first_ms=result.cold_first_ms,
            p50_ms=result.p50_ms,
            p95_ms=result.p95_ms,
            p99_ms=result.p99_ms,
            sample_count=result.sample_count,
            warmup_count=result.warmup_count,
            failures=result.failures,
            git_sha=git_sha,
        )
    except Exception:
        logger.exception("worker.queue_baseline_failed", git_sha=git_sha)


async def main() -> None:
    # ⚠️ 부팅 시점 실패가 일어나는 지점이다. worker가 `SUPABASE_SECRET_KEY` 없이
    # 조용히 뜨면 BYPASSRLS 경로가 자격증명 없이 도는 것과 같아진다. 여기서 죽는
    # 것이 그것보다 안전하다. 근거: 02-CONTEXT.md > D-10.
    settings = WorkerSettings()

    configure_logging(
        environment=settings.ENVIRONMENT,
        log_level=settings.LOG_LEVEL,
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop.set)
    loop.add_signal_handler(signal.SIGINT, stop.set)

    bind_job_context(job_id="bootstrap", workspace_id="bootstrap")
    logger = get_logger(__name__)
    git_sha = resolve_git_sha()
    logger.info(
        "worker.started",
        git_sha=git_sha,
    )
    configure_observability(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        base_url=settings.LANGFUSE_BASE_URL,
        environment=settings.ENVIRONMENT,
        release=git_sha,
    )
    try:
        # 필수 설정 누락으로 프로브를 건너뛰는 분기는 없앴다 — 그 경우 위에서 이미
        # 죽는다. 남은 것은 의도적으로 프로브를 끄는 운영 토글뿐이다.
        if not settings.RTT_PROBE_ENABLED:
            logger.info("worker.rtt_skipped", reason="disabled", git_sha=git_sha)
        else:
            try:
                # `railway run`은 로컬 프로세스에 환경변수만 주입하므로 RTT 근거가
                # 될 수 없다. 이 코드는 배포 컨테이너의 기동 경로에서만 의미가 있다.
                async with httpx.AsyncClient() as client:
                    result = await measure_rtt(
                        client,
                        supabase_url=settings.SUPABASE_URL,
                        publishable_key=settings.SUPABASE_PUBLISHABLE_KEY,
                    )
                logger.info(
                    "worker.rtt_measured",
                    cold_first_ms=result.cold_first_ms,
                    p50_ms=result.p50_ms,
                    p95_ms=result.p95_ms,
                    sample_count=result.sample_count,
                    warmup_count=result.warmup_count,
                    failures=result.failures,
                    git_sha=git_sha,
                )
            except Exception:
                logger.exception("worker.rtt_failed", git_sha=git_sha)
        # RTT 프로브는 기동 시 한 번만 돌고, 이후 프로세스 수명 전체는 큐 루프가
        # 차지한다. `stop`은 위에서 등록한 SIGTERM/SIGINT 핸들러가 세우며, 루프는
        # 그 신호를 받으면 새 claim을 멈추고 진행 중인 잡만 마무리한다.
        worker_id = resolve_worker_id()
        async with service_client(settings) as client:
            db = ServiceDb(client)
            # Probes are observations; schema mismatch is a startup contract.
            await assert_enums_match_db(db)
            await _run_queue_baseline_probe(
                db, settings=settings, worker_id=worker_id, git_sha=git_sha
            )
            async with asyncio.TaskGroup() as group:
                queue_task = group.create_task(
                    run_queue_loop(
                        db,
                        worker_id=worker_id,
                        stop=stop,
                        reap_enabled=settings.REAP_ENABLED,
                        reap_timeout_seconds=settings.REAP_TIMEOUT_SECONDS,
                    )
                )
                group.create_task(_serve_internal_listeners(settings, stop))
                if settings.LLM_STREAM_INTERNAL_TOKEN:
                    group.create_task(AskCostAccounting(settings).run(stop))
            processed = queue_task.result()
        # 루프가 잡마다 clear_job_context()를 부르므로 위 bootstrap 컨텍스트는
        # 이미 지워져 있다. 종료 로그가 맨몸이 되지 않도록 다시 세운다.
        bind_job_context(job_id="shutdown", workspace_id="shutdown")
        logger.info("worker.stopped", worker_id=worker_id, processed=processed)
    finally:
        # ⚠️ 큐 루프가 끝난 뒤에만 flush한다. 앞에 두면 `WORKER_GRACE_SECONDS`를 소모해 잡 반납이
        #    늦어진다. 호출이 3초로 제한되므로 기본 실행기의 종료를 막지 않는다.
        await asyncio.to_thread(flush_observability)
        clear_job_context()


if __name__ == "__main__":
    asyncio.run(main())
