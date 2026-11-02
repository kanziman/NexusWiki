#!/usr/bin/env bash
# 비교할 코드(<코드 루트>)의 API와 워커를 재생 전용 스택(546xx)에 붙여 포그라운드로 띄운다.
#
# ⚠️ `.env`의 SUPABASE_URL은 클라우드다. `.env`에서는 OPENROUTER_API_KEY와 LLM_MODEL만 읽는다.
# ⚠️ ASK_COST_POLICIES의 입력 상한은 일부러 넉넉하다. 낮으면 통제 전 코드의 큰 프롬프트가
#    422로 거부되어 전후 비교에서 빠지고, 통제 전 수치가 실제보다 좋게 나온다.
#
# ⚠️ 워커 내부 리스너는 8081 고정이다 (apps/worker/src/worker/__main__.py). 한 번에 한 벌만 띄운다.
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
LLM_MODEL="$(read_env LLM_MODEL)"
EMBEDDING_MODEL="$(read_env EMBEDDING_MODEL)"
EMBEDDING_PROVIDER="$(read_env EMBEDDING_PROVIDER)"
export OPENROUTER_API_KEY LLM_MODEL EMBEDDING_MODEL EMBEDDING_PROVIDER
export OPENAI_API_KEY="unused-openrouter-covers-embeddings"
export ENVIRONMENT=development LOG_LEVEL=INFO RTT_PROBE_ENABLED=false QUEUE_BASELINE_ENABLED=false
export QUERY_EMBEDDING_INTERNAL_TOKEN="ask-replay-embedding-token" LLM_STREAM_INTERNAL_TOKEN="ask-replay-llm-token"
export QUERY_EMBEDDING_INTERNAL_URL="http://127.0.0.1:${listener_port}" LLM_STREAM_INTERNAL_URL="http://127.0.0.1:${listener_port}"
export ASK_COST_POLICIES="{\"${LLM_MODEL}\":{\"reserve_micros\":200000,\"max_input_bytes\":1000000,\"max_tokens\":1500,\"version\":\"ask-replay-v1\"}}"
export GIT_SHA="$(git -C "${code_root}" rev-parse --short HEAD)$(git -C "${code_root}" diff --quiet HEAD || echo '+dirty')"
export RAILWAY_GIT_COMMIT_SHA="${GIT_SHA}"

cd "${code_root}"
uv run --package worker python -m worker >"${log_dir}/worker.log" 2>&1 &
worker_pid=$!
PORT="${api_port}" uv run --package api python -m api >"${log_dir}/api.log" 2>&1 &
api_pid=$!
trap 'kill "${worker_pid}" "${api_pid}" 2>/dev/null || true' EXIT INT TERM
# macOS 기본 bash 3.2에는 `wait -n`이 없다. 둘 중 하나가 죽으면 함께 내린다.
while kill -0 "${worker_pid}" 2>/dev/null && kill -0 "${api_pid}" 2>/dev/null; do
  sleep 2
done
