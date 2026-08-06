# 마이그레이션 0007 적용 기록

`docs/ops/cloud-bootstrap-record.md`(Phase 1의 `0001`~`0006` push 기록)를 이어 쓴 문서다.
`0007`은 그 기록이 "이후 마이그레이션은 `0007` 이상만 추가한다"고 남긴 다음 번호다.

## 적용 일시

- 로컬 `db reset` 재확인: 2026-08-07 (UTC 2026-08-06T15:35Z)
- 클라우드 `db push`: 2026-08-07 KST
- 대상 커밋: `b5ba33e` (마이그레이션 저술), 적용 시점 HEAD `3e52cbe`
- 대상 프로젝트: Supabase `dajhhwbkfdaqnuenulsb` / 리전 `ap-southeast-1` / 상태 `ACTIVE_HEALTHY` / Postgres 17.6.1.155

## 로컬

### 방법

- `supabase db reset --no-seed`를 두 번 돌렸다. 한 번은 `0007` 저술 직후, 한 번은 push 직전에 다시.
  두 번째 실행의 의미는 "빈 DB에서 `0001`부터 순서대로 다시 세워도 `0007`이 적용되는가"이며,
  `0007`이 그 앞 여섯 개의 산출물(특히 `0002`의 두 `smallint` 컬럼과 `0003`의 `jobs`)에 의존하기 때문에 필요하다.
- 큐 함수 계약 테스트를 reset된 스키마 위에서 재실행했다.
  `docker exec -i supabase_db_NexusWiki psql -U postgres -d postgres -v ON_ERROR_STOP=1 < supabase/tests/0007_queue_functions.sql`
- 스키마 객체·컬럼 타입·권한은 `information_schema`와 `pg_catalog`를 직접 조회해 확인했다.

### 결과

- `supabase db reset`이 `0001` → `0002` → `0003` → `0004` → `0005` → `0006` → `0007` 순서로 오류 없이 적용됐다. pass.
- 큐 계약 테스트 종료 코드 `0`, 출력 `queue_functions: ok`. 네 계약(attempts 되돌림 · 락 소유자 술어 ·
  상태 술어 · `complete_job_and_chain` 원자성) 전부 통과. 테스트가 `rollback`으로 끝나므로 잔여 행 `0`. pass.
- `complete_job_and_chain` · `release_job` · `search_chunks` 세 함수 존재. pass.
- `jobs_dedup_idx` 존재. pass.
- `tsv_tokenizer_version` 컬럼 중 `text` 2개 / `smallint` 0개. pass.
- `wiki_pages`에 `verified_by` · `verified_at` · `expires_at` 3개 컬럼 존재. pass.
- `source_chunks.embedding_version` · `source_chunks.chunker_version` · `wiki_embeddings.embedding_version` 존재. pass.
- 파일 첫 비주석 행 `begin;`, 마지막 비주석 행 `commit;`. 번호 섹션 8개. 대문자 SQL 키워드 0건. pass.
- `git diff --name-only supabase/migrations/0002_search_schema.sql` 빈 출력 — 섹션 7이 `0002`를 소급 수정하지 않았다. pass.
- Python 회귀: `uv run pytest -q` 88 passed, `uv run ruff check apps packages` 통과. pass.

## 클라우드

### 방법

- `supabase projects list`가 대화형 프롬프트 없이 응답하는 것을 먼저 확인했다(저장된 CLI 세션 사용,
  `SUPABASE_ACCESS_TOKEN` 환경변수는 설정되어 있지 않다).
- push **직전에** `supabase migration list --linked`로 원격 원장이 `0001`~`0006`이고 `0007`이 없음을 확인했다.
- `supabase db push --linked`로 적용한 뒤 같은 명령으로 다시 대조하고, 원격 스키마를
  `supabase db query --linked`로 직접 조회했다.

### 결과

`supabase db push --linked` 출력: `{"upToDate":false,"dryRun":false,"migrations":["0007_search_and_queue_extensions.sql"],...}`.
적용된 마이그레이션은 `0007` 하나뿐이며 부분 적용의 흔적은 없다 — 파일 전체가 단일 트랜잭션이므로
부분 적용이 애초에 불가능하다.

#### `migration list` 로컬/원격 대조표

| Local | Remote | 일치 |
|---|---|---|
| 0001 | 0001 | ✅ |
| 0002 | 0002 | ✅ |
| 0003 | 0003 | ✅ |
| 0004 | 0004 | ✅ |
| 0005 | 0005 | ✅ |
| 0006 | 0006 | ✅ |
| 0007 | 0007 | ✅ |

