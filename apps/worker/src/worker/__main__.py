"""SIGTERM을 직접 처리하는 worker 프로세스 진입점.

관련 태스크: P0-INIT-02, P2-BE-01, P2-JOB-01
설계 근거: 01-CONTEXT.md > D-03, D-13 · 02-CONTEXT.md > D-07, D-10, D-18
"""

import asyncio
import signal

import httpx
import uvicorn

from nexuswiki_core.deployment import resolve_git_sha
from nexuswiki_core.logging import (
    bind_job_context,
    clear_job_context,
    configure_logging,
    get_logger,
)
from worker.db.service import ServiceDb, service_client
from worker.embedding import embed_texts
from worker.llm import openrouter_client
from worker.query_embedding import QueryEmbeddingService, create_query_embedding_app
from worker.queue import resolve_worker_id, run_queue_loop
from worker.queue_baseline import measure_queue_roundtrip
from worker.rtt import measure_rtt
from worker.schema_guard import assert_enums_match_db
from worker.settings import WorkerSettings


async def _embed_query(settings: WorkerSettings, text: str) -> list[float]:
    async with openrouter_client(settings) as client:
        result = await embed_texts(client, settings=settings, texts=[text])
    return result.vectors[0]


async def _serve_query_embeddings(settings: WorkerSettings, stop: asyncio.Event) -> None:
    """Run the private listener until the queue process receives its stop signal."""
    if not settings.QUERY_EMBEDDING_INTERNAL_TOKEN:
        # No listener is safer than an unauthenticated listener during local setup.
        return
    service = QueryEmbeddingService(
        lambda text: _embed_query(settings, text),
        internal_token=settings.QUERY_EMBEDDING_INTERNAL_TOKEN,
        max_text_chars=settings.QUERY_EMBEDDING_MAX_TEXT_CHARS,
        timeout_seconds=settings.QUERY_EMBEDDING_TIMEOUT_SECONDS,
        max_concurrency=settings.QUERY_EMBEDDING_MAX_CONCURRENCY,
        max_requests=settings.QUERY_EMBEDDING_MAX_REQUESTS,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            create_query_embedding_app(service), host="0.0.0.0", port=8081, log_level="warning"
        )
    )
    server_task = asyncio.create_task(server.serve())
    await stop.wait()
    server.should_exit = True
    await server_task


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
                group.create_task(_serve_query_embeddings(settings, stop))
            processed = queue_task.result()
        # 루프가 잡마다 clear_job_context()를 부르므로 위 bootstrap 컨텍스트는
        # 이미 지워져 있다. 종료 로그가 맨몸이 되지 않도록 다시 세운다.
        bind_job_context(job_id="shutdown", workspace_id="shutdown")
        logger.info("worker.stopped", worker_id=worker_id, processed=processed)
    finally:
        clear_job_context()


if __name__ == "__main__":
    asyncio.run(main())
