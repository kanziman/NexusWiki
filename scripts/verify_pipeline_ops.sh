#!/usr/bin/env bash
set -euo pipefail

# ⚠️ ON_ERROR_STOP=1이 없으면 SQL 단언이 raise exception을 실행해도 psql이
#    성공 코드로 끝나 파이프라인 운영 함수 계약 회귀를 조용히 통과시킬 수 있습니다.
status=0
output="$({
  docker exec -i supabase_db_NexusWiki \
    psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - \
    < supabase/tests/0009_pipeline_ops.sql
} 2>&1)" || status=$?

# ⚠️ scripts/verify_search_contract.sh와 같은 이유로 종료 코드를 먼저 받아 둡니다.
#    실패한 명령의 출력을 변수에 담은 채 set -e로 곧바로 종료하면 어떤 단언이
#    깨졌는지가 사라지고 종료 코드만 남습니다. 판정은 그대로 non-zero입니다.
printf '%s\n' "$output"
[ "$status" -eq 0 ]
grep -q 'pipeline_ops: ok' <<< "$output"
