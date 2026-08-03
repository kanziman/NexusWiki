# 관련 태스크: P0-INIT-04
# 설계 근거: 01-CONTEXT.md > D-01 · D-02 · D-03 · D-04

FROM python:3.12-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
COPY packages/ packages/
COPY apps/api/ apps/api/
COPY apps/worker/ apps/worker/

# 비편집 설치가 아니면 결과가 소스 경로를 가리켜 venv만 복사한 런타임에서 import가 깨진다.
RUN uv sync --frozen --no-dev --no-editable --all-packages

FROM python:3.12-slim AS runtime

# 런타임 스테이지를 하나만 둬 두 서비스가 같은 이미지 다이제스트를 사용하게 한다 (D-01).
ENV PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

RUN useradd --create-home --uid 10001 appuser
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
USER appuser

# exec form으로 Python을 PID 1로 실행해 SIGTERM이 직접 전달되게 한다 (01-CONTEXT.md > D-03).
CMD ["python", "-m", "api"]