어긋나는 행은 하나도 없다. push 직전 표에서 `0007` 행의 Remote 열만 비어 있었고, push 후 채워졌다.
02-SPEC.md R7이 요구하는 것은 push의 성공이 아니라 **이 두 열의 일치**이며 그 조건이 충족됐다.

#### 원격 스키마 직접 조회

| 확인 항목 | 실제 반환값 | 판정 |
|---|---|---|
| 새 함수 존재 | `complete_job_and_chain,release_job,search_chunks` | pass |
| `tsv_tokenizer_version` 타입 | `text` 2개 / `smallint` 0개 | pass |
| `jobs_dedup_idx` | `jobs_dedup_idx` | pass |
| `anon` 테이블 권한 | 행 없음 (0건) | pass |
| `authenticated` 테이블 권한 | 23건 | pass |
| `service_role` 테이블 권한 | 25건 | pass |

권한 건수는 섹션 8의 매트릭스와 정확히 일치한다.
`authenticated` 23 = `workspaces` 4 + `workspace_members` 4 + `raw_sources` 3 + `wiki_pages` 4 +
`source_chunks` 1 + `wiki_embeddings` 1 + `wiki_links` 1 + `prompt_templates` 4 + `jobs` 1.
`service_role` 25 = `workspaces` 1 + `workspace_members` 1 + `raw_sources` 3 + `wiki_pages` 4 +
`source_chunks` 4 + `wiki_embeddings` 4 + `wiki_links` 4 + `prompt_templates` 1 + `jobs` 3.

`anon`이 조회 결과에 아예 나타나지 않는다는 것이 중요하다. 이전 상태에서는 세 롤 모두
`REFERENCES,TRIGGER,TRUNCATE`를 갖고 있었고, 그중 `TRUNCATE`는 RLS를 우회한다.

## 한계와 되돌리기

- **이 적용은 one-way다.** 원격 원장에 `0007`이 올라간 이상 `0007`보다 낮은 번호의 마이그레이션은
  다시는 추가할 수 없다. Phase 1이 `0005`를 `0006` **이전에** 넣어야 했던 것과 같은 제약이며,
  그 사건이 `docs/ops/cloud-bootstrap-record.md`에 기록되어 있다.
- **`0007`의 내용을 바꾸려면 `0008` 보정 마이그레이션이 필요하다.** `0007` 파일을 소급 편집하면
  로컬과 원격의 원장이 어긋나며, 그것은 이 프로젝트에서 되돌릴 방법이 없는 종류의 어긋남이다.
  섹션 7이 `0002`를 고치지 않고 앞으로 나아가는 방식으로 타입을 정정한 이유가 그대로 여기에도 적용된다.
- **되돌리기가 특히 비싼 두 지점.**
  1. 섹션 8의 권한 매트릭스를 좁히는 것은 `0008`의 `revoke` 한 줄이면 되지만, **넓히는** 방향으로
     잘못 잡았다면 그 사이에 열려 있던 창은 되돌릴 수 없다. 현재 매트릭스는 `anon` 무권한이고
     `service_role`도 열거된 동작만 가지므로 넓은 쪽으로 틀린 위험은 낮다.
  2. 섹션 7의 타입 변경은 지금 두 컬럼의 행이 0개라 무손실이었다. 되돌려 `smallint`로 가려면
     그때는 실제 데이터가 있을 것이고 `using` 절 없이는 실패한다. 사실상 편도다.
- **`0007`에 없는 것.** `wiki_pages`의 `verified` 상태에 대한 CHECK 제약을 걸지 않았다.
  `verified_by`가 `auth.users`를 `on delete set null`로 참조하므로, CHECK를 걸면 계정 삭제가
  발동시키는 `set null`이 곧바로 그 CHECK를 위반해 삭제가 `23514`로 실패한다.
  세 컬럼을 한 UPDATE로 함께 쓰는 책임은 `P2-QC-01`에 있다. 근거는 `0007` 섹션 5 주석에 있다.
- **아직 확인되지 않은 것.** 원격에서 실제 요청자 JWT로 `search_chunks`를 왕복시켜 본 적은 없다.
  로컬 스파이크(`supabase/spike/`)가 같은 형태의 함수로 그것을 확인했고 원격은 스키마 동일성만
  확인했다. 실제 왕복은 라우터가 서는 02-04와 검색 경로가 서는 Phase 4에서 처음 검증된다.
