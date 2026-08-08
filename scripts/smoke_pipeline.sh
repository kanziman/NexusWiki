#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# 텍스트 한 건이 HTTP 202에서 시작해 wiki_pages 행으로 끝나는 end-to-end 스모크.
#
# 관련 태스크: P2-ING-01 · P2-ING-02 · P2-LLM-01 (ING-01, ING-02, ING-05, COMP-01)
# 설계 근거: 03-04-PLAN.md (이 페이즈의 tracer)
#
#   POST /workspaces/{id}/sources/text ─202─> enqueue_source_job
#        └─> parse ──complete_job_and_chain──> compile ──> wiki_pages
#
# ⚠️ 실제 OpenRouter를 호출한다 — 돈이 든다. 본문을 짧게 유지할 것.
#
# ⚠️ 모든 작업을 **처분 가능한 워크스페이스에 가둔다.** `0007` 섹션 8의 최소권한
#    매트릭스는 `jobs`에 어느 롤에도 DELETE를 주지 않는다(잡 이력이 곧 감사 기록이다).
#    따라서 이 스크립트가 만든 잡을 지우는 유일한 경로가 워크스페이스 삭제의 cascade이며,
#    그것이 여기서 사용자와 워크스페이스를 매번 새로 만들고 trap으로 지우는 이유다.
#    "기존 워크스페이스에서 한 번만 돌려보자"로 바꾸면 잡 행이 영구히 쌓인다.
#
# ⚠️ 로컬 스택 전용이다. `.env`의 SUPABASE_URL은 **클라우드**를 가리키므로 여기서 읽지
#    않는다 — 읽으면 이 스크립트가 운영 프로젝트에 사용자와 워크스페이스를 만들고 지운다.
#    `.env`에서 가져오는 것은 OPENROUTER_API_KEY와 LLM_MODEL뿐이다.
# =============================================================================

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# -- 로컬 스택 상수 (apps/api/tests/conftest.py:33-45와 같은 값) ----------------
# Supabase CLI가 모든 로컬 스택에 동일하게 발급하는 공개 데모 키다. 포트 54421은
# supabase/config.toml의 [api] port이며, 같은 머신의 다른 프로젝트가 543xx를 점유하므로
# 튜토리얼 기본값 54321이 아니다.
LOCAL_URL="http://127.0.0.1:54421"
LOCAL_DB_URL="postgresql://postgres:postgres@127.0.0.1:54422/postgres"
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"

API_PORT="${SMOKE_API_PORT:-8021}"
API_URL="http://127.0.0.1:${API_PORT}"
JOB_TIMEOUT_SECONDS="${SMOKE_JOB_TIMEOUT:-300}"

case "$LOCAL_URL" in
  http://127.0.0.1:*|http://localhost:*) ;;
  *) echo "smoke_pipeline: 루프백이 아닌 주소를 가리키고 있다 — 중단" >&2; exit 2 ;;
esac

# -- OPENROUTER_API_KEY / LLM_MODEL 만 .env에서 가져온다 ------------------------
if [[ -z "${OPENROUTER_API_KEY:-}" && -f .env ]]; then
  OPENROUTER_API_KEY="$(grep -m1 '^OPENROUTER_API_KEY=' .env | cut -d= -f2-)"
fi
if [[ -z "${LLM_MODEL:-}" && -f .env ]]; then
  LLM_MODEL="$(grep -m1 '^LLM_MODEL=' .env | cut -d= -f2-)"
fi
if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
  echo "smoke_pipeline: OPENROUTER_API_KEY가 없다 (.env 또는 환경변수)" >&2
  exit 2
fi
: "${LLM_MODEL:?smoke_pipeline: LLM_MODEL이 없다}"

tmp_dir="$(mktemp -d)"
api_log="${tmp_dir}/api.log"
worker_log="${tmp_dir}/worker.log"
api_pid=""
worker_pid=""
user_id=""
workspace_id=""
access_token=""

psql_local() {
  docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -tAc "$1"
}

