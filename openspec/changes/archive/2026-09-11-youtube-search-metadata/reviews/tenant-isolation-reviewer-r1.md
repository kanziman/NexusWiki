# Tenant Isolation 리뷰 — youtube-search-metadata r1

- 판정: pass
- 대상: working tree (uncommitted) vs `HEAD f0c793e5928dfd8b0f26fce9f8c818ffc787f874`. `git diff main...HEAD`는 빈 결과다 — 현재 브랜치가 `main` 자체이고 변경이 아직 커밋되지 않았기 때문에, `git status`가 가리키는 unstaged 변경 전체를 대상으로 리뷰했다.
- 일시: 2026-09-11T10:00:35Z

## 검사 대상 파일

`apps/api/src/api/routers/youtube.py` · `apps/api/tests/test_youtube_router.py` ·
`apps/worker/src/worker/youtube.py` · `apps/worker/src/worker/__main__.py` ·
`apps/worker/tests/test_youtube.py` · `apps/dashboard/components/YoutubeChannelSearch.tsx` ·
`apps/dashboard/components/YoutubeVideoList.tsx` · 관련 테스트 3개 ·
`openspec/specs/youtube-channel-import/spec.md`

이 변경은 `raw_sources`·`jobs` 등 어떤 테이블도 쓰지 않는다(검색·목록 조회만). 새 테이블·새
마이그레이션·새 GRANT가 전혀 없어 A-2, A-3, A-5, C-8, C-9, D-10~D-14, E-15는 이 diff의
성격상 구조적으로 해당 없음이다.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 요청 경로의 `service_role` | 통과 | `apps/api/src/api/routers/youtube.py:79-86` `_user_db()`가 요청자 `credentials.credentials`(JWT)로 `UserDb`를 만든다. `_require_membership`(89-101)은 이 `UserDb`로 `has_workspace_role` RPC만 부른다 — `service_role`/service client는 이 라우터에 등장하지 않는다. 워커 쪽(`apps/worker/src/worker/youtube.py`)이 쓰는 것은 YouTube provider API 키이지 Supabase `service_role`이 아니며, 이는 SEC-01에 따라 원래도 워커만 소유하던 것으로 이번 diff가 새로 도입한 것이 아니다. |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 새 테이블 없음. 이 change는 DB 스키마를 건드리지 않는다. |
| A-3 | `anon` GRANT/정책 신규 추가 | 해당 없음 | 마이그레이션 파일 변경 없음(`git status`에 `supabase/migrations/` 항목 없음). |
| A-4 | `service_role` 워커의 `workspace_id` 명시 필터 | 해당 없음 | 워커의 신규/변경 코드(`_enrich_with_channel_statistics`, `order`/`relevance_language` 전달)는 DB를 전혀 건드리지 않는다. 워커가 실제로 DB를 만지는 유일한 지점(`apps/worker/src/worker/__main__.py`의 `_check_ask_budget`/`_record_ask_usage`)은 이 diff의 변경 범위 밖이며 그대로다. |
| A-5 | 신규 자식 테이블의 복합 FK | 해당 없음 | 새 테이블 없음. |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 이 라우터는 UPDATE/DELETE를 수행하지 않는다(순수 조회 프록시). `_require_membership`이 멤버가 아닐 때 던지는 `WorkspaceForbidden(table="workspace_members", affected=0)`(`youtube.py:101`)은 RLS 0행이 아니라 RPC 결과 판정이지만, 기존 `_render_isolation_failure`(변경되지 않은 `apps/api/src/api/errors.py:234-241`)로 여전히 403에 매핑된다. |
| B-7 | SQLSTATE 42501 → 403 | 통과(불변) | `errors.py`는 이 diff에서 전혀 수정되지 않았고 42501 매핑(`errors.py:244-246`)은 그대로다. |
| C-8 | 멱등 upsert 키 | 해당 없음 | 이 change는 새 DB 행을 쓰지 않는다(검색 캐시는 프로세스 메모리, 테넌트 데이터 아님 — `youtube.py:104-116`의 기존 D3 결정 재확인). |
| C-9 | `jobs` 직접 UPDATE 금지 | 해당 없음 | `jobs` 테이블에 손대지 않는다. |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 벡터 검색과 무관. |
| D-11 | 토크나이저 버전 일치 | 해당 없음 | `search_tsv`/`tsv_tokenizer_version`과 무관. |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음. |
| D-13 | 프롬프트 `str.format` | 해당 없음 | 프롬프트 템플릿 변경 없음. |
| D-14 | LLM 컨텍스트 인용 앵커 | 해당 없음 | LLM 컨텍스트 조립과 무관한 검색 메타데이터 기능이다. |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 신규 마이그레이션 없음. |

