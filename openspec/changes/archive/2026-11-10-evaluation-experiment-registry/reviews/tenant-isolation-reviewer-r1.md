# Tenant Isolation 리뷰 — evaluation-experiment-registry r1

- 판정: pass
- 대상: `git diff 5031820..HEAD` (`2a5df567e3d55c69e0c10df02ef5720afd92e4db`, 구현 커밋 1578862 · c1317a4 · 61381e0 · 2a5df56)
- 일시: 2026-11-10T13:32:11Z

## 실측 근거

- 경계 테스트 `supabase/tests/0037_eval_experiments.sql`을 로컬 DB에서 실행함. 마지막 출력은 `0037 eval_experiments: ok` / `ROLLBACK`
- 로컬 DB 카탈로그 조회(읽기 전용):
  - 네 테이블 모두 `relrowsecurity = t`, `pg_policies`에 행 없음
  - `information_schema.role_table_grants`에 `anon`·`authenticated` 권한 0건. `postgres` 기본 ACL이 `public` 스키마 새 테이블에 `anon`/`authenticated`로 `Dxtm`(TRUNCATE 포함)을 주는데, `revoke all`이 이것까지 회수했다. TRUNCATE는 RLS를 우회하므로 이 회수가 실제로 효과가 있다
  - `supabase_migrations.schema_migrations` 최신 버전은 `0037`
- `.venv/bin/python -m pytest apps/worker/tests/test_eval_experiment_registry.py apps/worker/tests/test_local_evaluation_server.py`: 31 passed

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `service_role`은 로컬 CLI `scripts/eval_experiments.py:350,379`의 `set local role service_role` 하나뿐이다. 이 스크립트는 `docker exec` psql로만 접속하고 HTTP 경로가 없다. 대시보드는 `apps/dashboard/lib/experiments.ts:1`, `app/showcase/regression/experiments.json/route.ts:1`에서 커밋된 `content/experiments.json`을 정적 import만 하고 DB·Supabase 클라이언트를 쓰지 않는다(`force-static`) |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `0037_eval_experiments.sql:15-114`의 한 트랜잭션 안에서 네 테이블 생성(20·35·53·81행)과 `enable row level security`(99-102행)가 함께 일어난다. 정책 없는 창이 열리지 않는다 |
| A-3 | anon 신규 GRANT·정책 | 통과 | 정책 0개, `revoke all ... from anon, authenticated`(105-107행). 테스트 136-152행에서 anon의 SELECT·INSERT가 `insufficient_privilege`로 막히는 것을 확인했다. 공개 화면은 DB를 거치지 않으므로 `0016` 공개 경로 외의 anon 노출이 없다 |
| A-4 | service_role 코드의 workspace_id 필터 | 해당 없음 | 네 테이블은 설계상 `workspace_id`가 없는 프로젝트 전역 운영 기록이다(design.md D2). 스크립트가 읽고 쓰는 테이블은 `TABLES`(`eval_experiments.py:72-77`)의 네 개뿐이고 테넌트 테이블은 건드리지 않는다. 스냅샷 `FORBIDDEN`(121행)이 `workspace_id`·`user_id`·`email`·`answer`·`response_text`·`token`·`api_key`를, `ALLOWED`(80-120행)가 허용 목록 밖 필드를 거부한다. 현재 `content/experiments.json`에 workspace·user·email 문자열 없음 |
| A-5 | 자식 테이블 복합 FK `(id, workspace_id)` | 해당 없음 | 테넌트 자식 테이블이 없다. `eval_decisions`의 복합 FK `(experiment_id, experiment_kind)`·`(experiment_id, criteria_set_id)`(90-93행)는 종류·기준 세트 무결성용이며, 테스트 59-123행이 위반 5가지를 확인한다 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 테이블을 사용자 JWT로 UPDATE/DELETE하는 API가 없다. 정책이 아니라 권한으로 막혀 있어 `authenticated`의 UPDATE는 0행이 아니라 `42501`을 던진다(테스트 168-173행). 그래서 "0행인데 성공처럼 보이는" 경로가 생기지 않는다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 이 테이블을 호출하는 사용자 API가 없다. 참고로 로컬 실행기의 같은 이름 거절(`scripts/local_evaluation_server.py:213-216` `Conflict` → 370-371행 409)은 5031820 이전 코드(590e7c6)이고, 이번 diff에는 테스트(`test_local_evaluation_server.py:196-216`)만 추가됐다. 인증 실패는 403, 운영 빌드 프록시는 `app/api/local-evaluation/route.ts:8-23`에서 403으로 거부한다(이번 diff 밖 코드) |
| C-8 | 핸들러 멱등성·upsert 키 | 통과 | 작업 큐 핸들러가 아니라서 세 upsert 키는 해당이 없다. 등록은 테이블마다 PK에 대해 `on conflict (<pk>) do update`를 쓴다(`eval_experiments.py:363-368`). FK 순서(정책 → 기준 세트 → 실험 → 결정)로 한 트랜잭션에서 돌아가므로, 다시 실행해도 같은 행이 된다. 생성 열 `preregistered`와 `experiment_kind`는 삽입 열에 없어서 DB가 값을 정한다. 내보내기는 `order by <pk>` + `sort_keys`라 결정적이다 |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 참조 없음 |
| D-10 | hnsw.iterative_scan | 해당 없음 | 벡터 검색 변경 없음 |
| D-11 | 토크나이저 일치 | 해당 없음 | 색인·질의 변경 없음 |
| D-12 | search_tsv 생성 컬럼화 | 해당 없음 | `search_tsv` 변경 없음. 새 생성 열은 `eval_criteria_sets.preregistered`(43행)뿐이며 검색과 무관하다 |
| D-13 | 프롬프트 템플릿 str.format | 해당 없음 | 프롬프트 템플릿 변경 없음. `eval_experiments.py`의 f-string은 SQL·문구 조립용이다. SQL 값은 달러 인용 JSON으로만 넘기고, 태그 충돌은 356-358행에서 다시 뽑는다 |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립 변경 없음 |
| E-15 | 마이그레이션 번호 순서 | 통과 | `main`의 최대 번호는 `0036_control_quality_measured.sql`, 신규는 `0037`. 앞선 번호 끼워넣기 없음. 클라우드 적용은 이 change 밖에서 결정한다는 주석이 있다(11-12행) |

