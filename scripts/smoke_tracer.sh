#!/usr/bin/env bash
set -euo pipefail

image=""
if [[ "${1:-}" == "--image" ]]; then
  image="${2:?--image requires a tag}"
fi

tmp_dir="$(mktemp -d)"
api_log="${tmp_dir}/api.log"
worker_log="${tmp_dir}/worker.log"
api_pid=""
worker_pid=""

cleanup() {
  if [[ -n "${image}" ]]; then
    docker stop -t 10 nexuswiki-smoke-api nexuswiki-smoke-worker >/dev/null 2>&1 || true
  else
    [[ -z "${api_pid}" ]] || kill "${api_pid}" 2>/dev/null || true
    [[ -z "${worker_pid}" ]] || kill "${worker_pid}" 2>/dev/null || true
  fi
  rm -rf "${tmp_dir}"
}
trap cleanup EXIT

wait_for_exit() {
  local pid="$1"
  local timeout="$2"
  local elapsed=0
  while kill -0 "${pid}" 2>/dev/null; do
    if (( elapsed >= timeout * 10 )); then
      return 1
    fi
    sleep 0.1
    ((elapsed += 1))
  done
}

if [[ -n "${image}" ]]; then
  docker run --rm --name nexuswiki-smoke-api -e PORT=8011 -p 8011:8011 "${image}" python -m api >"${api_log}" 2>&1 &
else
  PORT=8011 uv run --package api python -m api >"${api_log}" 2>&1 &
fi
api_pid=$!

api_ready=false
for _ in {1..200}; do
  if [[ "$(curl -fsS -o /dev/null -w '%{http_code}' http://127.0.0.1:8011/health 2>/dev/null || true)" == "200" ]]; then
    api_ready=true
    break
  fi
  sleep 0.1
done
if [[ "${api_ready}" != "true" ]]; then
  cat "${api_log}"
  exit 1
fi

if [[ -n "${image}" ]]; then
  docker stop -t 10 nexuswiki-smoke-api >/dev/null
else
  kill -TERM "${api_pid}"
fi
if ! wait_for_exit "${api_pid}" 10; then
  cat "${api_log}"
  exit 1
fi
# API는 10초 안에 내려가는지만 판정한다. uv 래퍼는 전달한 SIGTERM을 143으로 보고할 수 있다.
wait "${api_pid}" || true
api_pid=""

if [[ -n "${image}" ]]; then
  docker run --rm --name nexuswiki-smoke-worker "${image}" python -m worker >"${worker_log}" 2>&1 &
else
  uv run --package worker python -m worker >"${worker_log}" 2>&1 &
fi
worker_pid=$!

worker_ready=false
for _ in {1..150}; do
  if grep -q "worker.started" "${worker_log}"; then
    worker_ready=true
    break
  fi
  sleep 0.1
done
if [[ "${worker_ready}" != "true" ]]; then
  cat "${worker_log}"
  exit 1
fi

if [[ -n "${image}" ]]; then
  docker stop -t 10 nexuswiki-smoke-worker >/dev/null
else
  kill -TERM "${worker_pid}"
fi
if ! wait_for_exit "${worker_pid}" 10; then
  cat "${worker_log}"
  exit 1
fi
set +e
wait "${worker_pid}"
worker_status=$?
set -e
worker_pid=""
if [[ "${worker_status}" -ne 0 ]]; then
  cat "${worker_log}"
  exit 1
fi

echo "smoke_tracer: ok"