cleanup() {
  local code=$?
  [[ -z "${worker_pid}" ]] || kill "${worker_pid}" 2>/dev/null || true
  [[ -z "${api_pid}" ]] || kill "${api_pid}" 2>/dev/null || true
  # ⚠️ 삭제 순서가 중요하다. `workspaces.owner_id`는 `on delete restrict`라 워크스페이스가
  #    남아 있으면 사용자 삭제가 실패한다 (conftest.py:159-172와 같은 순서).
  if [[ -n "${workspace_id}" && -n "${access_token}" ]]; then
    curl -s -o /dev/null -X DELETE "${LOCAL_URL}/rest/v1/workspaces?id=eq.${workspace_id}" \
      -H "apikey: ${ANON_KEY}" -H "Authorization: Bearer ${access_token}" || true
  fi
  if [[ -n "${user_id}" ]]; then
    curl -s -o /dev/null -X DELETE "${LOCAL_URL}/auth/v1/admin/users/${user_id}" \
      -H "apikey: ${SERVICE_KEY}" -H "Authorization: Bearer ${SERVICE_KEY}" || true
  fi
  if (( code != 0 )); then
    echo "--- api.log ---" >&2; tail -40 "${api_log}" 2>/dev/null >&2 || true
    echo "--- worker.log ---" >&2; tail -60 "${worker_log}" 2>/dev/null >&2 || true
  elif [[ -n "${SMOKE_VERBOSE:-}" ]]; then
    # 성공한 실행에서도 워커 로그를 보고 싶을 때 — `response_format` 능력 탐지가
    # 실제로 통과했는지 폴백했는지는 로그에만 남는다 (docs/ops/openrouter-contract-record.md).
    echo "--- worker.log ---"; cat "${worker_log}" 2>/dev/null || true
  fi
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

jqr() { python3 -c "import json,sys;d=json.load(sys.stdin);print(d$1)"; }

# -- 1. 테스트 사용자와 처분 가능한 워크스페이스 --------------------------------
tag="$(python3 -c 'import uuid;print(uuid.uuid4().hex[:12])')"
email="smoke-${tag}@example.test"
credential="pw-$(python3 -c 'import uuid;print(uuid.uuid4().hex)')"

user_id="$(curl -sf -X POST "${LOCAL_URL}/auth/v1/admin/users" \
  -H "apikey: ${SERVICE_KEY}" -H "Authorization: Bearer ${SERVICE_KEY}" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${email}\",\"password\":\"${credential}\",\"email_confirm\":true}" | jqr "['id']")"

access_token="$(curl -sf -X POST "${LOCAL_URL}/auth/v1/token?grant_type=password" \
  -H "apikey: ${ANON_KEY}" -H 'Content-Type: application/json' \
  -d "{\"email\":\"${email}\",\"password\":\"${credential}\"}" | jqr "['access_token']")"

# 워크스페이스는 요청자 JWT로 만든다 — service_role은 workspaces에 SELECT만 갖는다.
workspace_id="$(curl -sf -X POST "${LOCAL_URL}/rest/v1/workspaces" \
  -H "apikey: ${ANON_KEY}" -H "Authorization: Bearer ${access_token}" \
  -H 'Content-Type: application/json' -H 'Prefer: return=representation' \
  -d "{\"name\":\"smoke-${tag}\",\"owner_id\":\"${user_id}\"}" | jqr "[0]['id']")"

echo "smoke_pipeline: workspace=${workspace_id}"

# -- 2. api와 worker를 로컬 스택에 붙여 띄운다 ---------------------------------
export SUPABASE_URL="${LOCAL_URL}"
export SUPABASE_PUBLISHABLE_KEY="${ANON_KEY}"
export SUPABASE_SECRET_KEY="${SERVICE_KEY}"
export DATABASE_URL="${LOCAL_DB_URL}"
export OPENROUTER_API_KEY LLM_MODEL
# 03-08이 제거할 때까지 WorkerSettings가 요구한다. 소비자는 없다 (03-CONTEXT.md > D-04).
export OPENAI_API_KEY="${OPENAI_API_KEY:-unused-openrouter-covers-embeddings}"
export ENVIRONMENT=development
export LOG_LEVEL=INFO
# 기동 시 55회 왕복하는 RTT 프로브는 스모크에 무의미하다.
export RTT_PROBE_ENABLED=false
export QUEUE_BASELINE_ENABLED=false

