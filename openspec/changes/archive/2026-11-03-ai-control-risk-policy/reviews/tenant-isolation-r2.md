# Tenant Isolation 리뷰 — ai-control-risk-policy r2

- 판정: needs_fix
- 대상: `git diff origin/main...HEAD` (`fb34a5e743ec7b16d86c4ac27c350ac01c58617c`)
- 일시: 2026-11-02T23:49:18Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 신규 승인·거부 경로는 `_user_db(...).rpc`를 사용한다(`apps/api/src/api/routers/wiki.py:437`). 리스크 탭도 요청자 JWT를 쓰는 `_user_db`다(`apps/api/src/api/routers/control.py:615`, `:92`). |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | 두 테이블의 생성과 RLS 활성화가 `0033`의 동일 트랜잭션 안에 있다(`supabase/migrations/0033_wiki_write_control.sql:12`, `:39`, `:84`, `:205`). |
| A-3 | anon 신규 GRANT·정책 | 통과 | 신규 테이블 권한을 `public, anon, authenticated`에서 회수한 뒤 authenticated SELECT만 연다(`0033:45-47`, `:91-93`). 신규 RPC도 public·anon 실행을 회수한다(`0033:133-138`, `:198-201`, `0034:76-79`). |
| A-4 | 워커의 workspace_id 명시 필터 | 통과 | 신규 읽기·쓰기 헬퍼는 workspace_id를 필수로 받아 필터·행·RPC 인자에 반영한다(`apps/worker/src/worker/db/service.py:455-536`). 적용 핸들러는 잡의 workspace_id를 모든 테이블 작업에 전달한다(`apps/worker/src/worker/handlers/wiki_proposal_apply.py:52`, `:68`, `:75`, `:96`, `:109`, `:115`). |
| A-5 | 복합 FK | 통과 | 개정의 wiki_id와 제안의 wiki_id·raw_source_id는 `(id, workspace_id)` 복합 FK다(`0033:31-33`, `:68-73`). 개정의 raw_source_id·job_id는 FK 없이 감사 식별자로만 쓰며 권한 판정에 사용하지 않는다. 제안의 근거 청크는 기존 `replace_wiki_page_evidence` 경계가 테넌트·원문을 다시 제한한다. |
| B-6 | 0행 오류 매핑 | 통과 | 승인 RPC는 RLS에 의한 0행 대신 함수 입구에서 역할을 검사하고, 제안 UPDATE도 workspace_id와 pending으로 제한한다(`0033:156-170`). 없는 제안·처리된 제안·다른 테넌트 제안은 동일한 409다(`apps/api/src/api/routers/wiki.py:446`). 리스크 스냅샷의 예기치 않은 빈 결과는 403이다(`control.py:620`). |
| B-7 | 42501 → 403 | 통과 | 신규 definer RPC의 권한 거부는 42501이며 기존 단일 핸들러가 403으로 변환한다(`0033:156-157`, `0034:37-38`, `apps/api/src/api/errors.py:262`). viewer·비멤버 경계 테스트가 있다(`apps/api/tests/test_wiki_proposals.py:100`, `:128`). 전체 스위트의 기존 Storage 매핑 실패는 아래 검증 한계에 별도로 기록한다. |
| C-8 | 핸들러 멱등성 | 통과 | 개정은 `(wiki_id, job_id)` 유니크 키와 ignore-duplicates다(`0033:30`, `service.py:469-476`). 적용 후 재실행은 본문을 다시 쓰지 않고 link_sync 체인을 복구한다(`wiki_proposal_apply.py:57-65`). 승인과 잡 INSERT는 단일 RPC 트랜잭션이다(`0033:163-190`). |
| C-9 | jobs 직접 UPDATE | 통과 | 승인 RPC는 jobs에 INSERT만 한다(`0033:179`). 신규 핸들러는 상태 전이에 `complete_job_and_chain`을 사용한다(`wiki_proposal_apply.py:54`, `:60`, `:121`). |
| D-10 | iterative_scan | 해당 없음 | 벡터 검색 SQL 변경 없음. 변경은 임베딩 갱신 대상 선정이다. |
| D-11 | 토크나이저 일치 | 통과 | 승인 적용도 기존 컴파일과 같은 `bigram(normalize(content))` 및 `TSV_TOKENIZER_VERSION`으로 어휘 색인을 갱신한다(`wiki_proposal_apply.py:19`, `:109-114`). |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 생성 컬럼 전환 없음. |
| D-13 | str.format | 통과 | 변경된 프롬프트 조립 경로에 str.format 사용이 없다. 공통 정책은 메시지 경계에서 추가된다(`apps/worker/src/worker/llm.py:203`, `:383`). |
| D-14 | 인용 앵커 | 통과 | 분쟁 표시는 기존 위키 별칭 앵커 뒤에만 붙는다(`apps/api/src/api/services/ask.py:462-464`). 원문 앵커·발급 맵 구조를 변경하지 않는다. |
| E-15 | 마이그레이션 번호 | 통과(운영 확인 별도) | 최신 origin/main의 최대 번호는 0031이며 신규 번호는 0032~0034다. 운영 적용 여부는 CLI 권한 제한 때문에 확인되지 않았다. |

