#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${1:-$repo_root/supabase/migrations/0011_retrieval.sql}"
contract_sql="$repo_root/supabase/tests/0011_retrieval_contract.sql"
if [ ! -f "$target" ]; then
  echo "ci_check_retrieval_contract: missing $target" >&2
  exit 2
fi
if [ ! -f "$contract_sql" ]; then
  echo "ci_check_retrieval_contract: missing $contract_sql" >&2
  exit 2
fi
body="$(grep -v '^[[:space:]]*--' "$target")"
tokens=(
  'source writer|index_source_chunk_lexical'
  'wiki writer|index_wiki_page_lexical'
  'source lexical|search_source_lexical'
  'wiki lexical|search_wiki_lexical'
  'wiki vector|search_wiki_embeddings'
  'graph|expand_wiki_graph'
  'security invoker|security[[:space:]]+invoker'
  'stable|stable'
  'volatile|volatile'
  'search path|set[[:space:]]+search_path[[:space:]]*=[[:space:]]*public'
  'HNSW iterative|hnsw\.iterative_scan'
  'HNSW ef|hnsw\.ef_search'
  'HNSW scan tuples|hnsw\.max_scan_tuples'
  'qualified vector operator|operator\(extensions\.<=>\)'
  'phrase query|phraseto_tsquery\('\''simple'\'''
  'resolved graph links|l\.resolved'
  'cycle guard|any\(walk\.path\)'
  'seed bound|cardinality\(p_seed_wiki_ids\).*10'
  'fanout bound|p_fanout.*5'
  'total bound|p_total_limit.*50'
  'PostgREST reload|reload schema'
)
missing=()
for entry in "${tokens[@]}"; do
  label="${entry%%|*}"; pattern="${entry#*|}"
  grep -qE "$pattern" <<< "$body" || missing+=("$label")
done
if [ "${#missing[@]}" -gt 0 ]; then
  printf 'ci_check_retrieval_contract: missing contract token(s):\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi
contract_body="$(grep -v '^[[:space:]]*--' "$contract_sql")"
contract_tokens=(
  'source named HNSW assertion|source_chunks_embedding_idx'
  'wiki named HNSW assertion|wiki_embeddings_embedding_idx'
  'JSON plan explain|explain \(format json\)'
  'recursive plan walk|with recursive nodes'
  'direct query contract|operator\(extensions\.<=>\)'
  'clamped candidate limit|least\(greatest\('
  'authenticated role|set local role authenticated'
  'JWT claims|set local request\.jwt\.claims'
  'exact-dataset preflight|retrieval_contract_preflight'
  'manifest identity|p_manifest_identity'
  'source expected count|p_expected_source_rows'
  'wiki expected count|p_expected_wiki_rows'
  'preflight-only mode|retrieval_contract_preflight_only'
  'matched iterative setting|set local hnsw\.iterative_scan = '\''strict_order'\'''
  'matched ef setting|set local hnsw\.ef_search = '\''200'\'''
  'matched tuple setting|set local hnsw\.max_scan_tuples = '\''40000'\'''
)
missing=()
for entry in "${contract_tokens[@]}"; do
  label="${entry%%|*}"; pattern="${entry#*|}"
  grep -qE "$pattern" <<< "$contract_body" || missing+=("$label")
done
if grep -qE 'enable_(seqscan|sort|indexscan|bitmapscan)[[:space:]]*=' <<< "$contract_body"; then
  missing+=("test-only planner forcing")
fi
planner_locals="$(grep -Ei 'set[[:space:]]+local[[:space:]]+(enable_|.*(cost|scan|join|sort|parallel))' <<< "$contract_body" || true)"
if [ -n "$planner_locals" ] && grep -Evi "set[[:space:]]+local[[:space:]]+hnsw\.(iterative_scan|ef_search|max_scan_tuples)[[:space:]]*=" <<< "$planner_locals" | grep -q .; then
  missing+=("unmatched SET LOCAL planner forcing")
fi
if [ "${#missing[@]}" -gt 0 ]; then
  printf 'ci_check_retrieval_contract: missing or forbidden contract token(s):\n' >&2
  printf '  - %s\n' "${missing[@]}" >&2
  exit 1
fi
echo "ci_check_retrieval_contract: ok ($target)"