## 조치가 필요한 항목

없음. 판정에는 영향이 없는 참고 사항만 적는다.

1. **경계 테스트가 TRUNCATE를 직접 검사하지 않는다** (심각도: 참고)
   - 위치: `supabase/tests/0037_eval_experiments.sql:135-174`
   - 내용: `public` 스키마 기본 ACL은 `anon`/`authenticated`에 TRUNCATE를 준다. TRUNCATE는 RLS를 우회한다. 지금은 `revoke all`이 이것까지 회수한 것을 카탈로그로 확인했다. 다만 나중에 `revoke all`을 `revoke select, insert, update, delete`로 좁히면 테스트가 이를 잡지 못한다
   - 제안: 다음에 손볼 때 anon/authenticated의 `truncate public.eval_decisions`가 `insufficient_privilege`인지 확인하는 블록을 하나 추가한다
2. **등록은 upsert만 하고 사라진 행을 지우지 않는다** (심각도: 참고)
   - 위치: `scripts/eval_experiments.py:348-370`
   - 내용: 로컬 실행 디렉터리가 사라지면 `local-grader-check` 행이 DB에 옛 실행 id로 남는다. `public = false`이고 `run_identity`가 `local` 출처를 거부하므로(433행) 공개 스냅샷으로 새지는 않는다. 격리 문제는 아니다

## 판정 근거

새 테이블 네 개는 같은 트랜잭션에서 RLS를 켜고, 정책 없이 `anon`·`authenticated` 권한을 모두 회수하고, `service_role`에만 권한을 준다. 이 상태를 경계 테스트 실행과 카탈로그 조회로 직접 확인했다. `service_role`은 HTTP 경로가 없는 로컬 CLI 안에서만 쓰이고, 그 CLI는 테넌트 테이블을 건드리지 않는다. 공개 화면과 다운로드 라우트는 커밋된 정적 스냅샷만 읽는다. 사용자 JWT로 이 테이블에 닿는 API가 없어 B 항목의 0행·42501 매핑은 해당이 없다. 멱등성과 번호 순서도 지켜졌다. 테넌트 경계를 넘거나 데이터가 조용히 손상되는 경로를 찾지 못했으므로 `pass`로 판정한다.
