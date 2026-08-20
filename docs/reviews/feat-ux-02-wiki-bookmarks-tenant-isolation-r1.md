# Tenant Isolation 리뷰 — feat/ux-02-wiki-bookmarks r1

- 판정: pass
- 대상: `git diff main...feat/ux-02-wiki-bookmarks` (커밋 `1308435bed1a43d85a58a420e77bf64ffe080543`)
- 일시: 2026-08-20T04:58:33Z

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | 전체 diff에 `service_role`/`SUPABASE_SERVICE_ROLE`/service client 참조 0건. `bookmark-actions.ts`, `wiki/[slug]/page.tsx`, `wiki/page.tsx`, `ContentViewer.tsx` 모두 `lib/supabase/server` 또는 `lib/supabase/client`의 requester JWT 클라이언트만 사용 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 통과 | `0017_wiki_bookmarks.sql:12-29` — `create table` 직후 같은 파일에서 `alter table … enable row level security`. 정책 없는 창 없음 |
| A-3 | anon 신규 GRANT/정책 | 통과 | `0017_wiki_bookmarks.sql:56`은 `grant … to authenticated`만 부여. `anon`에 새 정책/GRANT 없음. 로컬 DB에서 `information_schema.role_table_grants`로 실측 — `anon`은 `TRUNCATE/REFERENCES/TRIGGER`(스키마 기본값)만 가지고 `SELECT/INSERT/DELETE`는 없음. `set local role anon; select …` 실행 시 `permission denied for table user_wiki_bookmarks` 확인 |
| A-4 | 워커의 workspace_id 명시 필터 | 해당 없음 | 이 change에 service_role로 도는 워커/백그라운드 코드가 없음 |
| A-5 | 복합 FK로 테넌트 전달 | 통과 | `0017_wiki_bookmarks.sql:24-26` — `foreign key (wiki_id, workspace_id) references wiki_pages (id, workspace_id)`. `wiki_pages_id_workspace_key`(0002)가 이를 뒷받침. 로컬 DB에서 `wiki_id`는 W1 소속인데 `workspace_id`만 W2로 짝지어 삽입 시도 → `23503 foreign_key_violation`으로 실측 차단 (테스트 5) |
| B-6 | 0행 → 403 매핑 | 해당 없음(패턴 다름) | 이 경로는 apps/api HTTP 라우터가 아니라 Next.js 서버 액션이라 HTTP 상태 코드 개념이 없음. 대신 `bookmark-actions.ts:26-31`의 delete는 PostgREST 오류(`error`)가 있으면 `{error: ...}`를 반환해 조용한 성공으로 위장하지 않음. `apps/dashboard/tests/bookmark-actions.test.ts:87-94`가 delete 오류 → 사용자 노출 오류 매핑을 검증함. 참고로 delete 자체가 영향 0행(이미 지워진 상태)인 경우는 오류가 아니라 자기 자신의 멱등 해제이므로 성공 취급이 맞다 — RLS `USING`이 남의 행을 가리는 케이스가 애초에 발생하지 않는다(PK가 `(user_id, wiki_id)`이므로 다른 사용자 행은 이 delete의 대상이 될 수 없음, 테스트 7로 실측) |
| B-7 | SQLSTATE 42501 → 403 매핑 | 해당 없음(패턴 다름) | 위와 동일 — HTTP 라우터가 아님. `insert`가 RLS `with check` 위반 시 PostgREST가 오류를 던지고 `bookmark-actions.ts:38-39`가 `{error: "즐겨찾기에 추가하지 못했습니다."}`로 매핑해 사용자에게 실패로 보여준다(조용한 성공 없음). 로컬 DB에서 비멤버 삽입 시도, 타인 명의 삽입 시도 모두 `42501 insufficient_privilege`로 실측 차단 (테스트 4, 6) |
| C-8 | at-least-once 멱등성 | 해당 없음 | 큐/워커 작업이 아니라 사용자 클릭 기반 토글이며 `(workspace_id, slug)`/`(raw_source_id, chunk_index)`/`(wiki_id, chunk_index)` upsert 키 대상 테이블이 아님. PK `(user_id, wiki_id)`가 사실상 같은 역할(중복 삽입은 `23505`로 막힘) |
| C-9 | jobs 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블 관련 코드 없음 |
| D-10 | `hnsw.iterative_scan = strict_order` | 해당 없음 | 벡터 검색 경로 없음 |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | `search_tsv`/`tsv_tokenizer_version` 관련 변경 없음 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 템플릿 변경 없음 |
| D-14 | 인용 앵커 포함 여부 | 해당 없음 | LLM 컨텍스트 조립 경로가 아님(북마크 UI 기능) |
| E-15 | 마이그레이션 번호 순서 | 통과 | 기존 최대 번호 `0016`(`0016_public_sharing.sql`) 다음이 `0017_wiki_bookmarks.sql`. 순서 어긋남 없음 |

