#!/usr/bin/env bash
set -euo pipefail

PORT="${PORT:-3000}"
export NEXT_TELEMETRY_DISABLED=1

# 백그라운드 잡을 독립 프로세스 그룹으로 만들어 Next 자식 워커까지 종료한다.
set -m
pnpm --dir apps/dashboard exec next dev --port "$PORT" >/tmp/nexuswiki-dashboard.log 2>&1 &
dashboard_pid=$!

cleanup() {
  kill -- -"$dashboard_pid" 2>/dev/null || kill "$dashboard_pid" 2>/dev/null || true
  wait "$dashboard_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

for _ in $(seq 1 60); do
  if [ "$(curl -fsS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT/" 2>/dev/null || true)" = "200" ]; then
    echo "smoke_dashboard: ok"
    exit 0
  fi
  if ! kill -0 "$dashboard_pid" 2>/dev/null; then
    cat /tmp/nexuswiki-dashboard.log >&2
    exit 1
  fi
  sleep 1
done

cat /tmp/nexuswiki-dashboard.log >&2
exit 1
