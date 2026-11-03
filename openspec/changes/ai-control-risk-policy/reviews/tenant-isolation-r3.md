# Tenant Isolation 리뷰 — ai-control-risk-policy r3

- 판정: pass
- 대상: `git diff origin/main...HEAD` (`fb34a5e`)와 r2 이후 `.env.sample`, `docs/reference/stack.md`, `compile.py`, `wiki_proposal_apply.py`, `test_risk_policy.py` 작업 트리 수정
- 일시: 2026-11-02T23:58:59Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 승인·거부는 요청자 JWT의 `_user_db(...).rpc`이며 리스크 탭도 같은 경계다(`apps/api/src/api/routers/wiki.py:437`, `apps/api/src/api/routers/control.py:615`). r2 이후 사용자 DB 경로 변경 없음. |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | 개정·제안 테이블 생성과 RLS 활성화가 `0033`의 동일 트랜잭션 안에 있다(`supabase/migrations/0033_wiki_write_control.sql:12`, `:39`, `:84`, `:205`). |
| A-3 | anon 신규 GRANT·정책 | 통과 | 신규 테이블은 public·anon 권한을 회수하고 authenticated SELECT만 허용한다(`0033:45-47`, `:91-93`). 신규 RPC의 public·anon 실행도 회수한다(`0033:133-138`, `:198-201`, `supabase/migrations/0034_control_risk_tab.sql:76-79`). |
| A-4 | 워커의 workspace_id 명시 필터 | 통과 | 신규 헬퍼는 workspace_id를 필수로 받아 조회·쓰기·RPC 인자에 적용한다(`apps/worker/src/worker/db/service.py:455-536`). 적용 핸들러도 잡의 workspace_id를 모든 테이블 작업에 전달한다(`apps/worker/src/worker/handlers/wiki_proposal_apply.py:52`, `:68`, `:77`, `:96`, `:108`, `:114`, `:119`). |
| A-5 | 복합 FK | 통과 | 개정의 wiki_id와 제안의 wiki_id·raw_source_id는 workspace_id를 포함한 복합 FK다(`0033:31-33`, `:68-73`). 근거 청크는 기존 `replace_wiki_page_evidence`가 워크스페이스·원문을 재검증한다. |
| B-6 | 0행 오류 매핑 | 통과 | 승인 RPC의 역할 검사가 UPDATE보다 먼저이며 UPDATE는 workspace_id·pending으로 제한된다(`0033:156-170`). 없는 제안·처리된 제안·타 테넌트 제안은 동일한 409다(`wiki.py:446`). 리스크 RPC 빈 결과는 403이다(`control.py:620`). RLS 거부를 성공으로 반환하는 신규 경로 없음. |
| B-7 | 42501 → 403 | 통과 | 신규 RPC는 역할 거부에 42501을 사용하고 기존 핸들러가 403으로 렌더한다(`0033:157`, `0034:38`, `apps/api/src/api/errors.py:262`). 실제 경계 테스트 `apps/api/tests/test_wiki_proposals.py:100`, `:128`. 기존 Storage 오류 매핑 회귀는 별도 change로 분리되어 수정·리뷰됐다. |
| C-8 | 핸들러 멱등성 | 통과 | 개정 유니크 키와 ignore-duplicates가 최초 이전 본문을 유지한다(`0033:30`, `service.py:469-476`). applied 재실행은 본문을 다시 쓰지 않고 체인을 복구한다(`wiki_proposal_apply.py:57-65`). 본문 동일 시 개정을 생략해도 승인 상태 전이·색인·체인은 유지된다(`:74-89`, `:107-126`). |
| C-9 | jobs 직접 UPDATE | 통과 | 승인 RPC는 잡 INSERT만 하고(`0033:179`), 핸들러는 `complete_job_and_chain`을 사용한다(`wiki_proposal_apply.py:54`, `:60`, `:122`). 승인과 잡 등록은 한 RPC 트랜잭션이다. |
| D-10 | iterative_scan | 해당 없음 | 벡터 검색 SQL 변경 없음. 변경된 임베딩 대상 선정은 저장 본문과 새 본문을 비교한다(`apps/worker/src/worker/handlers/embed.py:75-87`). |
| D-11 | 토크나이저 일치 | 통과 | 승인 적용은 기존 컴파일과 같은 `bigram(normalize(content))` 및 `TSV_TOKENIZER_VERSION`을 사용한다(`wiki_proposal_apply.py:107-112`, `apps/worker/src/worker/handlers/compile.py:493-498`). |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 생성 컬럼 전환 없음. |
| D-13 | str.format | 통과 | 변경된 정책·프롬프트 조립 경로에 str.format 사용이 없다. 정책은 요청 메시지 경계에서 주입된다(`apps/worker/src/worker/llm.py:203`, `:383`). |
| D-14 | 인용 앵커 | 통과 | 분쟁 표시는 기존 위키 별칭 앵커 뒤에 붙으며 앵커 발급 구조와 원문 근거 구간을 변경하지 않는다(`apps/api/src/api/services/ask.py:462-464`). |
| E-15 | 마이그레이션 번호 | 통과(운영 확인 별도) | 최신 origin/main 최대 0031 뒤에 신규 0032~0034가 온다. 운영 적용 여부는 권한 제한으로 확인되지 않았고 이 pass가 적용 완료를 의미하지 않는다. |

