#!/usr/bin/env bash
set -euo pipefail

# SEC-05가 실제 값만 차단하는지 독립 fixture에서 검증한다. 테스트용 key payload는
# 실행 중에만 만들므로 저장소와 CI 로그에 key 형태의 리터럴을 남기지 않는다.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

secret_value="sb_secret_$(printf 'x%.0s' {1..32})"

make_fixture() {
  local name="$1"
  fixture_root="$tmp_dir/$name"
  mkdir -p "$fixture_root/scripts"
  cp "$repo_root/scripts/ci_check_bundle_secrets.sh" "$fixture_root/scripts/"
}

expect_pass() {
  local name="$1"
  if ! (cd "$fixture_root" && bash scripts/ci_check_bundle_secrets.sh) >/dev/null 2>&1; then
    echo "test_ci_check_bundle_secrets: $name 은 통과해야 한다" >&2
    exit 1
  fi
}

expect_fail() {
  local name="$1"
  if (cd "$fixture_root" && bash scripts/ci_check_bundle_secrets.sh) >/dev/null 2>&1; then
    echo "test_ci_check_bundle_secrets: $name 은 실패해야 한다" >&2
    exit 1
  fi
}

make_fixture "missing-bundle"
expect_fail "산출물 부재"

make_fixture "empty-bundle"
mkdir -p "$fixture_root/apps/dashboard/.next"
expect_fail "빈 산출물"

make_fixture "sdk-diagnostics"
mkdir -p "$fixture_root/apps/dashboard/.next/server"
printf '%s\n' 'sb_secret_ SUPABASE_SECRET_KEY' >"$fixture_root/apps/dashboard/.next/server/sdk.js"
expect_pass "SDK 진단 문자열"

for surface in static server source-map; do
  make_fixture "actual-$surface"
  case "$surface" in
    static) target="$fixture_root/apps/dashboard/.next/static/chunk.js" ;;
    server) target="$fixture_root/apps/dashboard/.next/server/chunk.js" ;;
    source-map) target="$fixture_root/apps/dashboard/.next/server/chunk.js.map" ;;
  esac
  mkdir -p "$(dirname "$target")"
  printf '%s\n' "$secret_value" >"$target"
  expect_fail "실제 key $surface 산출물"
done

make_fixture "cache-excluded"
mkdir -p "$fixture_root/apps/dashboard/.next/cache"
printf '%s\n' "$secret_value" >"$fixture_root/apps/dashboard/.next/cache/pack"
expect_fail "cache만 있는 빈 배포 산출물"

make_fixture "cache-with-clean-artifact"
mkdir -p "$fixture_root/apps/dashboard/.next/cache" "$fixture_root/apps/dashboard/.next/static"
printf '%s\n' "$secret_value" >"$fixture_root/apps/dashboard/.next/cache/pack"
printf '%s\n' 'clean bundle' >"$fixture_root/apps/dashboard/.next/static/chunk.js"
expect_pass "cache 제외"

echo "test_ci_check_bundle_secrets: ok"
