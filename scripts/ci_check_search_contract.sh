#!/usr/bin/env bash
set -euo pipefail

# `public.search_chunks`를 마지막으로 정의한 마이그레이션에서, 재생성할 때 반드시
# 함께 옮겨야 하는 아홉 토큰이 살아 있는지 **소스 수준**으로 검사한다. 하나라도
# 없으면 그 토큰 이름을 출력하며 non-zero로 종료한다.
#
# 관련 태스크: P2-EMB-01
# 설계 근거: 03-CONTEXT.md > D-08
#
# ⚠️ D-08은 "GitHub Actions PR 게이트에 추가"를 요구했고 그 항목은
#    `### Claude's Discretion` 블록 안에 있다. 형태를 바꾸었으므로 이유를 남긴다 —
#    러너에는 Supabase 스택이 없고, 세우지 않기로 한 것은 .github/workflows/ci.yml
#    155-169행의 명시적 결정이다. 스택을 세우면 이 잡이 검증하는 대상이 마이그레이션이
#    아니라 "CLI가 러너에서 뜨는가"로 바뀐다. 그래서 역할을 둘로 나눈다:
#      - psql 계약 러너(scripts/verify_search_contract.sh)  — 로컬·수동. 실제 스키마를 본다.
#      - 이 스크립트                                        — PR마다. 소스를 본다.
#    D-08이 CI에 요구한 실제 목표는 "Phase 4가 검색 함수를 다시 건드릴 때의 회귀"이고,
#    그 회귀는 마이그레이션 소스에서 먼저 드러난다.
#
# ⚠️ 이 검사는 **계약이 파일에 적혀 있는가**만 본다. 적힌 대로 DB에 섰는지는 보지
#    않는다. 그 판정은 psql 러너의 몫이며, 두 검사 중 하나만 두면 각각의 사각이
#    그대로 남는다.
#
# 사용법
#   bash scripts/ci_check_search_contract.sh              # 저장소의 supabase/migrations
#   bash scripts/ci_check_search_contract.sh <디렉터리>   # 대상 부재를 확인하는 음성 테스트용

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
migrations_dir="${1:-$repo_root/supabase/migrations}"

# 탐색 대상 — search_chunks를 정의하는 마이그레이션. 파일명 정렬이 곧 적용 순서이므로
# 가장 나중 파일 하나가 현재 유효한 정의다.
target=""
while IFS= read -r file; do
  if grep -q 'create or replace function public\.search_chunks' "$file"; then
    target="$file"
  fi
done < <(find "$migrations_dir" -maxdepth 1 -type f -name '*.sql' 2>/dev/null | sort)

# ⚠️ 대상 파일이 0개면 통과가 아니라 실패다. 경로가 바뀌었거나 체크아웃이 얕게 된
#    상태에서 "아무것도 못 찾았으니 통과"로 넘어가면 이 검사는 그 순간부터 영구히
#    아무것도 지키지 않는다.
if [ -z "$target" ]; then
  echo "ci_check_search_contract: search_chunks를 정의하는 마이그레이션이 0개다 ($migrations_dir) — 경로가 바뀌었는지 확인할 것" >&2
  exit 2
fi

# 주석은 계약이 아니다. `-- security invoker`라고 적어둔 설명문이 검사를 통과시키면
# 이 게이트는 아무것도 지키지 않는다.
body="$(grep -v '^[[:space:]]*--' "$target")"

# 라벨과 ERE 패턴을 한 줄에 담는다 (연관 배열은 bash 3.2에서 쓸 수 없다).
TOKENS=(
  'security invoker|security[[:space:]]+invoker'
  'stable|(^|[^[:alnum:]_])stable([^[:alnum:]_]|$)'
  'set search_path = public|set[[:space:]]+search_path[[:space:]]*=[[:space:]]*public'
  'set hnsw.iterative_scan|set[[:space:]]+hnsw\.iterative_scan'
  'set hnsw.ef_search|set[[:space:]]+hnsw\.ef_search'
  'set hnsw.max_scan_tuples|set[[:space:]]+hnsw\.max_scan_tuples'
  'operator(extensions.<=>)|operator\(extensions\.<=>\)'
  'pgvector warmup|pgvector_warmup'
  'grant execute on function public.search_chunks|grant[[:space:]]+execute[[:space:]]+on[[:space:]]+function[[:space:]]+public\.search_chunks'
)

missing=()
for entry in "${TOKENS[@]}"; do
  label="${entry%%|*}"
  pattern="${entry#*|}"
  if ! grep -qE "$pattern" <<< "$body"; then
    missing+=("$label")
  fi
done

if [ "${#missing[@]}" -gt 0 ]; then
  echo "ci_check_search_contract: $target 에서 검색 함수 계약 토큰이 빠졌다" >&2
  printf '  - %s\n' "${missing[@]}" >&2
  echo "" >&2
  echo "재생성한 search_chunks는 0007:70-104의 계약을 전부 옮겨야 한다. 근거: 03-CONTEXT.md > D-08" >&2
  exit 1
fi

echo "ci_check_search_contract: ok ($target, ${#TOKENS[@]} tokens)"
