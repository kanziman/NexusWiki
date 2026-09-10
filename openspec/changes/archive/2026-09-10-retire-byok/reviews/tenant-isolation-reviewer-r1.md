# Tenant Isolation 리뷰 — retire-byok r1

- 판정: pass
- 대상: `git diff main...HEAD` 브랜치 `fix/provider-credit-exhausted` 워킹트리 uncommitted 변경 (HEAD `3a960c2`)
- 일시: 2026-09-10T12:02:23Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `apps/api/src/api/routers/jobs.py:207` `workspace_budget`이 `_user_db(request, credentials)`(요청자 JWT)를 그대로 사용. `service_role`/service client 신규 도입 없음. 마이그레이션 `0022`는 관리자 컨텍스트에서 도는 스키마·데이터 정리이며 사용자 요청 경로가 아니므로 A-1 대상이 아님 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 change는 신규 테이블을 만들지 않음(기존 `workspaces.custom_api_key` 컬럼 값 정리만) |
| A-3 | anon 신규 GRANT/정책 | 해당 없음 | 마이그레이션 `0022`에 GRANT/정책 구문 없음(`UPDATE`·`COMMENT`만) |
| A-4 | service_role 워커의 workspace_id 필터 | 해당 없음 | 워커 변경은 `apps/worker/src/worker/errors.py`의 `ProviderCreditExhausted` 독스트링 정정뿐, DB 접근 코드 변경 없음. 마이그레이션 `0022`의 `update public.workspaces set custom_api_key = null where custom_api_key is not null;`(0022:6-8)은 `workspace_id` 필터가 없지만, 이는 job 단위로 도는 워커 런타임 코드가 아니라 **전 테넌트를 대상으로 한 일회성 스키마 마이그레이션**이며 proposal.md·design.md가 "모든 워크스페이스의 미사용 BYOK 값을 일괄 정리"로 스코프를 명시한 의도된 전역 연산 — A-4가 겨냥하는 "워커가 특정 workspace_id로 좁혀야 할 잡 처리"와는 다른 범주 |
| A-5 | 신규 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이번 변경은 UPDATE/DELETE 엔드포인트를 건드리지 않음. `workspace_budget`은 SELECT이고, RLS로 막힌 조회의 빈 결과(`cap_rows`가 빈 리스트)를 `cap_micros = 0`으로 처리하는 기존 로직(jobs.py:216, 주석 "읽기 0행은 RLS가 막은 경우에도 빈 목록이다")은 변경 전후 동일 — `has_custom_key` 분기 제거는 이 처리 경로에 영향 없음 |
| B-7 | SQLSTATE 42501 → 403 매핑 | 해당 없음 | `WITH CHECK` 경로 변경 없음 |
| C-8 | 멱등성(upsert 키) | 해당 없음 | 새 잡 핸들러 없음. 마이그레이션 자체는 `where custom_api_key is not null` 조건으로 재실행해도 안전(멱등) |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블 변경 없음 |
| D-10~14 | 벡터 검색·토크나이저·생성 컬럼·프롬프트·인용 앵커 | 해당 없음 | 이번 변경 범위 밖(검색·프롬프트 코드 미변경) |
| E-15 | 마이그레이션 번호 순서 | 통과 | 기존 최대 `0021_source_deletion_integrity.sql` 다음으로 `0022_retire_byok_custom_api_key.sql` 부여. 순서 어긋남 없음 |

## 항목별 상세 확인 (요청 사항 1~6)

**1. 마이그레이션 0022 스코프 및 실행 컨텍스트**
`update public.workspaces set custom_api_key = null where custom_api_key is not null;`(0022:6-8)에 `workspace_id` 필터가 없는 것은 실수가 아니라 의도된 전역 스코프다. proposal.md("기존에 등록된 `workspaces.custom_api_key` 값을 마이그레이션으로 전부 `null` 처리한다")와 design.md Migration Plan이 명시적으로 "모든 워크스페이스"를 대상으로 한다. Supabase 마이그레이션은 이 프로젝트 컨벤션상 `postgres`/관리자 권한으로 실행되며(`docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres`, CLAUDE.md "로컬 `psql`이 없다" 항목 및 기존 0001~0021 마이그레이션 전부가 `create policy`·`alter table` 등 RLS 자체를 정의하는 DDL이라는 사실이 이를 뒷받침) RLS를 우회하는 것이 맞다 — RLS는 `authenticated`/`anon` 런타임 역할에 적용되는 것이지 마이그레이션 실행자에게 적용되지 않는다. 단일 워크스페이스로 좁힐 이유가 없는 전사적 데이터 정리이므로 범위도 적절하다.

**2. jobs.py `workspace_budget`**
`_user_db(request, credentials)`로 요청자 JWT를 그대로 쓴다(jobs.py:207). `service_role` 오남용 없음. `has_custom_key` 분기 제거 후에도 "읽기 0행 → `cap_micros = 0`"(jobs.py:216) 로직은 코드상 그대로 남아 있고, 이번 diff가 건드린 것은 `-1`(무제한 표시) 산출 조건뿐이다. RLS가 막아 빈 리스트가 돌아오는 경우와 워크스페이스가 실제로 존재하지 않는 경우를 구분하지 않고 둘 다 `cap_micros=0`으로 표시하는 것은 이 엔드포인트의 원래 설계(다른 워크스페이스 존재 여부를 예산값으로 유출하지 않음)이며 이번 변경으로 깨지지 않았다.

