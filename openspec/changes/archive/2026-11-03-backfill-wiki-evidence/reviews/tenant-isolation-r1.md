# Tenant Isolation 리뷰 — backfill-wiki-evidence r1

- 판정: pass
- 대상: `HEAD` (`c802b1c`) 기준 작업 트리 변경분 (`supabase/migrations/0035_wiki_evidence_backfill.sql`, `apps/worker/src/worker/evidence_backfill.py`, `apps/worker/tests/test_evidence_backfill.py`, `docs/ops/wiki-evidence-backfill.md`, `docs/reference/stack.md`, `.gitignore`, `openspec/changes/backfill-wiki-evidence/`)
  - 검토 범위 제외(무관한 작업 트리 변경): `docs/ref/ref0.png`, `docs/ref/ref2.png`, `skills-lock.json`
- 일시: 2026-11-03T11:13:00+09:00

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 `service_role` | 통과 | 사용자 요청 경로(`apps/api/`, `apps/dashboard/`) 변경 없음. 백필 도구는 워커 패키지 내 운영자 전용 CLI(`apps/worker/src/worker/evidence_backfill.py`)로만 진입하며, SEC-03 검사(`ci_check_service_usage: ok (301 files scanned)`)를 통과함 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | `supabase/migrations/0035_wiki_evidence_backfill.sql`은 신규 테이블을 생성하지 않고 기존 `public.wiki_page_evidence`(`0030_wiki_page_evidence.sql:40`에서 RLS 활성화 완료)를 대상으로 RPC 함수 3개만 정의함 |
| A-3 | `anon`에 새로 부여된 GRANT나 정책 | 통과 | `supabase/migrations/0035_wiki_evidence_backfill.sql:154-161`에서 `wiki_evidence_backfill_token`, `wiki_evidence_backfill_candidates`, `apply_wiki_evidence_backfill` 3개 함수 모두 `revoke all ... from public, anon, authenticated;` 후 `grant execute ... to service_role;`만 부여함 (`apps/worker/tests/test_evidence_backfill.py:451-471`에서 `anon`·`authenticated` 호출 시 401/403 거부 검증) |
| A-4 | 워커(`service_role`) 코드의 명시적 `workspace_id` 필터 | 통과 | ① `0035_wiki_evidence_backfill.sql:20-56` (`wiki_evidence_backfill_candidates`): `p_workspace_id is null` 거부, `wiki_pages w`(`L50`), `source_chunks c` 및 `raw_sources r` 조인(`L45-46`), `wiki_page_evidence e`(`L41-42`), `has_more` 서브쿼리(`L55-56`) 전부에 `workspace_id = p_workspace_id` 및 `w.sources ? c.raw_source_id::text` 필터를 명시함.<br>② `0035_wiki_evidence_backfill.sql:71-145` (`apply_wiki_evidence_backfill`): `for share` 잠금 3종(`L94-102`), 단건 재검증 조회 3종(`L105-120`: `wiki_pages`, `raw_sources`, `source_chunks`의 `workspace_id = p_workspace_id` 및 `v_page.sources ? v_source.id::text`), 최종 `insert into public.wiki_page_evidence`(`L139-142`) 전부에 `p_workspace_id`를 명시함.<br>③ `apps/worker/src/worker/evidence_backfill.py`: `export_candidates`(`L163, 175, 183-184`), `validate_files`(`L235, 238-239, 254-260`), `apply_approved`(`L312-313, 322, 393-394`)에서 `workspace_id` 일치와 출처 범위를 다중 검증함 |
| A-5 | 새 자식 테이블의 복합 FK `(id, workspace_id)` | 해당 없음 | 신규 자식 테이블 없음. 쓰기 대상인 기존 `public.wiki_page_evidence`(`0030_wiki_page_evidence.sql:28-33`)는 이미 `(wiki_id, workspace_id)` 및 `(chunk_id, workspace_id)` 복합 FK를 보유함 |
| B-6 | `USING`에 막힌 UPDATE/DELETE 0행 → 403 매핑 | 해당 없음 | 사용자 API(`UserDb` 경유 UPDATE/DELETE) 경로 변경 없음 |
| B-7 | SQLSTATE `42501`(`WITH CHECK` 위반) → 403 매핑 | 해당 없음 | 사용자 API 경로 변경 없음 |
| C-8 | at-least-once 재실행 안전성 및 upsert 키 | 통과 | 큐 잡 핸들러는 추가되지 않았으나, 관리용 적용 경로인 `0035_wiki_evidence_backfill.sql:138-146`이 기존 근거 DELETE 없이 `insert into public.wiki_page_evidence(workspace_id, wiki_id, raw_source_id, chunk_id) ... on conflict (wiki_id, chunk_id) do nothing returning ...`을 사용해 재실행에 멱등함. 또한 `raw_sources` → `wiki_pages` → `source_chunks` UUID 오름차순 `for share` 잠금(`L94-102`)과 `page_token`·`source_token`·`chunk_token` 대조(`L127-134`)를 단일 트랜잭션에서 수행해 부분 적용과 경합 손상을 방지함 |
| C-9 | `jobs` 직접 UPDATE 금지 (`claim_job` 등 전용 함수 사용) | 해당 없음 | `jobs` 테이블을 조회하거나 수정하지 않음 (`apps/worker/tests/test_evidence_backfill.py:298, 303, 324`에서 전후 불변 확인) |
| D-10 | 벡터 검색 `set local hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 질의 없음 |
| D-11 | 색인·질의 토크나이저 일치 및 `tsv_tokenizer_version` | 통과 | FTS 질의나 `search_tsv` 갱신 없음. 후보 정렬 점수(`apps/worker/src/worker/evidence_backfill.py:24, 79-82`)는 공유 코어의 `normalize`·`bigram`을 그대로 사용하며, `0035_wiki_evidence_backfill.sql:34-37, 129-132`의 `chunk_token` 계산은 `search_tsv`·`tsv_tokenizer_version`·`embedding` 등 파생 컬럼을 제외해 재색인이 검토 토큰을 조용히 무효화하지 않도록 설계됨 (`apps/worker/tests/test_evidence_backfill.py:754-760` 검증) |
| D-12 | `search_tsv` 생성 컬럼 전환 시도 여부 | 해당 없음 | `search_tsv` 컬럼 정의 및 값 변경 없음 |
| D-13 | 프롬프트 템플릿 `str.format` 사용 금지 | 해당 없음 | 프롬프트 템플릿 및 `str.format` 사용 없음 |
| D-14 | 인용 앵커(`raw_source_id`+`chunk_index`+char 구간, `wiki_id`+`slug`) 보존 및 조용한 실패 방지 | 통과 | ① 이중 Citation의 원문 슬라이스 무결성을 위해 `0035_wiki_evidence_backfill.sql:38-40, 121-126` 및 `apps/worker/src/worker/evidence_backfill.py:261-262`에서 `char_start >= 0`, `char_end > char_start`, `char_end <= char_length(r.content)`, `substring(r.content from c.char_start + 1 for c.char_end - c.char_start) = c.content`를 후보 추출·로컬 검증·DB 적용 3단계 모두에서 강제해 좌표 불일치 청크가 근거로 연결되는 조용한 실패를 차단함.<br>② PostgREST `max_rows` 절단으로 인한 페이지 누락을 막기 위해 `wiki_evidence_backfill_candidates`(`0035_wiki_evidence_backfill.sql:11-58`)는 최대 50페이지를 단일 JSONB 객체로 묶어 반환하고, CLI(`evidence_backfill.py:170-199`)는 `has_more`·`next_cursor` 단조 증가를 검증하며 전수 순회함.<br>③ 로컬 산출물 경로를 `.gitignore`(`L44`)에 등록된 `.local/evidence-backfill/`로 강제(`evidence_backfill.py:85-94`)해 민감 본문 유출을 차단함 |
| E-15 | 새 마이그레이션 번호가 기존 최대 번호보다 큰가 | 통과 | 기존 최대 번호 `0034_control_risk_tab.sql` 다음인 `0035_wiki_evidence_backfill.sql`을 사용함 (`docs/reference/stack.md:54, 85`, `docs/ops/wiki-evidence-backfill.md:14-27`) |

## 조치가 필요한 항목

없음.

## 판정 근거

변경분은 사용자 요청 경로에 `service_role`을 노출하지 않고, 새 백필 RPC 3종 모두 `public`·`anon`·`authenticated` 권한을 회수한 뒤 `service_role` 전용으로 제한했다. `service_role`(BYPASSRLS)로 동작하는 모든 SQL 쿼리와 CLI 검증 단계에 `workspace_id` 필터 및 `wiki_pages.sources` 소속 검증이 명시되어 있으며, `FOR SHARE` 잠금 + SHA-256 스냅샷 토큰 검증 + `(wiki_id, chunk_id)` 멱등 삽입으로 교차 테넌트 오염·경합 시 조용한 데이터 손상·좌표 불일치 근거 연결·PostgREST 행 절단 누락을 모두 차단했다. A-1~E-15 전 항목에서 위반이 없으므로 `pass`로 판정한다.
