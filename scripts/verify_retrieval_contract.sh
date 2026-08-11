#!/usr/bin/env bash
set -euo pipefail

status=0
output="$({
  docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1 -f - \
    < supabase/tests/0011_retrieval_contract.sql
} 2>&1)" || status=$?
printf '%s\n' "$output"
[ "$status" -eq 0 ]
grep -q 'retrieval_contract: ok' <<< "$output"
