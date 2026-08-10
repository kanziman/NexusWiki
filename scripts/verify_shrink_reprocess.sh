#!/usr/bin/env bash
set -euo pipefail

# Verify COMP-07 against the local, disposable stack.  `jobs` has no DELETE
# grant; deleting this workspace is therefore the only supported cleanup path
# for the job history created by this probe.
#
# This invokes OpenRouter and costs money.  EMBEDDING_MODEL and
# EMBEDDING_PROVIDER are deliberately required from the caller rather than
# read from .env: the observed provider/model must be an explicit choice.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

LOCAL_URL="http://127.0.0.1:54421"
LOCAL_DB_URL="postgresql://postgres:postgres@127.0.0.1:54422/postgres"
ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImV4cCI6MTk4MzgxMjk5Nn0.EGIM96RAZx35lJzdJsyH-qQwv8Hdp7fsn3W0YpN81IU"
API_PORT="${SHRINK_SMOKE_API_PORT:-8022}"
API_URL="http://127.0.0.1:${API_PORT}"
JOB_TIMEOUT_SECONDS="${SHRINK_SMOKE_JOB_TIMEOUT:-420}"

[[ "$LOCAL_URL" == http://127.0.0.1:* ]] || { echo "shrink_reprocess: non-loopback target" >&2; exit 2; }
if [[ -z "${OPENROUTER_API_KEY:-}" && -f .env ]]; then OPENROUTER_API_KEY="$(grep -m1 '^OPENROUTER_API_KEY=' .env | cut -d= -f2-)"; fi
if [[ -z "${LLM_MODEL:-}" && -f .env ]]; then LLM_MODEL="$(grep -m1 '^LLM_MODEL=' .env | cut -d= -f2-)"; fi
: "${OPENROUTER_API_KEY:?shrink_reprocess: OPENROUTER_API_KEY is required}"
: "${LLM_MODEL:?shrink_reprocess: LLM_MODEL is required}"
: "${EMBEDDING_MODEL:?shrink_reprocess: EMBEDDING_MODEL is required}"
: "${EMBEDDING_PROVIDER:?shrink_reprocess: EMBEDDING_PROVIDER is required}"

tmp_dir="$(mktemp -d)"; api_pid=""; worker_pid=""; user_id=""; workspace_id=""; access_token=""
psql_local() { docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -tAc "$1"; }
jqr() { python3 -c "import json,sys; print(json.load(sys.stdin)$1)"; }
cleanup() {
  local code=$?
  [[ -z "$worker_pid" ]] || kill "$worker_pid" 2>/dev/null || true
  [[ -z "$api_pid" ]] || kill "$api_pid" 2>/dev/null || true
  if [[ -n "$workspace_id" && -n "$access_token" ]]; then
    curl -sf -o /dev/null -X DELETE "${LOCAL_URL}/rest/v1/workspaces?id=eq.${workspace_id}" -H "apikey: ${ANON_KEY}" -H "Authorization: Bearer ${access_token}" || true
    local remaining
    remaining="$(psql_local "select count(*) from public.jobs where workspace_id = '${workspace_id}';")"
    (( remaining == 0 )) || { echo "shrink_reprocess: cleanup left jobs=${remaining}" >&2; code=1; }
    workspace_id=""
  fi
  [[ -z "$user_id" ]] || curl -s -o /dev/null -X DELETE "${LOCAL_URL}/auth/v1/admin/users/${user_id}" -H "apikey: ${SERVICE_KEY}" -H "Authorization: Bearer ${SERVICE_KEY}" || true
  if (( code != 0 )); then tail -60 "$tmp_dir/worker.log" >&2 2>/dev/null || true; fi
  rm -rf "$tmp_dir"
  return "$code"
}
trap cleanup EXIT

tag="$(python3 -c 'import uuid; print(uuid.uuid4().hex[:12])')"
email="shrink-${tag}@example.test"; credential="pw-$(python3 -c 'import uuid; print(uuid.uuid4().hex)')"
user_id="$(curl -sf -X POST "${LOCAL_URL}/auth/v1/admin/users" -H "apikey: ${SERVICE_KEY}" -H "Authorization: Bearer ${SERVICE_KEY}" -H 'Content-Type: application/json' -d "{\"email\":\"${email}\",\"password\":\"${credential}\",\"email_confirm\":true}" | jqr "['id']")"
access_token="$(curl -sf -X POST "${LOCAL_URL}/auth/v1/token?grant_type=password" -H "apikey: ${ANON_KEY}" -H 'Content-Type: application/json' -d "{\"email\":\"${email}\",\"password\":\"${credential}\"}" | jqr "['access_token']")"
workspace_id="$(curl -sf -X POST "${LOCAL_URL}/rest/v1/workspaces" -H "apikey: ${ANON_KEY}" -H "Authorization: Bearer ${access_token}" -H 'Content-Type: application/json' -H 'Prefer: return=representation' -d "{\"name\":\"shrink-${tag}\",\"owner_id\":\"${user_id}\"}" | jqr "[0]['id']")"

export SUPABASE_URL="$LOCAL_URL" SUPABASE_PUBLISHABLE_KEY="$ANON_KEY" SUPABASE_SECRET_KEY="$SERVICE_KEY" DATABASE_URL="$LOCAL_DB_URL"
export OPENROUTER_API_KEY LLM_MODEL EMBEDDING_MODEL EMBEDDING_PROVIDER ENVIRONMENT=development LOG_LEVEL=INFO RTT_PROBE_ENABLED=false QUEUE_BASELINE_ENABLED=false
PORT="$API_PORT" uv run --package api python -m api >"$tmp_dir/api.log" 2>&1 & api_pid=$!
for _ in {1..200}; do curl -fsS -o /dev/null "$API_URL/health" 2>/dev/null && break; sleep 0.1; done
curl -fsS -o /dev/null "$API_URL/health" || { echo "shrink_reprocess: api did not start" >&2; exit 1; }
uv run --package worker python -m worker >"$tmp_dir/worker.log" 2>&1 & worker_pid=$!

long_body="$tmp_dir/long.json"
python3 - "$long_body" <<'PY'
import json, sys
paragraph = "NexusWiki의 재처리 검증은 원문 청크와 위키 임베딩의 잔여 행을 함께 검사한다. 각 단락은 출처, 계약, 관측값, 그리고 링크의 의미를 설명한다. "
# Keep this above one chunk but below the provider's small-batch smoke limit.
text = "\n\n".join(f"{i}. {paragraph * 8}" for i in range(1, 4))
json.dump({"title": "축소 재처리 검증", "text": text, "source_type": "text"}, open(sys.argv[1], "w"), ensure_ascii=False)
PY
first="$tmp_dir/first.json"
[[ "$(curl -s -o "$first" -w '%{http_code}' -X POST "$API_URL/workspaces/$workspace_id/sources/text" -H "Authorization: Bearer $access_token" -H 'Content-Type: application/json' --data-binary "@$long_body")" == 202 ]] || { cat "$first" >&2; exit 1; }
raw_source_id="$(jqr "['raw_source_id']" <"$first")"

wait_chain() {
  local deadline=$(( $(date +%s) + JOB_TIMEOUT_SECONDS )) states
  while :; do
    states="$(psql_local "select type || '=' || status from public.jobs where workspace_id = '${workspace_id}' order by created_at;" | tr '\n' ' ')"
    grep -qE '=(dead|failed|canceled)' <<<"$states" && { echo "shrink_reprocess: failed chain ${states}" >&2; exit 1; }
    [[ "$(psql_local "select count(*) from public.jobs where workspace_id = '${workspace_id}' and status in ('queued','running');")" == 0 ]] && return
    (( $(date +%s) < deadline )) || { echo "shrink_reprocess: timeout ${states}" >&2; exit 1; }
    sleep 2
  done
}
wait_chain
before_chunks="$(psql_local "select count(*) from public.source_chunks where raw_source_id = '${raw_source_id}';")"
before_wiki="$(psql_local "select count(*) from public.wiki_embeddings where workspace_id = '${workspace_id}';")"
echo "shrink_reprocess: before source_chunks=${before_chunks} wiki_embeddings=${before_wiki}"
(( before_chunks > 1 )) || { echo "shrink_reprocess: long source did not make multiple chunks" >&2; exit 1; }

# Do not change content_hash: doing so would test duplicate ingestion rather
# than the existing source's parse→compile reprocessing path.
short_content="NexusWiki 축소 재처리 검증 원문이다. 청크와 임베딩의 고아 행이 없어야 한다."
psql_local "update public.raw_sources set content = '${short_content}' where id = '${raw_source_id}';" >/dev/null
curl -sf -o /dev/null -X POST "${LOCAL_URL}/rest/v1/rpc/enqueue_source_job" \
  -H "apikey: ${ANON_KEY}" -H "Authorization: Bearer ${access_token}" \
  -H 'Content-Type: application/json' \
  -d "{\"p_workspace_id\":\"${workspace_id}\",\"p_raw_source_id\":\"${raw_source_id}\"}"
wait_chain
after_chunks="$(psql_local "select count(*) from public.source_chunks where raw_source_id = '${raw_source_id}';")"
after_wiki="$(psql_local "select count(*) from public.wiki_embeddings where workspace_id = '${workspace_id}';")"
echo "shrink_reprocess: after source_chunks=${after_chunks} wiki_embeddings=${after_wiki}"
(( after_chunks < before_chunks )) || { echo "shrink_reprocess: source_chunks did not shrink" >&2; exit 1; }
for query in \
  "select count(*) = coalesce(max(chunk_index) + 1, 0) from public.source_chunks where raw_source_id = '${raw_source_id}'" \
  "select coalesce(bool_and(row_count = max_index + 1), true) from (select wiki_id, count(*) as row_count, max(chunk_index) as max_index from public.wiki_embeddings where workspace_id = '${workspace_id}' group by wiki_id) indexed_wikis"; do
  [[ "$(psql_local "$query")" == t ]] || { echo "shrink_reprocess: non-contiguous chunk_index" >&2; exit 1; }
done

# Queue terminal RPCs clear `locked_at`, so the durable row cannot recover the
# claim→terminal interval after success.  The worker's monotonic-duration log
# is the authoritative observation for this run (and avoids wall-clock skew).
python3 - "$tmp_dir/worker.log" <<'PY'
import re, sys
text = re.sub(r"\x1b\[[0-9;]*m", "", open(sys.argv[1]).read())
samples = {}
for line in text.splitlines():
    if "worker.job_completed" not in line:
        continue
    duration = re.search(r"duration_ms=([0-9.]+)", line)
    job_type = re.search(r"job_type=([a-z_]+)", line)
    if duration and job_type:
        samples.setdefault(job_type.group(1), []).append(float(duration.group(1)))
for job_type, values in sorted(samples.items()):
    print(f"handler_duration: {job_type} samples={len(values)} max_ms={max(values):.3f}")
compile_values = samples.get("compile", [])
if not compile_values:
    raise SystemExit("shrink_reprocess: no compile duration was logged")
print(
    "compile_duration_observation:"
    f" sample_count={len(compile_values)}"
    f" max_seconds={int(__import__('math').ceil(max(compile_values) / 1000))}"
)
PY
psql_local "select 'usage: ' || provider || ' ' || model || ' cost_micros=' || cost_micros from public.usage_events where workspace_id = '${workspace_id}';"
cleanup; trap - EXIT
echo "shrink_reprocess: ok"