## 추가로 짚어본 것 (체크리스트 밖, 문맥상 필요)

1. **캐시 키에 `workspace_id`가 없다** — `SearchCache`(`apps/api/src/api/routers/youtube.py:104-142`)의 키는 `(query, region_code, page_token, order, relevance_language)`뿐이고 `workspace_id`가 없다. 다만 이 캐시가 담는 데이터는 YouTube의 공개 검색 결과이지 워크스페이스 소유 데이터가 아니며, 이는 이번 diff가 도입한 설계가 아니라 기존 D3 결정("이 데이터는 테넌트 데이터가 아니다")을 그대로 유지한 것이다(`104-111`행 docstring 참고). 또한 멤버십 확인(`_require_membership`, 268행)이 캐시 조회(270-275행)보다 **먼저** 실행되므로, 비멤버가 캐시 워밍 결과를 훔쳐보는 경로도 없다. 이 change는 캐시 키 축을 3개→5개로 늘렸을 뿐 이 성질을 바꾸지 않았다 — 문제 없음.
2. **쿼터/통계 조회 실패가 "조용한 성공"으로 위장되지 않는가** — `_enrich_with_channel_statistics`(`apps/worker/src/worker/youtube.py:282-353`)가 `channels.list`(+1유닛) 실패를 삼키고 핵심 필드만 반환하는 것은 우연한 예외 흡수가 아니라 `design.md`("채널 통계 조회 실패는 검색 전체를 실패시키지 않는다")와 spec Given/When/Then(`tasks.md` Task 3)에 명시된 의도된 축소 응답이다. 대시보드는 `subscriber_count`/`video_count`가 `null`일 때 배지 자체를 숨긴다(`YoutubeChannelSearch.tsx` diff, "배치 조회가 실패하면 셋 다 null이다" 주석) — 통계가 있는데 없다고 보여주는 거짓 확언이 아니라 항목을 생략하는 것이라 조용한 실패 anti-pattern과 다르다. `search.list`(100유닛) 자체의 쿼터 소진은 기존 `YoutubeQuotaExceeded → 503`(`errors.py`, 이 diff 밖) 경로로 여전히 구분 가능하게 올라간다.
3. **`좋아요 수` 비공개 처리** — `like_count`가 응답에서 아예 빠진 경우(비공개 설정) `_parse_stat_count(None)`이 `None`을 반환하고(`youtube.py:385-392`), 프론트는 `formatCount`가 빈 문자열이면 해당 줄 자체를 렌더하지 않는다(`YoutubeVideoList.tsx` diff). `0`으로 접지 않아 "숨김"과 "0개"를 구분하는 스펙 요구(Task 2 Given/When/Then)를 지킨다.
4. **범위 밖 관찰**: 같은 `git status`에 걸린 `apps/dashboard/app/w/[workspaceId]/sources/page.tsx`(jobs 조회를 `raw_source_id` 컬럼에서 `payload->>raw_source_id`로 변경)와 `wiki/loading.tsx`는 `openspec/changes/archive/2026-09-11-youtube-search-metadata/tasks.md`에 나열된 파일이 아니라 이 change의 범위 밖이다. 참고로만 확인했고, 두 곳 모두 `.eq("workspace_id", workspaceId)` 필터는 유지되어 있어 테넌트 격리 문제는 보이지 않는다. 이 change의 판정에는 포함하지 않았다.

## 조치가 필요한 항목

없음.

## 판정 근거

이 change는 DB 스키마·RLS·`jobs` 테이블·워커의 `service_role` 사용 경로를 전혀 건드리지 않는
순수 조회 확장(YouTube 검색 결과에 구독자 수·통계·정렬 옵션 추가)이다. 유일하게 테넌트 경계와
접점이 있는 지점 — 멤버십 확인이 캐시 조회보다 앞서는가, 캐시 키가 정렬/언어 축을 놓쳐 조용히
틀린 결과를 서빙하지 않는가 — 둘 다 코드와 테스트(`test_cache_distinguishes_order_and_relevance_language`
등)에서 명시적으로 지켜진다. 쿼터/통계 조회 실패 경로도 기존에 확립된 403/503/404 구분 오류
매핑을 그대로 유지하며 새로 도입한 "실패를 성공처럼 보여주는" 지점이 없다. 따라서 `pass`.
