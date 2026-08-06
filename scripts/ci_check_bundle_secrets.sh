#!/usr/bin/env bash
set -euo pipefail

# dashboard 프로덕션 빌드 산출물에 service key 문자열이 남았는지 검사하고, 하나라도 있으면
# non-zero로 종료한다. CI의 `bundle-secrets` 잡이 dashboard 빌드 직후 이 스크립트를 부르고,
# 로컬에서도 `pnpm --dir apps/dashboard build` 뒤에 인자 없이 실행할 수 있다.
#
# 관련 태스크: P2-BE-01
# 설계 근거: 02-CONTEXT.md > D-09 (SEC-05의 클라이언트 번들 grep)
#
# 번들에 들어간 것은 사이트를 여는 모든 방문자가 읽는다. service key는 BYPASSRLS이므로
# (checklists.json > decisions.db_access) 번들 유출 한 번이 38개 격리 정책 전부를 장식으로 만든다.

# 검사 대상. 환경변수로 덮어쓸 수 있게 두지 않는다 — 보안 게이트에 우회 손잡이를 다는 셈이고,
# 파일이 하나뿐인 빈 디렉터리를 가리키면 아래의 0개 검사마저 통과해버린다.
BUNDLE_DIR="apps/dashboard/.next"

# 찾는 문자열. 값이 아니라 **접두어와 키 이름**이다.
PATTERNS=('sb_secret_' 'SUPABASE_SECRET_KEY')

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# ⚠️ 검사 대상이 없으면 pass가 아니라 fail이다. 빌드가 실패했거나 Next의 출력 경로가 바뀐
#    상태에서 "grep이 아무것도 못 찾았으니 통과"로 넘어가면, 이 검사는 그 시점부터 영구히
#    아무것도 지키지 않게 된다 (02-SPEC.md Edge Coverage R3). 디렉터리 부재와 "디렉터리는
#    있는데 파일이 0개"를 서로 다른 메시지로 구분해 낸다 — 원인이 빌드 실패인지 경로 변경인지가
#    로그만으로 갈리기 때문이다.
if [ ! -d "$BUNDLE_DIR" ]; then
  echo "ci_check_bundle_secrets: 검사 대상 디렉터리가 없다 — $BUNDLE_DIR" >&2
  echo "빌드가 실패했거나 Next 출력 경로가 바뀌었다. 산출물 부재는 통과가 아니라 실패다." >&2
  exit 1
fi

file_count="$(find "$BUNDLE_DIR" -type f | wc -l | tr -d '[:space:]')"
if [ "$file_count" -eq 0 ]; then
  echo "ci_check_bundle_secrets: $BUNDLE_DIR 에 파일이 0개다" >&2
  echo "디렉터리는 있으나 산출물이 비었다. 빈 결과를 통과로 넘기지 않는다." >&2
  exit 1
fi

# ⚠️ 출력에 매치된 값 자체를 싣지 않는다. CI 로그는 공개될 수 있으므로, secret을 탐지하는
#    검사가 그 secret을 로그로 옮기면 유출 경로가 하나 늘어난다. 내는 것은 **파일 경로 ·
#    패턴 이름 · 매치 개수** 셋뿐이며, grep -o 의 출력은 wc 로만 흘러가고 절대 인쇄되지 않는다.
violations=0
for pattern in "${PATTERNS[@]}"; do
  hits=""
  status=0
  # grep: 0=발견, 1=미발견, 2 이상=오류. 셋을 뭉개면 grep이 터진 실행이 "깨끗함"으로 읽힌다.
  # -a: 산출물에는 소스맵·webpack 팩처럼 grep이 바이너리로 판정하는 파일이 섞인다. 텍스트로
  #     강제하지 않으면 그 안의 문자열을 통째로 놓치고, 개수 세기도 "Binary file matches" 한 줄이 된다.
  hits="$(grep -rlaF -- "$pattern" "$BUNDLE_DIR")" || status=$?

  if [ "$status" -gt 1 ]; then
    echo "ci_check_bundle_secrets: grep이 오류로 종료했다 (exit $status) — 패턴 '$pattern'" >&2
    exit 2
  fi

  if [ "$status" -eq 0 ]; then
    while IFS= read -r file; do
      [ -n "$file" ] || continue
      count="$(grep -oaF -- "$pattern" "$file" | wc -l | tr -d '[:space:]')"
      echo "ci_check_bundle_secrets: 패턴 '$pattern' 이 $file 에 ${count}건 있다" >&2
      violations=$((violations + 1))
    done <<EOF
$hits
EOF
  fi
done

if [ "$violations" -gt 0 ]; then
  echo "" >&2
  echo "번들에 실린 문자열은 모든 방문자가 읽는다. service key는 worker 전용이며 클라이언트로 내려가서는 안 된다." >&2
  echo "근거: checklists.json > decisions.db_access · 02-CONTEXT.md > D-06" >&2
  exit 1
fi

echo "ci_check_bundle_secrets: ok ($BUNDLE_DIR, ${file_count} files scanned, ${#PATTERNS[@]} patterns)"
