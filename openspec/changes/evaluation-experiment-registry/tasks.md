## 0. 추적

추적: umbrella https://github.com/kanziman/NexusWiki/issues/272. Gate 4 승인으로 작업 분해 확정. 하위 이슈: 1절 #273, 2절 #274, 3절 #275, 4절 #276, 5절 #277. GitHub sub-issue 연결 응답 확인 완료. 구현 전에 이 change 전용 브랜치를 만들고, 같은 파일을 건드리는 미커밋 작업(골든셋 리뷰, 이 세션의 화면 수정)을 먼저 분리한다.

## 1. 재검색 실험이 원래 기준과 출처로 판정되어 공개된다

이슈: https://github.com/kanziman/NexusWiki/issues/273

- [x] 1.1 `0037_eval_experiments.sql`(테이블 4개, RLS·권한 회수, 종류 CHECK, 측정 실험 결정 금지 복합 외래키, `preregistered` 생성 열)과 SQL 경계 테스트, 등록 스크립트(정책 v1 행, 재검색 원래 기준 세트, 재검색 실험, 미채택 결정)와 내보내기 스크립트(허용 필드, 결정적 출력), `content/experiments.json`·`/showcase/regression/experiments.json` 라우트, 재검색 화면의 공식 판정·기준 출처·두 시각·결정 기록 표시와 기준선·후보 쌍 고정을 연결한다.

AC:
Given: 로컬 DB에 `0037`이 적용되고 기존 `content/evidence-research.json`이 있다.
When: 등록과 내보내기를 실행하고 공개 빌드로 재검색 실험을 연다.
Then: 원래 기준 6개 중 답변 복구·통과 증가·비용(+66.4%) 미충족, 나머지 3개 충족, 결정 미채택이 보인다. 출처 첫 커밋(`0f9bbbe`, 11:00 KST)이 OFF 실행(08:26 KST)보다 늦어 사전 등록으로 표시되지 않는다. 맞바꾸기·실행 선택이 없고, 다운로드 JSON이 렌더링 스냅샷과 같다. `anon`·`authenticated`는 0행이며, 측정 실험 결정 삽입과 없는 실행 id 등록은 실패하고, 재등록은 행을 늘리지 않으며, 두 번 내보내면 같은 바이트다.

검증:
`docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1 < supabase/tests/0037_eval_experiments.sql && .venv/bin/python -m pytest apps/worker/tests/test_eval_experiment_registry.py -q && (cd apps/dashboard && npx vitest run tests/RegressionDashboard.test.tsx)`

## 2. 정책 v1을 읽기 전용으로 보고 참고 판정을 확인한다

이슈: https://github.com/kanziman/NexusWiki/issues/274

- [x] 2.1 `evaluatePolicy`(정책 객체에서만 기준값을 받음)와 정책 v1 전문 보기, 재검색 화면의 참고 판정 문구("정책 v1로 판정했다면 새로 실패 1개도 막는 조건"), 허용 기준 입력칸·`ReviewPanel`·기준과 메모 localStorage 읽기·쓰기 삭제, `scripts/evidence_research_eval.py` 상수 정리와 원래 기준 세트 대조 테스트를 연결한다.

AC:
Given: 스냅샷에 정책 v1과 재검색 원래 기준 세트가 있고, 브라우저 저장소에 이전 버전의 기준값·검토 메모가 남아 있다.
When: 방문자가 재검색 실험의 모든 영역을 펼친다.
Then: 정책 v1 조건 전문과 버전이 보이고 기준을 바꾸는 입력칸과 메모가 없다. 참고 판정은 공식 판정과 구분돼 보이고 공식 판정·결정은 바뀌지 않는다. 저장소 값은 판정에 영향이 없다. 정책 값을 바꾼 가짜 스냅샷에서는 판정이 따라 바뀌고, 스크립트 상수가 원래 기준 세트와 다르면 테스트가 실패한다. 통과 수가 같고 회귀가 없는 후보는 정책 v1에서 채택 가능이 아니다.

검증:
`(cd apps/dashboard && npx vitest run tests/RegressionDashboard.test.tsx tests/regression-policy.test.ts) && .venv/bin/python -m pytest apps/worker/tests/test_evidence_research_eval.py apps/worker/tests/test_eval_experiment_registry.py -q`

## 3. Ask 반복 측정이 안정성 측정으로 보인다

