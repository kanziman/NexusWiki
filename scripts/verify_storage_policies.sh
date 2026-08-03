#!/usr/bin/env bash
set -euo pipefail

# ⚠️ ON_ERROR_STOP=1이 없으면 SQL 단언이 raise exception을 실행해도 psql이
#    성공 코드로 끝나 정책 회귀를 조용히 통과시킬 수 있습니다.
output="$({
  docker exec -i supabase_db_NexusWiki \
    psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - \
    < supabase/tests/0005_storage_policies.sql
} 2>&1)"

printf '%s\n' "$output"
grep -q 'storage_policies: ok' <<< "$output"