## r1 지적 재확인

| r1 항목 | 결과 | 근거 |
| --- | --- | --- |
| 1. 승인 뒤 낡은 벡터 색인 | 해소 | 저장된 chunk_content와 새 청크를 비교하고 다른 청크를 다시 임베딩한다(`apps/worker/src/worker/handlers/embed.py:75-104`, `service.py:687`). 회귀 테스트 `apps/worker/tests/test_risk_policy.py:556`, `:564`. |
| 2. 적용 표시 뒤 체인 유실 | 해소 | applied 재실행도 link_sync를 등록한다(`wiki_proposal_apply.py:57-65`). 회귀 테스트 `test_risk_policy.py:432`. |
| 3. 메타데이터 변경의 enforce 우회 | 해소 | 제목·분류·별칭·신뢰도 차이를 분류에 전달하고 protected page에서 high로 보류한다(`apps/worker/src/worker/handlers/compile.py:433-460`, `packages/core/src/nexuswiki_core/wiki_write_policy.py:51-55`). 회귀 테스트 `test_risk_policy.py:449`, `:473`. 본문이 같은 개정 생성의 스펙 부합 여부는 spec-conformance r2가 별도로 다룬다. |
| 4. 위키 전체 조회의 잘림 | 해소 | 제안별 wiki_id와 workspace_id로 1행만 조회한다(`control.py:635-645`). FK로 대상 페이지의 존재를 보장하며 삭제와 조회의 경합으로 누락된 경우에는 여전히 null이다. 안정적으로 1000행 상한에 잘리는 기존 경로는 제거됐다. |
| 5. 승인 뒤 실패·취소의 비가시성 | 부분 해소, 잔여 제한 명시 | approved 전체 건수가 기간과 무관하게 보이고 적용 잡의 단계 라벨이 추가됐다(`0034:54-56`, `apps/dashboard/components/ControlRoom.tsx:644-647`, `apps/api/src/api/routers/jobs.py:38`). 취소된 잡의 자동 복구가 없다는 제한을 design.md:53에 명시했다. 이번 변경이 복구를 완료했다고 판단하지 않는다. |
| 6. 표시 모드와 실제 모드 불일치 | 부분 해소 | API 로컬 설정을 표시하고 worker 로컬 설정으로 분기하는 구조가 그대로다(`control.py:662`, `compile.py:280`). `.env.sample:94`에는 이미 두 서비스에 같은 값을 두라는 안내가 있다. 그러나 표시상의 한계와 불일치 자동 탐지 부재, stack 설정 참조 안내가 빠져 있다. 아래 조치 1. |

## 조치가 필요한 항목

