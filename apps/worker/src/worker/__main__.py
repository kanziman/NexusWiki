"""SIGTERM을 직접 처리하는 worker 프로세스 진입점.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-03, D-13
"""

import asyncio
import os
import signal

import httpx

from nexuswiki_core.logging import (
    bind_job_context,
    clear_job_context,
    configure_logging,
    get_logger,
)
from worker.rtt import measure_rtt


async def main() -> None:
    configure_logging(
        environment=os.environ.get("ENVIRONMENT", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
    )
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop.set)
    loop.add_signal_handler(signal.SIGINT, stop.set)

    bind_job_context(job_id="bootstrap", workspace_id="bootstrap")
    logger = get_logger(__name__)
    git_sha = os.environ.get("RAILWAY_GIT_COMMIT_SHA", os.environ.get("GIT_SHA", "unknown"))
    logger.info(
        "worker.started",
        git_sha=git_sha,
    )
    try:
        probe_enabled = os.environ.get("RTT_PROBE_ENABLED", "true").lower() != "false"
        supabase_url = os.environ.get("SUPABASE_URL")
        publishable_key = os.environ.get("SUPABASE_PUBLISHABLE_KEY")
        if not probe_enabled:
            logger.info("worker.rtt_skipped", reason="disabled", git_sha=git_sha)
        elif not supabase_url or not publishable_key:
            logger.info("worker.rtt_skipped", reason="missing_configuration", git_sha=git_sha)
        else:
            try:
                # `railway run`은 로컬 프로세스에 환경변수만 주입하므로 RTT 근거가
                # 될 수 없다. 이 코드는 배포 컨테이너의 기동 경로에서만 의미가 있다.
                async with httpx.AsyncClient() as client:
                    result = await measure_rtt(
                        client,
                        supabase_url=supabase_url,
                        publishable_key=publishable_key,
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
        await stop.wait()
        logger.info("worker.stopped")
    finally:
        clear_job_context()


if __name__ == "__main__":
    asyncio.run(main())
