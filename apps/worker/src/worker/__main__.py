"""SIGTERM을 직접 처리하는 worker 프로세스 진입점.

관련 태스크: P0-INIT-02, P2-BE-01, P2-JOB-01
설계 근거: 01-CONTEXT.md > D-03, D-13 · 02-CONTEXT.md > D-07, D-10, D-18
"""

import asyncio
import signal

import httpx

from nexuswiki_core.deployment import resolve_git_sha
from nexuswiki_core.logging import (
    bind_job_context,
    clear_job_context,
    configure_logging,
    get_logger,
)
from worker.db.service import ServiceDb, service_client
from worker.queue import resolve_worker_id, run_queue_loop
from worker.rtt import measure_rtt
from worker.settings import WorkerSettings


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
            processed = await run_queue_loop(
                ServiceDb(client),
                worker_id=worker_id,
                stop=stop,
            )
        # 루프가 잡마다 clear_job_context()를 부르므로 위 bootstrap 컨텍스트는
        # 이미 지워져 있다. 종료 로그가 맨몸이 되지 않도록 다시 세운다.
        bind_job_context(job_id="shutdown", workspace_id="shutdown")
        logger.info("worker.stopped", worker_id=worker_id, processed=processed)
    finally:
        clear_job_context()


if __name__ == "__main__":
    asyncio.run(main())