## 로컬 DB 실측 (docker exec supabase_db_NexusWiki, 트랜잭션 내 rollback으로 정리)

사용자 A·B(워크스페이스 W1 멤버), C(워크스페이스 W2 오너, W1 비멤버)를 만들고 `set local role authenticated; set local request.jwt.claims`로 각 사용자 세션을 시뮬레이션했다.

| 시나리오 | 기대 | 실측 |
| --- | --- | --- |
| A가 자기 워크스페이스(W1) 위키를 북마크 | 성공 | `INSERT 0 1` 성공 |
| B가 같은 W1 문서를 북마크 | 성공(별개 행) | `INSERT 0 1` 성공 |
| A가 SELECT | B의 행은 안 보여야 함 | A는 자기 행 1건만 조회됨 |
| C(W1 비멤버)가 W1 위키를 자기 명의로 북마크 시도 | 차단 | `42501 insufficient_privilege` |
| A(W1·W2 양쪽 멤버)가 W1 소속 `wiki_id`에 `workspace_id=W2`를 짝지어 삽입 | 차단(FK) | `23503 foreign_key_violation` |
| A가 B의 `user_id`로 위장해 삽입 | 차단 | `42501 insufficient_privilege` |
| A가 `wiki_id`만 걸고 delete 실행(B도 같은 wiki_id 북마크한 상태) | A 자신의 행만 삭제, B 행은 생존 | `DELETE 1`, 이후 `service_role`로 확인 시 B의 행만 남음 |
| A가 존재하지 않는 `wiki_id`로 삽입 | 차단(FK) | `23503 foreign_key_violation` |
| `anon` 역할로 SELECT | 완전 거부 | `permission denied for table user_wiki_bookmarks` |

모든 케이스가 기대한 대로 차단/허용되었다. 재현 스크립트: `/private/tmp/claude-501/-Users-zorba-projects-NexusWiki/f629894a-64a6-4f1f-a5b5-98675e1d9bf6/scratchpad/bookmark_isolation_test.sql`(세션 scratchpad, 저장소 밖).

## 조치가 필요한 항목

없음.

## 판정 근거

A-1(서버 액션이 전부 requester JWT 클라이언트만 사용), A-3(anon GRANT 없음, 실측으로 완전 거부 확인), A-5(복합 FK가 `wiki_id`/`workspace_id` 불일치를 실제로 막는 것을 `23503`으로 실측)가 이 리뷰에서 가장 중요한 세 항목이었고 전부 통과했다. `user_id`를 요청 바디에서 그대로 받지 않고 세션에서 얻은 `user.id`로만 채우는 점(`bookmark-actions.ts:34-38`), INSERT `with check`가 `user_id`와 `is_workspace_member(workspace_id)`를 동시에 검사하는 점, PK `(user_id, wiki_id)`가 DELETE의 대상 범위를 자연히 본인 행으로 좁히는 점이 겹겹이 방어를 이룬다. B-6/B-7의 "0행/42501 → 403" 규칙은 apps/api HTTP 라우터를 전제로 하는데 이 기능은 Next.js 서버 액션(JSON 반환, HTTP 상태 코드 없음)이라 문자 그대로는 해당 없음으로 처리했지만, 그 취지("차단된 쓰기를 조용한 성공으로 보여주지 않는다")는 코드와 테스트 양쪽에서 실제로 지켜지고 있음을 확인했다.