이슈: https://github.com/kanziman/NexusWiki/issues/275

- [x] 3.1 등록 스크립트에 Ask 반복 측정(안정성 측정, 공개, 역할 기준 반복·비교 반복)을 추가해 스냅샷에 내보내고, 화면에서 채택 배지·조건 목록·결정 기록 대신 질문별 판정 일치 수와 흔들린 질문을 보이며, 질문별 변화를 흔들림으로 부르고 측정 실험에만 실행 선택·맞바꾸기를 남긴다.

AC:
Given: 스냅샷에 Ask 반복 측정 실험이 안정성 측정으로 있다.
When: 방문자가 이 실험을 열고 다른 실행 쌍을 고른다.
Then: 채택 배지와 비용·p95 허용 조건이 없고, 고른 쌍의 판정 일치 수와 흔들린 질문이 보인다. 화면 어디에도 회귀라는 말이 쓰이지 않는다. 결정 기록을 이 실험에 등록하려 하면 DB가 거부한다.

검증:
`(cd apps/dashboard && npx vitest run tests/RegressionDashboard.test.tsx) && .venv/bin/python -m pytest apps/worker/tests/test_eval_experiment_registry.py -q`

## 4. 로컬 개발 도구가 실험과 분리되고 내 검증이 채점 검증으로 보인다

이슈: https://github.com/kanziman/NexusWiki/issues/276

- [ ] 4.1 사이드바를 「실험」과 「로컬 개발 도구」(개발 모드만: 내 검증 · 골든셋과 AI 심사)로 나누고, 실행 서랍을 내 검증 화면 맨 위에서만 렌더링하며, 다른 실험의 로컬 기록 안내를 없앤다. 로컬 재채점 실험을 비공개 채점 검증으로 등록해 스냅샷에서 제외하고, 판정 변화 수와 "채점 규칙을 바꾸지 않았다면 같은 결과가 정상" 설명을 보인다. 로컬 실행기의 같은 이름 거절(409) 경로 테스트를 추가한다.

AC:
Given: 개발 모드이고 로컬 실행기에 재채점 기록이 있다.
When: 재검색 실험 화면과 내 검증 화면을 차례로 연다.
Then: 재검색 화면에는 실행 서랍과 로컬 기록 안내가 없고, 내 검증 화면 맨 위에 서랍과 결과 카드가 있으며 채택 배지 없이 판정 변화 수가 보인다. 공개 빌드에는 로컬 개발 도구 구역이 없고, 내보낸 스냅샷에 로컬 실험이 없다. 같은 이름으로 실행을 요청하면 실행기가 409로 거절한다.

검증:
`(cd apps/dashboard && npx vitest run tests/RegressionDashboard.test.tsx tests/LocalEvaluation.test.tsx) && .venv/bin/python -m pytest apps/worker/tests/test_local_evaluation_server.py apps/worker/tests/test_eval_experiment_registry.py -q`

## 5. 리뷰 게이트·스펙 동기화·변경 마감

이슈: https://github.com/kanziman/NexusWiki/issues/277

- [ ] 5.1 관련 Python·프런트엔드 테스트, typecheck·lint·포맷, SQL 경계 테스트, `openspec validate evaluation-experiment-registry --strict`를 새로 실행하고, 데스크톱·모바일 폭에서 세 실험 화면을 확인한다. `spec-conformance-reviewer`·`tenant-isolation-reviewer`를 병렬로 돌려 pass를 받고, `docs/reference/stack.md`의 마이그레이션 표에 `0037`(로컬 검증, 운영 미적용)을 기록한 뒤 스펙 동기화와 아카이브를 브랜치에서 커밋한다.

AC:
Given: 1~4절이 모두 완료됐다.
When: 전체 검증과 리뷰 게이트를 실행한다.
Then: 모든 검증이 새 실행 결과로 통과하고 두 리뷰어가 pass이며, `openspec/specs/`에 두 capability가 생기고 change가 아카이브된다. 운영 DB에 `0037`을 적용했다고 주장하지 않는다.

검증:
`(cd apps/dashboard && npx vitest run) && (cd apps/dashboard && npx tsc --noEmit) && (cd apps/dashboard && npx eslint .) && .venv/bin/python -m pytest apps/worker/tests -q && openspec validate evaluation-experiment-registry --strict`
