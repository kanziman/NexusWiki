# Migration 0023~0026 application record

## Scope

요청 trace와 비용 회계를 위한 마이그레이션 네 개다. 컬럼은 null을 허용하고 새 함수 인자에는 기본값이 있어 이전 버전 애플리케이션 호출과 호환된다. `0025`는 작성자의 직접 UPDATE 권한을 좁히고 이미 쓰인 trace의 INSERT를 거부하므로, 권한까지 전부 추가 전용인 변경은 아니다.

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
- `0025`, `0026`은 리뷰 지적을 반영해 첫 로컬 적용 뒤 파일을 직접 수정했다. 당시에는 클라우드에 적용한 적이 없어 번호를 늘리지 않았다. 이전 내용으로 적용한 로컬 DB는 다시 만들어야 한다 (`supabase db reset`). 현재 클라우드에는 아래 보고대로 적용됐으므로 더는 이 파일들을 소급 수정하지 않는다.
- 확인: `supabase_migrations.schema_migrations`의 최신 값이 `0026`이다.
- 검증: `supabase/tests/0023_job_trace.sql`이 `job_trace: ok`를 출력하고 롤백했다.
- 경계 검증: `apps/api/tests/test_control_router.py`, `apps/api/tests/test_tenant_isolation_full_path.py`, `apps/api/tests/test_observability_e2e.py`가 로컬 스택에서 통과했다.

- 부분 적용 확인: 임시 Supabase 프로젝트에 `0024`까지만 적용한 상태에서 `supabase/tests/0023_job_trace.sql`이 `job_trace: ok`를 출력했다. 이어서 `0025`, `0026`을 적용해도 같은 결과였고, `enqueue_source_job`의 definer와 권한(`authenticated`만 실행)이 유지되었다.

## 클라우드 적용

기록 출처: 2026-11-02 사용자가 이 작업에 전달한 운영 복구 보고. 이번 문서 정리 세션에서 클라우드 명령을 다시 실행해 독립 확인한 결과는 아니다.

| 항목 | 보고된 결과 |
| --- | --- |
| 적용 전 원격 최신 버전 | `0021` (이 문서의 기존 `0022` 가정 정정) |
| 클라우드 적용 후 | `0026`까지 적용, 대기 0건 |
| API `/health` | HTTP 200, `git_sha`가 병합 커밋 `184c5b4`와 일치 |
| 위조 토큰 요청 | `/retrieval`, `/ask`, `/sources/text` 모두 HTTP 401 `unauthorized` |
| Vercel Production | `184c5b4` 배포 기록 생성, 완료 상태 미확인 |

따라서 위조 토큰의 401이 로컬에서만 확인됐다는 당시 한계는 보고된 클라우드 호출에서도 해소됐다. 이 호출들은 JWT 단계에서 거부되므로 실제 멤버의 인큐·턴 시작이나 워커 처리를 검증한 것은 아니다. 실제 push 대상 파일 목록과 상세 명령 출력은 전달받지 않았으므로, 대상이 네 파일뿐이었다거나 `0022`가 어떤 경로로 적용됐는지는 단정하지 않는다.

### 남은 운영 확인

- 실제 계정의 원문 등록 → 컴파일·임베딩 → Ask와 Control Room의 수집·질문 trace 확인.
- Railway worker의 정상 기동과 오류 로그, API의 `LANGFUSE_SECRET_KEY` 부재 확인.
- 클라우드 DB 조회는 403, Railway CLI는 로그인 만료로 확인하지 못했다고 보고됐다. 함수·트리거 권한은 클라우드에서 직접 확인하지 못했고, 동일 파일의 빈 로컬 DB 적용만 검증됐다.
- 배포 시작 12:31 UTC부터 DB push까지의 피해는 미확인이다. 잡 없이 남은 원문, 재시도 중 기록되지 않은 비용이 있을 수 있으며 존재나 규모를 확정하지 않는다.

### 이후 마이그레이션

현재 운영 코드와 호환되는 DB 변경은 main 머지 전에 적용·확인을 끝낸다. 계약 정본은 `openspec/specs/pull-request-workflow/spec.md`의 「자동 운영 배포 전 마이그레이션 게이트」이며, 실행 순서는 `docs/ops/railway-env-checklist.md`를 따른다. 다음 작업에서 원격 최신 번호를 고정값으로 가정하거나 이 기록을 현재 상태 조회 대신 사용하지 않는다.

배포 순서는 DB, 워커, API, 대시보드다. 환경 변수는 `docs/ops/railway-env-checklist.md`를 따른다. Langfuse 키는 선택 사항이며, 지정하지 않으면 내보내기만 비활성이다.

## 롤백

코드를 되돌리면 된다. 추가한 컬럼과 인자는 이전 코드에 영향을 주지 않으므로 스키마는 되돌리지 않는다. 내보내기만 끄려면 Langfuse 키를 제거하고 프로세스를 재시작한다.
