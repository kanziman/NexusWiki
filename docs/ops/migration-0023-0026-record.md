# Migration 0023~0026 application record

## Scope

요청 trace와 비용 회계를 위한 마이그레이션 네 개다. 전부 추가 전용이며, 컬럼은 null을 허용하고 새 함수 인자에는 기본값이 있어 이전 버전 코드가 그대로 동작한다.

| 번호 | 내용 |
| --- | --- |
| `0023_job_trace.sql` | `jobs.trace_id`, `jobs.last_claimed_at`, `claim_job` · `complete_job_and_chain` · `enqueue_source_job`의 trace 전달 |
| `0024_usage_trace.sql` | `usage_events.trace_id`, `usage_events.duration_ms` |
| `0025_ask_trace.sql` | `ask_messages.trace_id`, `ask_messages.control_report`, `start_ask_turn` · `finalize_ask_turn`의 새 인자, 작성자 UPDATE를 종결 컬럼으로 제한, 이미 쓰인 trace의 턴 INSERT를 거부하는 트리거, Ask 턴의 trace로 잡을 만드는 호출 거부 |
| `0026_ask_trace_aggregate.sql` | 작성자를 드러내지 않는 editor 전용 집계 RPC `ask_trace_aggregate` |

관련 OpenSpec change: `ai-control-flow-accounting`.

## 로컬 적용

측정 일시: 2026-11-02 (KST)

- 적용 방법: `npx -y supabase@2.84.2 migration up --local` (2026-11-02 Mac에서 `supabase` 2.111.0으로 다시 적용)
- `0025`, `0026`은 리뷰 지적을 반영해 첫 로컬 적용 뒤 파일을 직접 수정했다. 클라우드에 적용한 적이 없어 번호를 늘리지 않았다. 이전 내용으로 적용한 로컬 DB는 다시 만들어야 한다 (`supabase db reset`).
- 확인: `supabase_migrations.schema_migrations`의 최신 값이 `0026`이다.
- 검증: `supabase/tests/0023_job_trace.sql`이 `job_trace: ok`를 출력하고 롤백했다.
- 경계 검증: `apps/api/tests/test_control_router.py`, `apps/api/tests/test_tenant_isolation_full_path.py`, `apps/api/tests/test_observability_e2e.py`가 로컬 스택에서 통과했다.

- 부분 적용 확인: 임시 Supabase 프로젝트에 `0024`까지만 적용한 상태에서 `supabase/tests/0023_job_trace.sql`이 `job_trace: ok`를 출력했다. 이어서 `0025`, `0026`을 적용해도 같은 결과였고, `enqueue_source_job`의 definer와 권한(`authenticated`만 실행)이 유지되었다.

## 클라우드 적용

⚠️ **아직 적용하지 않았다.** 이 절은 적용한 뒤에 결과로 채운다.

적용 전에 확인할 사항은 다음과 같다.

1. `supabase migration list --linked`로 클라우드의 최신 번호가 `0022`인지 확인한다. 이미 뒷번호가 있으면 번호를 다시 정해야 한다.
2. `supabase db push --linked --dry-run`의 대상이 네 파일뿐인지 확인한다.
3. 실제 `db push`는 운영자가 직접 실행한다.
4. 적용 뒤 위조 토큰으로 `POST /workspaces/{id}/retrieval`을 호출해 401인지 확인한다. 클라우드 게이트웨이의 응답 코드가 `PGRST30x`가 아니면 500이 되며, 이때도 임베딩 호출과 비용은 생기지 않는다. 로컬에서만 확인한 동작이다.

배포 순서는 DB, 워커, API, 대시보드다. 환경 변수는 `docs/ops/railway-env-checklist.md`를 따른다. Langfuse 키는 선택 사항이며, 지정하지 않으면 내보내기만 비활성이다.

## 롤백

코드를 되돌리면 된다. 추가한 컬럼과 인자는 이전 코드에 영향을 주지 않으므로 스키마는 되돌리지 않는다. 내보내기만 끄려면 Langfuse 키를 제거하고 프로세스를 재시작한다.
