#!/usr/bin/env bash
set -euo pipefail

# apps/worker 밖에서 service key 경로(`worker.db.service` 모듈 · `service_client` 심볼)를
# 쓰는 곳을 찾아, 하나라도 있으면 non-zero로 종료한다. CI의 `service-usage` 잡이 이 스크립트를
# 그대로 부르고, 로컬에서도 인자 없이 저장소 루트 기준으로 실행할 수 있다.
#
# 관련 태스크: P2-BE-01
# 설계 근거: 02-CONTEXT.md > D-06, D-09 · checklists.json > decisions.db_access
#
# ⚠️ 이 검사는 **조기 경보**이지 1차 방어선이 아니다. 인과를 뒤집어 쓰지 말 것.
#    api와 worker는 단일 이미지를 공유하므로(01-CONTEXT.md > D-01) 이 import는 런타임에
#    물리적으로 가능하며, grep도 ruff의 TID251도 동적 import를 막지 못한다.
#    실제로 막는 것은 두 가지 **키의 부재**다 (02-CONTEXT.md > D-06):
#      1. `ApiSettings`에 `SUPABASE_SECRET_KEY` 필드가 존재하지 않는다 — 담을 그릇이 없다
#      2. Railway가 그 값을 worker 서비스 env에만 주입한다 — api 프로세스에 값 자체가 없다
#    이 스크립트가 하는 일은 그 둘이 지키는 경계를 **누가 넘으려 했는지 PR 단계에서 알리는 것**뿐이다.
#    "grep이 막고 있으니 안전하다"는 서술은 단일 이미지라는 사실과 어긋난다.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

# 탐색 대상 — worker 밖에서 service key 경로가 등장할 수 있는 소스 트리 전부.
TARGETS=(apps/api apps/dashboard packages)

# 매칭 규칙. 산문 언급이 아니라 **실제 사용**만 잡는다 — `apps/api/src/api/db/user.py`의
# docstring이 `worker.db.service`를 역할 설명으로 인용하고 있고, 그것을 위반으로 세면
# 이 검사는 첫날부터 red가 되어 곧 꺼진다. 잡는 것은 셋뿐이다:
#   (1) 모듈 경로 import   — `from worker.db.service ...` / `import worker.db.service`
#   (2) 심볼 import        — `... import ... service_client`
#   (3) 호출               — `service_client(` / `m.service_client(`
PATTERN='(^|[^[:alnum:]_.])(from|import)[[:space:]]+worker\.db\.service([^[:alnum:]_]|$)'
PATTERN="$PATTERN"'|(^|[^[:alnum:]_.])import[[:space:]][^#]*[^[:alnum:]_]service_client([^[:alnum:]_]|$)'
PATTERN="$PATTERN"'|(^|[^[:alnum:]_])service_client[[:space:]]*\('

# 제외 목록. 각 항목에 "왜 제외하는가"를 남긴다 — 이유 없는 제외가 하나라도 늘어나면
# 이 검사는 조용히 아무것도 보지 않는 상태가 된다.
#   apps/api/tests/fixtures : 02-03이 만든 TID251 위반 픽스처가 **의도적으로** 위반을 담는다.
#                             경로를 정확히 지정한다 — 이름만으로 걸면 나중에 생길
#                             `apps/api/src/api/fixtures/` 같은 실코드 디렉터리까지 조용히 빠진다.
#   __pycache__             : 컴파일 산출물. 소스가 아니고 바이너리라 파일:행이 무의미하다.
#   node_modules            : 서드파티 의존성. 우리가 쓴 코드가 아니다.
#   .next                   : dashboard 빌드 산출물. 소스가 아니며 번들 검사는 bundle-secrets 잡의 몫이다.
files=()
while IFS= read -r file; do
  files+=("$file")
done < <(
  find "${TARGETS[@]}" \
    \( -path 'apps/api/tests/fixtures' \
       -o -name '__pycache__' \
       -o -name 'node_modules' \
       -o -name '.next' \) -prune \
    -o -type f -print
)

# ⚠️ 대상 파일이 0개면 통과가 아니라 실패다. 경로가 바뀌었거나 체크아웃이 얕게 된 상태에서
#    "아무것도 못 찾았으니 통과"로 넘어가면 이 검사는 그 순간부터 영구히 아무것도 지키지 않는다.
if [ "${#files[@]}" -eq 0 ]; then
  echo "ci_check_service_usage: 탐색 대상 파일이 0개다 (${TARGETS[*]}) — 경로가 바뀌었는지 확인할 것" >&2
  exit 2
fi

# grep은 미발견을 1로, 실제 오류를 2 이상으로 낸다. 셋을 뭉개면 grep이 터진 실행이
# "위반 없음"으로 읽힌다. 종료 코드를 받아 세 갈래로 나눠 판정한다.
matches=""
status=0
matches="$(grep -nE "$PATTERN" "${files[@]}")" || status=$?

if [ "$status" -gt 1 ]; then
  echo "ci_check_service_usage: grep이 오류로 종료했다 (exit $status)" >&2
  exit 2
fi

if [ "$status" -eq 0 ]; then
  echo "ci_check_service_usage: apps/worker 밖에서 service key 경로 사용이 발견됐다" >&2
  printf '%s\n' "$matches" >&2
  echo "" >&2
  echo "사용자 요청 경로는 요청자 JWT를 쓰는 api.db.user 를 쓴다. 근거: checklists.json > decisions.db_access" >&2
  exit 1
fi

echo "ci_check_service_usage: ok (${#files[@]} files scanned)"
