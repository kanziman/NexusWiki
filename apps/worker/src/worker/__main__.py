"""SIGTERM을 직접 처리하는 worker 프로세스 진입점.

관련 태스크: P0-INIT-02
설계 근거: 01-CONTEXT.md > D-03, D-13
"""

import asyncio
import os
import signal

from nexuswiki_core.logging import (
    bind_job_context,
    clear_job_context,
    configure_logging,
    get_logger,
)


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
    logger.info(
        "worker.started",
        git_sha=os.environ.get(
            "RAILWAY_GIT_COMMIT_SHA", os.environ.get("GIT_SHA", "unknown")
        ),
    )
    try:
        await stop.wait()
        logger.info("worker.stopped")
    finally:
        clear_job_context()


if __name__ == "__main__":
    asyncio.run(main())
