#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${1:-$repo_root/supabase/migrations/0011_retrieval.sql}"
if [ ! -f "$target" ]; then
  echo "ci_check_retrieval_contract: missing $target" >&2
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
echo "ci_check_retrieval_contract: ok ($target)"