PORT="${API_PORT}" uv run --package api python -m api >"${api_log}" 2>&1 &
api_pid=$!

api_ready=false
for _ in {1..200}; do
  if [[ "$(curl -fsS -o /dev/null -w '%{http_code}' "${API_URL}/health" 2>/dev/null || true)" == "200" ]]; then
    api_ready=true; break
  fi
  sleep 0.1
done
[[ "${api_ready}" == "true" ]] || { echo "smoke_pipeline: api가 뜨지 않았다" >&2; exit 1; }

uv run --package worker python -m worker >"${worker_log}" 2>&1 &
worker_pid=$!

# -- 3. 첫 POST — 202 + job_id · raw_source_id ---------------------------------
# 짧은 한국어 본문 하나. `[[...]]` 링크가 들어 있어 컴파일 프롬프트의 위키 링크 규약도
# 함께 지난다. ⚠️ 길게 쓰면 그만큼 OpenRouter 청구서가 커진다.
body_file="${tmp_dir}/body.json"
python3 - "${body_file}" <<'PY'
import json, sys
text = (
    "NexusWiki는 원시 소스를 LLM으로 컴파일해 상호 링크된 위키를 만드는 도구다.\n\n"
    "수집된 소스는 먼저 청크로 나뉘어 [[source-chunks]]에 저장되고, 그 다음 컴파일러가 "
    "위키 페이지를 만든다. 답변은 원문과 위키 양쪽을 함께 인용한다."
)
json.dump({"title": "NexusWiki 파이프라인 개요", "text": text, "source_type": "text"},
          open(sys.argv[1], "w"), ensure_ascii=False)
PY

first="${tmp_dir}/first.json"
status_code="$(curl -s -o "${first}" -w '%{http_code}' \
  -X POST "${API_URL}/workspaces/${workspace_id}/sources/text" \
  -H "Authorization: Bearer ${access_token}" -H 'Content-Type: application/json' \
  --data-binary "@${body_file}")"

[[ "${status_code}" == "202" ]] || {
  echo "smoke_pipeline: 첫 POST가 202가 아니다 (${status_code}): $(cat "${first}")" >&2; exit 1; }
job_id="$(jqr "['job_id']" <"${first}")"
raw_source_id="$(jqr "['raw_source_id']" <"${first}")"
[[ -n "${job_id}" && -n "${raw_source_id}" ]] || {
  echo "smoke_pipeline: 응답에 job_id/raw_source_id가 없다" >&2; exit 1; }
echo "smoke_pipeline: 202 job=${job_id} raw_source=${raw_source_id}"

# -- 4. 같은 본문 재투입 — 409 already_ingested --------------------------------
second="${tmp_dir}/second.json"
status_code="$(curl -s -o "${second}" -w '%{http_code}' \
  -X POST "${API_URL}/workspaces/${workspace_id}/sources/text" \
  -H "Authorization: Bearer ${access_token}" -H 'Content-Type: application/json' \
  --data-binary "@${body_file}")"

[[ "${status_code}" == "409" ]] || {
  echo "smoke_pipeline: 재투입이 409가 아니다 (${status_code}): $(cat "${second}")" >&2; exit 1; }
[[ "$(jqr "['detail']" <"${second}")" == "already_ingested" ]] || {
  echo "smoke_pipeline: 409 본문 detail이 already_ingested가 아니다" >&2; exit 1; }
echo "smoke_pipeline: 409 already_ingested"