1. **서로 다른 서비스의 설정을 같은 실제 쓰기 모드로 오인하게 하는 배포 안내 부족** (심각도: 보통)
   - 위치: `apps/api/src/api/routers/control.py:662`, `apps/worker/src/worker/handlers/compile.py:280`, `.env.sample:94-95`, `docs/reference/stack.md:50`
   - 깨지는 것: 화면의 `write_mode`는 API 환경변수이고 실제 보류 여부는 worker 환경변수다. API만 enforce로 올리면 화면은 승인 보류라고 표시하지만 worker는 기본 shadow로 검증 페이지를 계속 덮어쓴다. `.env.sample:94`의 같은 값 설정 안내만으로는 화면이 worker의 실제 값을 관측하지 않으며 불일치도 자동 탐지하지 않는다는 점이 드러나지 않는다. 운영 설정 참조인 stack에도 두 서비스 동시 설정 안내가 없다. `design.md:52`의 위험 기록은 배포 설정 안내를 대신하지 않는다.
   - 조치: `.env.sample`의 기존 같은 값 설정 안내에 표시상의 한계와 불일치 자동 탐지 부재를 보완하고, `docs/reference/stack.md`의 설정 안내에 API·worker 모두 같은 값으로 배포해야 함을 명시한다. 기본값 shadow는 유지한다. 실제 worker 모드를 조회하는 개선은 이 최소 수정의 필수 조건으로 요구하지 않는다.

## 검증 범위와 한계

- 이번 리뷰에서는 코드·마이그레이션·기존 테스트와 r1 수정 diff를 읽었고, 공유 DB 큐 충돌을 피하기 위해 별도의 테스트 프로세스나 DB 쓰기를 실행하지 않았다.
- 호출자가 새로 실행한 전체 pytest는 1,074 passed / 1 failed다. 실패는 Step 4 diff 밖의 `apps/api/tests/test_sources_router.py::test_cross_tenant_ingest_is_forbidden_with_a_fixed_body[file]`이며 단독 재현됐다. 로컬 Storage는 RLS의 42501을 HTTP 400으로 반환하고 기존 API가 502로 매핑한다. 이는 전체 검증 완료를 막는 실제 실패이며, 이 리뷰의 Step 4 코드 경계 판정과 구분한다.
- 호출자가 실행한 Vitest는 워커 2개로 79개 파일 / 473개 테스트 통과, TypeScript·ESLint·Ruff·OpenSpec strict validation도 통과했다. 이 결과를 리뷰어가 독립 실행한 것으로 표시하지 않는다.
- 로컬 DB reset으로 0034까지 적용됐다는 호출자 결과를 확인했다. 운영 `migration list --linked`는 링크 부재로 실패했고, 문서의 프로젝트에 연결하려는 시도도 계정 접근 권한 부족으로 실패했다. 운영 적용 확인이나 배포 준비 완료를 주장하지 않는다.

## 판정 근거

신규 테넌트 경계, JWT 사용, 역할 검사, 복합 FK, 승인·잡 등록 원자성에서 위반을 찾지 못했다. r1의 임베딩 갱신과 applied 재실행 체인 문제도 수정됐다. 그러나 모드 불일치에 대한 배포 안내가 불완전해, 실제로 승인 보류하지 않는 worker를 화면만 보고 enforce로 오인할 수 있다. 테넌트 경계를 넘는 결함은 아니고 범위 안의 문서 수정으로 해결할 수 있으므로 `needs_fix`다. r3에서 수정과 남은 필수 검증 결과를 확인해야 한다.

### 사실관계 정정

최초 보고서는 `.env.sample`에도 같은 값 설정 안내가 없다고 잘못 적었다. 검토 대상 `fb34a5e`의 94행에는 해당 안내가 이미 있었다. 위 표와 조치 항목은 이 사실을 반영해 표시 한계·자동 탐지 부재·stack 안내 부족으로 정정했다. 이후 문서 보완의 통과 여부는 r3에서 판정한다.
