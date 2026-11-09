#!/usr/bin/env bash
# 비교할 코드(<코드 루트>)의 API와 워커를 재생 전용 스택(546xx)에 붙여 포그라운드로 띄운다.
#
# ⚠️ `.env`의 SUPABASE_URL은 클라우드다. `.env`에서는 OPENROUTER_API_KEY와 LLM_MODEL만 읽는다.
# ⚠️ ASK_COST_POLICIES의 입력 상한은 일부러 넉넉하다. 낮으면 통제 전 코드의 큰 프롬프트가
#    422로 거부되어 전후 비교에서 빠지고, 통제 전 수치가 실제보다 좋게 나온다.
#
# ⚠️ 워커 내부 리스너는 8081 고정이다 (apps/worker/src/worker/__main__.py). 한 번에 한 벌만 띄운다.
#
# 모델 비교 실험용 선택 옵션(cheap-model-evidence-ablation 설계 D2):
#   ASK_REPLAY_LLM_MODEL=<슬러그>  `.env`의 LLM_MODEL 대신 이 답변 모델로 워커를 띄운다.
#                                  비용 정책도 이 모델 이름으로 만든다. `.env`는 바꾸지 않는다.
#   ASK_REPLAY_WORKER_ONLY=1       API를 띄우지 않는다. 프로세스 안에서 Ask를 돌리는 실험 전용이다.
#   ASK_REPLAY_RESERVE_MICROS=<정수> Ask 호출마다 미리 잡는 예약액(기본 200000). 월 한도를 실험
#                                  상한으로 낮춘 워크스페이스에서 예약이 한도를 먼저 막지 않게 줄인다.
#
# 사용법: scripts/ask_replay_serve.sh <코드 루트> <로그 디렉터리> [API 포트]
set -euo pipefail

code_root="$(cd "${1:?코드 루트}" && pwd)"
log_dir="${2:?로그 디렉터리}"
api_port="${3:-8031}"
listener_port=8081
# worktree에서 돌릴 수 있게 `.env` 위치를 지정할 수 있다.
env_file="${ASK_REPLAY_ENV_FILE:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env}"

read_env() { grep -m1 "^$1=" "${env_file}" | cut -d= -f2-; }

mkdir -p "${log_dir}"
export SUPABASE_URL="http://127.0.0.1:54621"
export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:54622/postgres"
export SUPABASE_PUBLISHABLE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
export SUPABASE_SECRET_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
OPENROUTER_API_KEY="$(read_env OPENROUTER_API_KEY)"
LLM_MODEL="${ASK_REPLAY_LLM_MODEL:-$(read_env LLM_MODEL)}"
EMBEDDING_MODEL="$(read_env EMBEDDING_MODEL)"
EMBEDDING_PROVIDER="$(read_env EMBEDDING_PROVIDER)"
export OPENROUTER_API_KEY LLM_MODEL EMBEDDING_MODEL EMBEDDING_PROVIDER
export OPENAI_API_KEY="unused-openrouter-covers-embeddings"
export ENVIRONMENT=development LOG_LEVEL=INFO RTT_PROBE_ENABLED=false QUEUE_BASELINE_ENABLED=false
export QUERY_EMBEDDING_INTERNAL_TOKEN="ask-replay-embedding-token" LLM_STREAM_INTERNAL_TOKEN="ask-replay-llm-token"
export QUERY_EMBEDDING_INTERNAL_URL="http://127.0.0.1:${listener_port}" LLM_STREAM_INTERNAL_URL="http://127.0.0.1:${listener_port}"
export QUERY_EMBEDDING_TIMEOUT_SECONDS=20
export QUERY_EMBEDDING_RATE_CAPACITY=500 QUERY_EMBEDDING_RATE_REFILL_TOKENS_PER_SECOND=10
export LLM_STREAM_RATE_CAPACITY=500 LLM_STREAM_RATE_REFILL_TOKENS_PER_SECOND=10
reserve_micros="${ASK_REPLAY_RESERVE_MICROS:-200000}"
export ASK_COST_POLICIES="{\"${LLM_MODEL}\":{\"reserve_micros\":${reserve_micros},\"max_input_bytes\":1000000,\"max_tokens\":1500,\"version\":\"ask-replay-v1\"}}"
export GIT_SHA="$(git -C "${code_root}" rev-parse --short HEAD)$(git -C "${code_root}" diff --quiet HEAD || echo '+dirty')"
export RAILWAY_GIT_COMMIT_SHA="${GIT_SHA}"

cd "${code_root}"
# 키는 제외하고 실제 API·워커 설정만 평가 재현 조건으로 남긴다.
uv run --all-packages python - "${log_dir}/evaluation-runtime.json" <<'PY'
import json
import sys
from pathlib import Path
from api.settings import ApiSettings
from worker.settings import WorkerSettings
sys.path.insert(0, str(Path.cwd() / "scripts"))
from evidence_research_eval import execution_sha256

api, worker = ApiSettings(), WorkerSettings()
runtime = {
    "execution_sha256": execution_sha256(),
    "model": worker.LLM_MODEL,
    "model_settings": worker.ASK_COST_POLICIES.get(worker.LLM_MODEL),
    "context_tokens": api.ASK_MAX_CONTEXT_TOKENS,
    "quality_mode": api.AI_CONTROL_QUALITY_MODE,
    "embedding_model": worker.EMBEDDING_MODEL,
    "embedding_provider": worker.EMBEDDING_PROVIDER,
    "concurrency": worker.LLM_STREAM_MAX_CONCURRENCY,
}
Path(sys.argv[1]).write_text(json.dumps(runtime, sort_keys=True), encoding="utf-8")
PY
uv run --package worker python -m worker >"${log_dir}/worker.log" 2>&1 &
worker_pid=$!
if [[ "${ASK_REPLAY_WORKER_ONLY:-}" == "1" ]]; then
  trap 'kill "${worker_pid}" 2>/dev/null || true' EXIT INT TERM
  wait "${worker_pid}"
  exit $?
fi
PORT="${api_port}" uv run --package api python -m api >"${log_dir}/api.log" 2>&1 &
api_pid=$!
research_api_pid=""
if [[ -n "${ASK_REPLAY_RESEARCH_API_PORT:-}" ]]; then
  # 같은 워커와 데이터에서 모드만 다른 두 API를 준비한다. 평가 요청은 직렬 실행한다.
  ASK_EVIDENCE_RESEARCH_ENABLED=true PORT="${ASK_REPLAY_RESEARCH_API_PORT}" \
    uv run --package api python -m api >"${log_dir}/research-api.log" 2>&1 &
  research_api_pid=$!
fi
trap 'kill "${worker_pid}" "${api_pid}" ${research_api_pid:+"${research_api_pid}"} 2>/dev/null || true' EXIT INT TERM
# macOS 기본 bash 3.2에는 `wait -n`이 없다. 둘 중 하나가 죽으면 함께 내린다.
while kill -0 "${worker_pid}" 2>/dev/null && kill -0 "${api_pid}" 2>/dev/null; do
  sleep 2
done