# -- 5. parse → compile 이 succeeded 가 될 때까지 -------------------------------
deadline=$(( $(date +%s) + JOB_TIMEOUT_SECONDS ))
while :; do
  states="$(psql_local "select type || '=' || status from public.jobs where workspace_id = '${workspace_id}' order by created_at;" | tr '\n' ' ')"
  if grep -qE '=(dead|failed|canceled)' <<<"${states}"; then
    echo "smoke_pipeline: 잡이 실패했다 — ${states}" >&2
    psql_local "select type, status, attempts, coalesce(last_error,'') from public.jobs where workspace_id = '${workspace_id}';" >&2
    exit 1
  fi
  if grep -q 'parse=succeeded' <<<"${states}" && grep -q 'compile=succeeded' <<<"${states}"; then
    echo "smoke_pipeline: 잡 체인 완료 — ${states}"
    break
  fi
  if (( $(date +%s) > deadline )); then
    echo "smoke_pipeline: ${JOB_TIMEOUT_SECONDS}초 안에 체인이 끝나지 않았다 — ${states}" >&2
    exit 1
  fi
  sleep 2
done

# -- 6. 행 수 확인 --------------------------------------------------------------
chunk_count="$(psql_local "select count(*) from public.source_chunks where workspace_id = '${workspace_id}';")"
page_count="$(psql_local "select count(*) from public.wiki_pages where workspace_id = '${workspace_id}';")"
usage_count="$(psql_local "select count(*) from public.usage_events where workspace_id = '${workspace_id}';")"
noninteger_cost="$(psql_local "select count(*) from public.usage_events where workspace_id = '${workspace_id}' and cost_micros is null;")"

echo "smoke_pipeline: chunks=${chunk_count} pages=${page_count} usage_events=${usage_count}"
# 사용량 실측을 그대로 인쇄한다 — 이 줄이 "LLM 호출이 얼마였나"에 답하는 유일한 관측이다.
psql_local "select 'usage: ' || provider || ' ' || model || ' prompt=' || prompt_tokens || ' completion=' || completion_tokens || ' cost_micros=' || cost_micros from public.usage_events where workspace_id = '${workspace_id}';"
(( chunk_count > 0 )) || { echo "smoke_pipeline: source_chunks가 0행이다" >&2; exit 1; }
(( usage_count > 0 )) || { echo "smoke_pipeline: usage_events가 0행이다 — LLM 호출이 기록되지 않았다" >&2; exit 1; }
(( noninteger_cost == 0 )) || { echo "smoke_pipeline: cost_micros가 null인 행이 있다" >&2; exit 1; }

# 멱등성: 같은 체인을 한 번 더 돌려도 행 수가 늘지 않는다 (at-least-once).
psql_local "insert into public.jobs (workspace_id, type, payload) values ('${workspace_id}', 'parse', jsonb_build_object('target_id','${raw_source_id}','raw_source_id','${raw_source_id}'));" >/dev/null
deadline=$(( $(date +%s) + JOB_TIMEOUT_SECONDS ))
while :; do
  pending="$(psql_local "select count(*) from public.jobs where workspace_id = '${workspace_id}' and status in ('queued','running');")"
  (( pending == 0 )) && break
  if (( $(date +%s) > deadline )); then
    echo "smoke_pipeline: 2회차 체인이 끝나지 않았다" >&2; exit 1
  fi
  sleep 2
done
chunk_count_2="$(psql_local "select count(*) from public.source_chunks where workspace_id = '${workspace_id}';")"
page_count_2="$(psql_local "select count(*) from public.wiki_pages where workspace_id = '${workspace_id}';")"
(( chunk_count_2 == chunk_count )) || {
  echo "smoke_pipeline: 재처리로 청크가 늘었다 (${chunk_count} → ${chunk_count_2})" >&2; exit 1; }
(( page_count_2 == page_count )) || {
  echo "smoke_pipeline: 재처리로 페이지가 늘었다 (${page_count} → ${page_count_2})" >&2; exit 1; }
echo "smoke_pipeline: 멱등 확인 — chunks=${chunk_count_2} pages=${page_count_2}"

echo "smoke_pipeline: ok"
