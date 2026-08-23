# Migration 0018 application record

## Scope

`0018_ask_history.sql`는 Ask 대화 스레드 이력을 추가한다. `ask_threads` · `ask_messages`, 작성자∩멤버십 RLS, `persist_ask_turn`(security invoker)가 포함된다.

## 클라우드 적용

측정 일시: 2026-08-23 (KST)

### 방법

- push **직전에** `supabase migration list --linked`로 원격 원장의 `0018` Remote 열이 비어 있음을 확인했다.
- `supabase db push --linked --dry-run`으로 적용 대상이 `0018_ask_history.sql` 하나뿐임을 확인했다.
- `supabase db push --linked`로 적용한 뒤 같은 `migration list`와 `supabase db query --linked`로 카탈로그를 조회했다.
- 자격 증명·연결 문자열은 기록하지 않는다.

### 결과

dry-run JSON:
`{"upToDate":false,"dryRun":true,"migrations":["0018_ask_history.sql"],"seeds":[],"roles":[],"message":"Finished supabase db push."}`

실제 push JSON:
`{"upToDate":false,"dryRun":false,"migrations":["0018_ask_history.sql"],"seeds":[],"roles":[],"message":"Finished supabase db push."}`

적용된 마이그레이션은 `0018` 하나뿐이며 부분 적용의 흔적은 없다.

#### `migration list` 로컬/원격 대조표

| Local | Remote | 일치 |
| --- | --- | --- |
| 0001 ~ 0017 | 0001 ~ 0017 | 변화 없음 |
| 0018 | 0018 | push 후 채워짐 |

#### 원격 스키마 직접 조회

| 확인 항목 | 실제 반환값 | 판정 |
| --- | --- | --- |
| `ask_threads.relrowsecurity` | true | pass |
| `ask_messages.relrowsecurity` | true | pass |
| `ask_threads` 정책 | select/insert/update/delete `_own`, roles `{authenticated}` | pass |
| `ask_messages` 정책 | select/insert `_own`, roles `{authenticated}` | pass |
| `anon` 정책 | 없음 | pass |
| `persist_ask_turn.prosecdef` | false (invoker) | pass |
| `ask_messages_turn_key` | unique | pass |

#### 원격 기본 ACL

클라우드 `pg_default_acl` 때문에 `information_schema.role_table_grants`에는 `anon`/`authenticated`/`service_role`의 DML GRANT가 보인다. 로컬 Docker ACL과 다르다. `0009` 기록과 같은 한계다. 행 접근은 RLS가 막는다 — `anon` 정책이 없으므로 테이블 GRANT가 있어도 행은 보이지 않는다.

`has_function_privilege(..., persist_ask_turn, EXECUTE)`는 원격에서 `anon`/`authenticated`/`service_role`이 true로 나왔다. 함수는 security invoker이고 INSERT/SELECT는 RLS `authenticated` 정책만 있으므로, `anon` 호출은 행을 쓰지 못한다. 이후 번호에서 EXECUTE를 `authenticated`만 남기려면 별도 마이그레이션이 필요하다. 이미 적용한 `0018` 파일은 수정하지 않는다.

## Rollback

이미 클라우드에 기록된 `0018`을 고치거나 지우지 않는다. 동작을 되돌리려면 이후 번호 마이그레이션으로 정책을 회수한다.
