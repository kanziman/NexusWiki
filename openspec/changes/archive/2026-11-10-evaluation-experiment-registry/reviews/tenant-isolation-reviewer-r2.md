# Tenant Isolation 리뷰 — evaluation-experiment-registry r2

- 판정: pass
- 대상: `git diff main...HEAD` (`9d59cdc718b4e38da7076b12b9bf2a6655d9be05`). 이번 라운드의 중점은 r1 이후 수정 커밋 `9d59cdc`
- 일시: 2026-11-10T13:39:51Z

## 실측 근거

- 경계 테스트 `supabase/tests/0037_eval_experiments.sql`을 로컬 DB에서 실행했다. 마지막 출력은 `0037 eval_experiments: ok` / `ROLLBACK`, 종료 코드 0. 새로 추가된 블록(출처 시각 null이면 preregistered null, 출처 없는 채점 검증 거부, anon·authenticated TRUNCATE 거부)이 모두 통과했다
- 로컬 DB 카탈로그 조회(읽기 전용)
  - 네 테이블 모두 `relrowsecurity = t`, `pg_policies` 0행
  - `relacl`은 `postgres`와 `service_role`만 있다. `information_schema.role_table_grants`에 `anon`·`authenticated`·`public` 권한 0건
  - `eval_criteria_sets.source_commit`·`source_first_commit_at`·`preregistered`가 모두 `is_nullable = YES`다. 로컬 DB에 수정된 0037이 반영되어 있다
  - `supabase_migrations.schema_migrations` 최대 버전 `0037`
- 혼합 null 탐침(`begin … rollback`, `service_role`): `source_commit = null`, `source_first_commit_at = '2026-01-01'`, `earliest_run_at = '2026-11-09'`인 행을 넣으니 DB가 받아들였고 `preregistered = t`가 됐다. 아래 참고 1을 보라
- `.venv/bin/python -m pytest -q apps/worker/tests/test_eval_experiment_registry.py apps/worker/tests/test_local_evaluation_server.py`: 34 passed

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `9d59cdc`는 DB 접근 경로를 늘리지 않았다. `service_role`은 여전히 로컬 CLI `scripts/eval_experiments.py`의 `upsert_sql`·`select_sql`(`set local role service_role`) 안에서만 쓰이고, 이 CLI는 `docker exec` psql로만 접속한다. 대시보드 변경(`RegressionDashboard.tsx`, `lib/experiments.ts`, `content/experiments.json`)은 정적 스냅샷의 타입과 표시만 바꿨다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | 열 추가·null 허용은 같은 `0037` 트랜잭션 안의 `create table`에서 일어난다(`0037_eval_experiments.sql:35-82`). RLS 활성화(105-108행)는 그대로다 |
| A-3 | anon 신규 GRANT·정책 | 통과 | 권한·RLS 구문(105-118행)은 바뀌지 않았다. 카탈로그에 anon·authenticated 권한이 없다. r1 참고 1을 반영해 TRUNCATE 거부를 직접 검사하게 됐다(테스트 anon `truncate public.eval_decisions`, authenticated `truncate public.eval_experiments cascade` 모두 `insufficient_privilege`). 두 테이블만 표본으로 검사하지만, `revoke all`이 네 테이블을 한 구문으로 회수하므로 회수 범위가 좁혀지면 이 블록이 먼저 깨진다 |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | 네 테이블은 `workspace_id`가 없는 프로젝트 전역 운영 기록이다(design.md D2). 새 `reference` 열은 계약 문서 경로다. 스냅샷 허용 목록(`ALLOWED["experiments"]`)에 `reference`만 더해졌고 `FORBIDDEN` 검사는 그대로다. 채점 검증 행은 `public = false`라 스냅샷에 들어가지 않는다 |
| A-5 | 자식 테이블 복합 FK `(id, workspace_id)` | 해당 없음 | 테넌트 자식 테이블 없음. 복합 FK 구조(96-99행)는 바뀌지 않았다 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 테이블을 사용자 JWT로 UPDATE/DELETE하는 API가 없다. 권한이 없어 0행이 아니라 `42501`이 난다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 이 테이블을 호출하는 사용자 API가 없다 |
| C-8 | 핸들러 멱등성·upsert 키 | 통과 | 작업 큐 핸들러가 아니다. 등록은 그대로 PK 기준 `on conflict do update`다. 새 `reference` 열은 등록 행의 키에서 열 목록을 만들기 때문에 upsert 갱신 대상에 자동으로 포함된다. 세 실험 행 모두 `reference` 키를 갖고 있어(`LOCAL_EXPERIMENT`, `research_records`, `reliability_records`) 행마다 열 목록이 같다. `validate_run_refs`(`eval_experiments.py:354-360`)는 upsert SQL을 만들기 전 `build_records` 안에서 실행되므로, 없는 실행을 가리키면 DB에 아무것도 쓰지 않고 멈춘다. 출처 커밋을 못 찾은 경우의 null은 `git log` 결과에서 결정적으로 나오므로 재실행해도 같은 값이다 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 참조 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 색인·질의 변경 없음 |
| D-12 | search_tsv 생성 컬럼화 | 해당 없음 | `search_tsv` 변경 없음. 생성 열 `preregistered`의 식(45행)은 그대로다 |
| D-13 | 프롬프트 템플릿 str.format | 해당 없음 | 프롬프트 템플릿 변경 없음 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 순서 | 통과 | `main` 최대 번호는 `0036_control_quality_measured.sql`, 이 브랜치 신규는 `0037` 하나다. `0037`을 제자리에서 고쳤지만, 0037은 아직 클라우드에 push되지 않았다(11-12행 주석, change 밖 결정). 그러므로 이미 적용된 번호를 고친 것이 아니다. 로컬 DB는 수정본으로 다시 적용되어 있다 |

