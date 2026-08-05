#!/usr/bin/env bash
set -euo pipefail

# BOOT-10 프로덕션 Auth 정책 회귀 검증.
# ⚠️ SUPABASE_SECRET_KEY로 테스트 계정을 삭제하므로 개발자 머신 전용이다.
#    Railway api 서비스에는 이 키가 없으며 배포 환경에서 실행하면 안 된다.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$repo_root/.env.local"

if [[ ! -f "$env_file" ]]; then
  printf '%s\n' 'auth_hardening: missing .env.local' >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$env_file"
set +a

for required_name in SUPABASE_URL SUPABASE_PUBLISHABLE_KEY SUPABASE_SECRET_KEY; do
  if [[ -z "${!required_name:-}" ]]; then
    printf 'auth_hardening: missing %s\n' "$required_name" >&2
    exit 1
  fi
done

test_user_id=""
cleanup_count=0

cleanup_test_user() {
  local cleanup_status

  [[ -n "$test_user_id" ]] || return 0
  cleanup_status="$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' \
    --request DELETE \
    --header "apikey: $SUPABASE_SECRET_KEY" \
    --header "Authorization: Bearer $SUPABASE_SECRET_KEY" \
    "$SUPABASE_URL/auth/v1/admin/users/$test_user_id" || true)"
  if [[ "$cleanup_status" == "200" || "$cleanup_status" == "204" ]]; then
    cleanup_count=1
    test_user_id=""
    return 0
  fi

  printf 'auth_hardening: cleanup failed (%s)\n' "$cleanup_status" >&2
  return 1
}

trap cleanup_test_user EXIT

request_auth() {
  local method="$1"
  local endpoint="$2"
  local body="$3"
  local output_file="$4"

  curl --silent --show-error \
    --request "$method" \
    --header "apikey: $SUPABASE_PUBLISHABLE_KEY" \
    --header 'Content-Type: application/json' \
    --output "$output_file" \
    --write-out '%{http_code}' \
    --data "$body" \
    "$SUPABASE_URL$endpoint"
}

tmp_dir="$(mktemp -d)"
trap 'cleanup_test_user; rm -rf "$tmp_dir"' EXIT

nonce="$(date +%s)-$RANDOM"
test_email="nexuswiki.auth.hardening+$nonce@gmail.com"
weak_password='A1!b2?'
strong_password='NexusWiki!2026Ab'

weak_status="$(request_auth POST '/auth/v1/signup' \
  "$(jq -nc --arg email "$test_email" --arg password "$weak_password" '{email: $email, password: $password}')" \
  "$tmp_dir/weak.json")"
weak_code="$(jq -r '.error_code // .code // empty' "$tmp_dir/weak.json")"
if [[ ! "$weak_status" =~ ^4[0-9][0-9]$ ]] || \
   ! jq -e '[(.error_code // ""), (.code // ""), (.msg // ""), (.message // "")] | join(" ") | test("weak|password.*(short|length|characters)"; "i")' \
     "$tmp_dir/weak.json" >/dev/null; then
  printf 'auth_hardening: weak-password assertion failed (%s)\n' "$weak_status" >&2
  exit 1
fi
printf 'weak_password_signup: rejected (%s, %s)\n' "$weak_status" "${weak_code:-password_policy_error}"

signup_status="$(request_auth POST '/auth/v1/signup' \
  "$(jq -nc --arg email "$test_email" --arg password "$strong_password" '{email: $email, password: $password}')" \
  "$tmp_dir/signup.json")"
test_user_id="$(jq -r '(.user // .).id // empty' "$tmp_dir/signup.json")"
if [[ ! "$signup_status" =~ ^2[0-9][0-9]$ ]] || \
   ! jq -e '((.user // .).id | type == "string") and ((.user // .).email_confirmed_at == null)' "$tmp_dir/signup.json" >/dev/null; then
  printf 'auth_hardening: confirmation-pending assertion failed (%s)\n' "$signup_status" >&2
  exit 1
fi
printf 'strong_password_signup: confirmation pending (%s)\n' "$signup_status"

login_status="$(request_auth POST '/auth/v1/token?grant_type=password' \
  "$(jq -nc --arg email "$test_email" --arg password "$strong_password" '{email: $email, password: $password}')" \
  "$tmp_dir/login.json")"
login_code="$(jq -r '.error_code // .code // empty' "$tmp_dir/login.json")"
if [[ ! "$login_status" =~ ^4[0-9][0-9]$ ]] || \
   ! jq -e '[(.error_code // ""), (.code // ""), (.msg // ""), (.message // "")] | join(" ") | test("email.*not.*confirm|not.*confirmed"; "i")' \
     "$tmp_dir/login.json" >/dev/null; then
  printf 'auth_hardening: unconfirmed-login assertion failed (%s)\n' "$login_status" >&2
  exit 1
fi
printf 'unconfirmed_email_login: rejected (%s, %s)\n' "$login_status" "${login_code:-email_not_confirmed}"

cleanup_test_user
trap - EXIT
rm -rf "$tmp_dir"
printf 'test_users_deleted: %s\n' "$cleanup_count"
printf '%s\n' 'auth_hardening: ok'