## 이전 라운드 조치 재확인

- **표시 모드와 실제 모드:** `.env.sample:94-96`과 `docs/reference/stack.md:50-52`에 API·worker 동시 설정, API 값 표시와 worker 실제 동작의 구분, 불일치 자동 탐지 부재가 모두 명시됐다. r2의 문서 보완 요구를 충족한다. API와 worker 기본값은 계속 shadow다(`apps/api/src/api/settings.py:79`, `apps/worker/src/worker/settings.py:126`).
- **메타데이터 변경:** protected page의 메타데이터 변경은 계속 enforce 제안으로 보류한다(`compile.py:433-458`). shadow와 승인 적용의 개정 INSERT는 본문 차이로 별도 제한되어 동일 본문의 불필요한 이력이 생기지 않는다(`compile.py:459-475`, `wiki_proposal_apply.py:74-89`). 회귀 테스트 `apps/worker/tests/test_risk_policy.py:473`, `:489`, `:499`.
- **적용 뒤 체인과 벡터 갱신:** applied 재실행의 link_sync 복구와 chunk_content 비교 재임베딩을 유지한다(`wiki_proposal_apply.py:57-65`, `embed.py:75-104`). 회귀 테스트 `test_risk_policy.py:432`, `:581`, `:589`.
- **리스크 조회와 승인 상태:** 제안별 id·workspace_id 조회로 전체 위키 조회의 잘림을 제거했고(`control.py:635-645`), approved 건수는 기간과 무관하게 표시한다(`0034:54-56`, `apps/dashboard/components/ControlRoom.tsx:644-647`). 취소된 적용 잡의 자동 복구가 없다는 제한은 `design.md:53`에 남아 있으며 이번 리뷰가 복구 기능의 존재를 주장하지 않는다.
- **권한·재실행:** 제안 접근 제한, viewer 본문 비공개, 동일 잡 개정 1건의 저장소 테스트가 유지된다(`apps/api/tests/test_wiki_proposals.py:100`, `:128`, `:217`, `:286`). 새 수정은 이 경계를 완화하지 않는다.

## 조치가 필요한 항목

없음.

## 검증 범위와 한계

- 리뷰어는 r2 전체 경계와 r3 수정 diff·계약·회귀 테스트를 정적으로 재확인했다. 공유 큐 충돌을 피하기 위해 DB·큐 테스트나 코드 수정을 수행하지 않았다.
- 호출자가 새로 실행한 전체 pytest 결과는 **1,092 passed / 1 skipped**다. 건너뛴 항목은 작업 트리가 수정된 상태에서 실행하지 않는 쇼케이스 증거 최신성 검사이며, 증거 재측정·커밋 후 확인이 남아 있다. skip을 통과로 표시하지 않는다.
- 호출자가 실행한 Vitest 473개, TypeScript·ESLint·Ruff·OpenSpec strict validation과 로컬 `supabase/tests/wiki_write_control.sql`은 통과했다. 리뷰어의 독립 실행 결과로 표시하지 않는다.
- 운영 `supabase migration list --linked` 확인은 프로젝트 연결 부재와 이후 계정 접근 권한 오류로 완료되지 않았다. 0032~0034의 운영 적용 확인, 운영 DB 쓰기, 머지 승인을 이 보고서가 대신하지 않는다.

## 판정 근거

r2의 배포 안내 부족이 해소됐고, 본문 동일 개정 생성을 막는 수정이 테넌트 필터·승인 보류·at-least-once 재실행·후속 색인 갱신을 유지한다. r1의 주요 조용한 실패 수정도 유지되며 신규 격리 위반을 찾지 못했다. tenant-isolation 최종 3라운드를 `pass`로 판정한다. 증거 최신성 후속 검증과 운영 마이그레이션 적용 확인은 별도 완료 조건으로 남는다.
