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

# ⚠️ tiktoken은 인코딩을 처음 쓸 때 BPE 어휘 파일을 인터넷에서 받아 이 디렉터리에 캐시한다.
#    빌드 시점에 미리 받아 두지 않으면 워커가 **첫 컴파일 잡을 처리하는 도중** 아웃바운드로
#    나가게 되고, 컨테이너가 외부로 못 나가거나 느리면 그 잡이 원인 불명으로 지연되거나
#    실패한다 — 잡 실패는 재시도되지만 매 시도가 같은 곳에서 멈춘다.
#    설계 근거: 03-03-PLAN.md > D-P4 (청크 토큰은 cl100k_base로 센다), 위협 T-03-15.
ENV TIKTOKEN_CACHE_DIR=/app/.tiktoken
RUN /app/.venv/bin/python -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

FROM python:3.12-slim AS runtime

# 런타임 스테이지를 하나만 둬 두 서비스가 같은 이미지 다이제스트를 사용하게 한다 (D-01).
# ⚠️ TIKTOKEN_CACHE_DIR은 builder와 **같은 값**이어야 한다. 다르면 아래 COPY가 옮긴
#    BPE 파일을 런타임이 찾지 못해 캐시가 없는 것과 똑같이 동작한다 — 오류 없이
#    조용히 인터넷으로 나간다.
ENV PYTHONUNBUFFERED=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    TIKTOKEN_CACHE_DIR=/app/.tiktoken \
    PATH="/app/.venv/bin:$PATH"
WORKDIR /app

RUN useradd --create-home --uid 10001 appuser
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --from=builder --chown=appuser:appuser /app/.tiktoken /app/.tiktoken
USER appuser

# exec form으로 Python을 PID 1로 실행해 SIGTERM이 직접 전달되게 한다 (01-CONTEXT.md > D-03).
CMD ["python", "-m", "api"]