**3. 컬럼을 null 처리만 하고 유지하는 결정**
design.md Risks 섹션(35행)이 "컬럼을 남겨두면 나중에 실수로 UI를 재연결할 위험"을 이미 인지하고, 그 완화책으로 컬럼 코멘트를 "BYOK는 UI·실제 라우팅 모두 비활성 상태 — 워커가 읽지 않는다. 재도입 전까지 값을 쓰지 않는다"(0022:10-11)로 갱신하는 조치를 마이그레이션에 실제로 반영했다. 보안 관점에서 컬럼에 남는 것은 전부 `null`이므로 비밀값 노출 리스크는 없다(마이그레이션이 실행되면 기존 등록 키가 전부 지워짐). 데이터 위생 관점에서 컬럼 유지 자체는 design.md가 이미 다룬 트레이드오프이고, 코멘트로 재노출을 막는 완화책도 마련되어 있어 이 change 범위에서는 충분하다.

**4. `ProviderCreditExhausted`(402) 로직 불변**
`git diff apps/worker/src/worker/errors.py`는 독스트링 문구 교체(BYOK 언급 제거 + 폐지 안내 추가)만 포함하고, `NON_RETRYABLE_ERRORS` 분류·`__init__` 등 실행 로직은 변경되지 않았다. 402 즉시 종결 동작(`c7e4a5e`에서 구현된 것)에 회귀 없음.

**5. BYOK UI 제거에 대한 사용자 안내 부재**
CLAUDE.md의 "조용한 실패" 금기(D-10~D-14, Anti-Patterns)는 "예외 없이 조용히 잘못된 결과/데이터 손상을 내는 시스템 결함"(0행을 403으로 매핑 안 함, 토크나이저 불일치, `hnsw.iterative_scan` 미설정 등)을 가리키는 개념이지, "이미 동작하지 않던 UI 기능을 제거하면서 앱 내 안내를 추가하지 않는 제품 결정"을 가리키지 않는다. 이 항목은 이 리뷰어의 15개 체크리스트(A~E) 어디에도 해당하지 않아 **해당 없음**으로 판정한다. 다만 design.md는 이 판단("애초에 동작한 적 없는 기능을 제거하는 것이므로 실패를 감추는 게 아니라 거짓 약속을 제거하는 것")을 proposal.md Why에서 명시적으로 근거를 댔고, 실제로 워커가 `custom_api_key`를 읽은 적이 없다는 사실(코드 검색으로 확인: 이번 diff 전후 모두 `apps/worker/`에 해당 컬럼을 읽는 코드 없음)과 부합하므로 판단 자체는 타당하다. 이는 tenant-isolation 리뷰 게이트의 판정 범위 밖이며, 필요하면 별도로 UX/제품 리뷰에서 다룰 사안이다.

**6. `set_workspace_budget` fixture와 테스트 격리**
`apps/api/tests/conftest.py:210-217`의 `two_workspaces_two_users`는 함수 스코프이며, docstring이 명시적으로 "세션·모듈 스코프로 공유하면 위양성·위음성이 함께 생긴다"는 이유로 함수 스코프 + teardown(`_destroy_actor`)을 강제한다. `set_workspace_budget`(conftest.py:367-386)은 이 change에서 신규 도입된 게 아니라 기존에 `test_sources_router.py`(예산 소진 케이스 4곳)에서 이미 쓰이던 픽스처이며, owner JWT로 자신의 워크스페이스만 PATCH한다(RLS owner-only UPDATE 정책에 의존). 각 테스트가 고유한 워크스페이스 쌍을 새로 발급받고 종료 시 파기하므로, `test_jobs_router.py`에 추가된 `set_workspace_budget(owner, 7_000_000)` 호출이 다른 테스트의 워크스페이스 상태를 오염시킬 경로는 없다.

## 조치가 필요한 항목

없음.

## 판정 근거

A-1(사용자 경로 service_role 오남용)·A-3(anon 신규 권한)·A-4(워커 workspace_id 필터 누락) 등 치명 등급 트리거가 전부 미해당이며, 유일하게 눈에 띄는 "필터 없는 UPDATE"(마이그레이션 0022)는 워커 런타임 코드가 아니라 관리자 권한으로 실행되는 일회성 마이그레이션이고 proposal·design 문서가 그 전역 스코프를 의도적으로 명시했다. B(오류 매핑)·C(멱등성)·D(조용한 실패 기술 항목)·E(마이그레이션 순서)는 이 change의 실제 변경 표면(표시 로직 단순화, UI 제거, 독스트링 정정, 데이터 정리 마이그레이션)과 겹치지 않거나 기존 동작을 그대로 보존한다. 기존에 노출되던 "무제한" 약속을 제거하는 이번 변경은 오히려 사용자에게 잘못된 예산 정보를 보여주던 기존 결함(스펙-구현 불일치)을 바로잡는 방향이며, 새로운 테넌트 경계 위반이나 조용한 데이터 손상 경로를 만들지 않는다.