### 사전 등록 여부가 조용히 참이 되는 경로 점검

호출자가 요청한 중점 항목이다. 결론은 **등록 스크립트와 화면 경로에는 그런 경로가 없다**는 것이다. DB 제약에만 틈이 하나 있다(참고 1).

- **DB 식**: `source_first_commit_at < earliest_run_at`에서 앞 값이 null이면 결과도 null이다. `earliest_run_at`은 `not null`로 남아 있다. 경계 테스트가 null을 직접 확인한다
- **출처 시각을 지어내지 않음**: `git_first_commit`(`eval_experiments.py:148-166`)은 `git log --reverse`의 첫 줄만 쓰고, 못 찾으면 `(None, None)`을 함께 돌려준다. 해시와 시각은 늘 같이 채워지거나 같이 비어 있다. 결정 날짜(`decided_at`)는 null이면 등록을 멈춘다(232-237행). 날짜를 대신 만들어 넣지 않는다
- **얕은 클론**: `git log`의 첫 커밋이 얕은 경계로 잘려도, 그 시각은 실제 첫 커밋보다 늦다. 그래서 오판이 나도 `false` 방향(사전 등록 아님)이다. 참으로 잘못 뒤집히지는 않는다
- **내보내기**: `build_snapshot`(496-501행)은 null을 `utc()`에 넣지 않고 그대로 null로 옮긴다. `preregistered`는 DB 값을 그대로 쓴다. 파이썬이 다시 계산하지 않는다
- **화면**: `RegressionDashboard.tsx:490-506`은 `=== true`일 때만 "사전 등록"을 표시한다. null이면 "기록 시점을 확인할 수 없음 · 사전 등록으로 표시하지 않음"이 나온다. `preregistered`를 참·거짓으로 판단하는 다른 소비자는 없다(`lib/regression-policy.ts`·`regression-data.ts`·`regression-analysis.ts`에 참조 없음). 현재 커밋된 스냅샷은 `preregistered: false`, `source_commit: "0f9bbbe"`다

## 조치가 필요한 항목

없음. 판정에는 영향이 없는 참고 사항만 적는다.

1. **해시와 출처 시각이 함께 null이어야 한다는 규칙을 DB가 강제하지 않는다** (심각도: 참고)
   - 위치: `supabase/migrations/0037_eval_experiments.sql:40-41`
   - 내용: r1에서는 두 열이 모두 `not null`이었다. 그래서 `preregistered = true`인 행에는 늘 커밋 해시가 함께 있었다. 이번 수정으로 각 열이 따로 null을 허용하게 됐다. 그 결과 `source_commit = null`이면서 `source_first_commit_at`만 채운 행을 DB가 받아들인다. 이 행은 `preregistered = t`가 된다(탐침으로 확인). 이런 행이 스냅샷에 실리면 화면에 "사전 등록 · 실행 전에 기록됨"과 "기준 출처의 커밋 기록 없음"이 함께 표시된다. 커밋 근거 없이 사전 등록으로 보이는 것이다
   - 판정 영향이 없는 이유: 이 테이블에 쓸 수 있는 역할은 `service_role`뿐이다. 유일한 작성 경로인 `git_first_commit`은 두 값을 늘 짝으로 돌려준다. 게다가 r1에서도 DB는 해시 형식만 검사했고, 시각이 git 이력과 맞는지는 검증하지 않았다. 손으로 시각을 지어내는 위협은 이번 수정 전에도 있었다. 테넌트 경계와도 무관하다
   - 제안: 다음에 0037을 손볼 때 `check ((source_commit is null) = (source_first_commit_at is null))`를 더하고, 경계 테스트에 혼합 null 거부 블록을 하나 둔다
2. **r1 참고 2(등록은 upsert만 하고 사라진 행을 지우지 않음)는 그대로다** (심각도: 참고)
   - 위치: `scripts/eval_experiments.py:363-385`
   - 내용: 이번 `validate_run_refs`는 등록하려는 행만 검사한다. 이미 DB에 남은 `local-grader-check` 행의 옛 실행 id는 검사하지 않는다. `public = false`이고 `run_identity`가 `local` 출처를 거부하므로 공개 스냅샷으로 새지는 않는다. 격리 문제는 아니다

## 판정 근거

`9d59cdc`는 권한·RLS 구문을 바꾸지 않았다. 경계 테스트 재실행과 카탈로그 조회로 anon·authenticated의 권한이 0건이고 정책이 0개임을 다시 확인했다. TRUNCATE 거부를 직접 검사하게 되어 r1의 참고 1도 해소됐다. null 허용 변경은 등록 스크립트·내보내기·화면 어디에서도 사전 등록 여부를 참으로 만들지 않는다. null은 끝까지 "확인 불가"로 전달되고, 얕은 클론에서 오판이 나도 거짓 방향이다. 새 실행 id 대조는 DB에 쓰기 전에 멈추므로 멱등성을 해치지 않는다. 남은 틈은 해시·시각 짝을 강제하지 않는 DB 제약 하나다. 이 틈은 `service_role`의 수동 쓰기로만 열리고 테넌트 경계와 무관하므로 참고로 남긴다. 테넌트 경계를 넘거나 데이터가 조용히 손상되는 경로를 찾지 못했으므로 `pass`로 판정한다.
