# Migration 0021 application record

## Scope

`0021_source_deletion_integrity.sql`는 원문(raw source) 영구 삭제의 참조 무결성과 Storage 정리 잡을 추가한다.

- Storage 경로 파서 `storage_path_source(text)`와 `storage.objects`의 `sources_objects_*` 정책 3종
- 참조 잠금·검사 헬퍼 `lock_raw_source_reference` · `assert_raw_source_reference`
- 참조 가드 트리거 4종 — `wiki_pages` · `wiki_page_publications` · `ask_messages` · `jobs`
- 오너 전용 삭제 RPC `delete_raw_source(uuid, uuid)`

관련 OpenSpec change: `deletion-integrity-hardening` (PR [#118](https://github.com/kanziman/NexusWiki/pull/118), `2f64376`).

## 클라우드 적용

측정 일시: 2026-09-01 (KST)

### ⚠️ push를 막은 로컬/원격 원장 불일치

첫 `db push --dry-run`이 마이그레이션이 아니라 **원장 불일치로 거부**됐다.

```
LegacyDbPushMissingLocalError: Remote migration versions not found in local migrations directory.
```

원인: `0020_workspace_byok_api_key.sql`이 **원격에는 이미 적용돼 있는데 로컬 브랜치에는 파일이 없었다.** 그 파일은 아직 머지되지 않은 `feat/workspace-byok-api-key` 브랜치(`e4b1f0e`)에만 존재한다.

⚠️ CLI가 제안하는 `supabase migration repair --status reverted 0020`을 **따르면 안 된다.** 프로덕션에는 `workspaces.custom_api_key` 컬럼이 실제로 존재하므로, reverted로 표시하는 순간 원장이 스키마와 어긋난 거짓이 되고 이후 누군가 0020을 재적용하려 들게 된다.

올바른 처치는 로컬에 파일을 되살리는 것이다:

```bash
git show feat/workspace-byok-api-key:supabase/migrations/0020_workspace_byok_api_key.sql \
  > supabase/migrations/0020_workspace_byok_api_key.sql
```

`0021` 파일 헤더가 이미 이 위험을 예고하고 있었다 — "0020은 병렬 진행 중인 workspace BYOK 변경이 예약했다 … 병합 전 0020이 먼저 main에 들어왔는지 확인해야 한다". 번호를 예약해 둔 브랜치가 머지되기 전에 뒷번호를 push하면 이 상태가 재현된다.

### 방법

- push 직전 `supabase migration list --linked`로 `0021`의 Remote 열이 비어 있고 `0020`의 Local 열이 비어 있음을 확인했다.
- 위 처치로 `0020` 파일을 로컬에 복원한 뒤 `supabase db push --linked --dry-run`으로 적용 대상이 `0021` 하나뿐임을 확인했다.
- 실제 `supabase db push --linked`는 **운영자가 직접 실행했다**(에이전트 세션의 프로덕션 쓰기 권한 밖).
- 적용 후 `supabase migration list --linked`와 `supabase db query --linked`의 카탈로그 조회로 검증했다.
- 자격 증명·연결 문자열은 기록하지 않는다.

### 결과

dry-run JSON:
`{"upToDate":false,"dryRun":true,"migrations":["0021_source_deletion_integrity.sql"],"seeds":[],"roles":[],"message":"Finished supabase db push."}`

실제 push의 stdout JSON은 이 기록에 남기지 않는다 — 운영자 터미널에서 실행돼 세션이 회수하지 못했다. 대신 아래 카탈로그 조회로 적용 결과를 직접 확인했다.

#### `migration list` 로컬/원격 대조표

| Local | Remote | 일치 |
| --- | --- | --- |
| 0001 ~ 0019 | 0001 ~ 0019 | 변화 없음 |
| 0020 | 0020 | 로컬 파일 복원 후 채워짐 (원격은 이전부터 적용돼 있었음) |
| 0021 | 0021 | push 후 채워짐 |

#### 원격 스키마 직접 조회

| 확인 항목 | 실제 반환값 | 판정 |
| --- | --- | --- |
| `storage_path_source.prosecdef` | false (invoker) | pass |
| `lock_raw_source_reference.prosecdef` | true | pass |
| `assert_raw_source_reference.prosecdef` | true | pass |
| `enforce_wiki_source_references.prosecdef` | true | pass |
| `enforce_publication_source_references.prosecdef` | true | pass |
| `enforce_ask_source_references.prosecdef` | true | pass |
| `enforce_job_source_reference.prosecdef` | true | pass |
| `delete_raw_source.prosecdef` | true | pass |
| 트리거 `wiki_pages_source_reference_guard` | `wiki_pages`에 존재 | pass |
| 트리거 `wiki_publications_source_reference_guard` | `wiki_page_publications`에 존재 | pass |
| 트리거 `ask_messages_source_reference_guard` | `ask_messages`에 존재 | pass |
| 트리거 `jobs_source_reference_guard` | `jobs`에 존재 | pass |
| `storage.objects` 정책 | `sources_objects_select_member`(r) · `sources_objects_insert_editor`(a) · `sources_objects_delete_owner`(d), 전부 roles `{authenticated}` | pass |
| `anon`의 `sources_objects_*` 정책 | 없음 | pass |

#### `delete_raw_source` EXECUTE 권한

| 역할 | `has_function_privilege(..., 'EXECUTE')` | 판정 |
| --- | --- | --- |
| `anon` | false | pass |
| `authenticated` | true | pass |
| `service_role` | false | pass |

마이그레이션의 `revoke all … from public, anon, service_role` + `grant execute … to authenticated`가 원격에 그대로 반영됐다. `0018` 기록에서 남았던 "EXECUTE가 세 역할 모두 true" 문제가 이 번호에서는 재현되지 않는다.

## Rollback

이미 클라우드에 기록된 `0021`을 고치거나 지우지 않는다. 동작을 되돌리려면 이후 번호 마이그레이션으로 트리거와 정책을 회수한다.

## 후속 조치

- `feat/workspace-byok-api-key` 브랜치가 머지되면 `supabase/migrations/0020_workspace_byok_api_key.sql`이 정식으로 `main`에 들어온다. 그때까지 이 워킹트리의 복원본은 untracked로 남는다 — **삭제하면 다음 push가 같은 이유로 다시 막힌다.**
