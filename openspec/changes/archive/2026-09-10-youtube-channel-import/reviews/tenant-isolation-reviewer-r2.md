# Tenant Isolation 리뷰 — youtube-channel-import r2

- 판정: pass
- 대상: `git diff main...HEAD` (c0176fb) + 커밋되지 않은 워킹트리
- 일시: 2026-09-10T05:55:24Z

r1과 같이 이 change가 만든 표면으로 범위를 한정한다. `main...HEAD`에 함께 들어오는
이미 머지된 PR(#111 · #118~#124)의 diff는 각자 리뷰를 통과한 코드이며, E-15에서만
명시적으로 확인했다. HEAD는 r1 이후 움직이지 않았고 변경은 전부 워킹트리에 있다.

## r1 조치 3건의 반영 확인

| # | r1 조치 | 반영 | 확인 근거 |
| --- | --- | --- | --- |
| 1 | INSERT 미시도 요청의 멤버십 판정 | 반영 | `routers/sources.py:503-517`(`_assert_membership`) · `:608`·`:634`(`attempted`) · `:646-648`. 테스트 `test_sources_router.py:764`·`:787` |
| 2 | 503의 본문 토큰 대조 | 반영 | `routers/youtube.py:186-192`가 503·404를 대칭으로 좁혔다. 테스트 `test_youtube_router.py:195` |
| 3 | 워커의 `video_id` 재검증 | 반영 | `domain.py`의 `YOUTUBE_VIDEO_ID_PATTERN`을 api(`sources.py:88`)와 worker(`handlers/parse.py:165`)가 공유. 테스트 `test_handlers.py:561-586`(3케이스 파라미터화) |

검증 실행: `apps/worker` 73건 · `apps/api` (`test_sources_router.py` + `test_youtube_router.py`) 79건 전부 green.
`ruff check apps/api apps/worker packages/core` → All checks passed.

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 (퇴행 없음) | `apps/api/src` 전체에 `service_client` · `SUPABASE_SECRET_KEY` 사용이 없다(주석 1줄뿐). 신규 `_assert_membership`도 `_user_db`가 만든 요청자 JWT 어댑터(`sources.py:604`)로 RPC를 부른다 — service client를 새로 끌어오지 않았다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | 이 change에 마이그레이션이 없다. 워킹트리 diff에 `supabase/migrations/` 변경이 0건이다 |
| A-3 | `anon` 신규 GRANT·정책 | 해당 없음 | SQL 변경 0줄 |
| A-4 | service_role 코드의 workspace_id 필터 | 통과 (강화됨) | transcript 분기는 여전히 `get_raw_source(…, workspace_id=)`로 읽은 행만 쓰고 `update_raw_source_content`가 `id`+`workspace_id` 두 필터를 건다. 조치 3이 여기에 "DB에서 읽은 값을 사용자 입력으로 취급한다"를 실제로 구현했다 — `parse.py:165`가 `metadata.video_id`를 소비 직전에 재검증한다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 통과 (r1 단서 해소) | `_assert_membership`이 `has_workspace_role`의 0행/false를 `WorkspaceForbidden(table="raw_sources", affected=0)`으로 올린다(`sources.py:516-517`). `insert_one`의 0행은 기존대로 `db/user.py:151-152`가 403으로 바꾼다. `delete_source`의 `len(rows) != 1` 매핑도 그대로다 |
| B-7 | SQLSTATE 42501 → 403 | 통과 | `sources.py:563-567`이 `FORBIDDEN_SQLSTATE`만 재raise하고 나머지를 영상별 `failed/internal`로 접는다. 신규 `_assert_membership`은 그 위에 얹힌 별개 경로이고 같은 403 본문으로 렌더된다(`test_sources_router.py:783`이 `FORBIDDEN_BODY` 왕복 단언) |
| C-8 | 멱등성 (upsert 키) | 통과 (퇴행 없음) | 중복 키는 여전히 정규화된 영상 URL 해시 → `(workspace_id, content_hash)`. 조치 1은 읽기 전용 RPC 하나를 더할 뿐 쓰기 경로를 건드리지 않았다. parse 재실행은 `(raw_source_id, chunk_index)` 업서트 + `delete_source_chunks_from`. 조치 3의 재검증은 `update_raw_source_content` **이전**에 있어 부분 기록을 남기지 않는다 |
| C-9 | jobs 직접 UPDATE 금지 | 통과 (테스트 한정 예외 유지) | 프로덕션의 `jobs` 접근은 `db/service.py:171·183·202`(INSERT·SELECT)와 `routers/jobs.py:149·257`(SELECT)뿐이다. UPDATE는 `enqueue_source_job`·`complete_job_and_chain`·`dead_letter_job` RPC 경유. r1 관찰 3의 `conftest.py` 픽스처는 준비 전용으로 그대로다 |
| D-10 | `hnsw.iterative_scan` | 해당 없음 | 검색 질의 코드 변경 없음 |
| D-11 | 색인·질의 토크나이저 일치 | 통과 | transcript 분기는 조치 3 이후에도 다른 소스와 같은 합류 지점(`strip_forged_anchors`) 이후에 청킹·`bigram(normalize())`·`TSV_TOKENIZER_VERSION` 경로를 탄다 |
| D-12 | `search_tsv` 생성 컬럼화 시도 | 해당 없음 | 시도 없음 |
| D-13 | 프롬프트 템플릿 `str.format` | 해당 없음 | 프롬프트 변경 없음 |
| D-14 | 인용 앵커 | 통과 (퇴행 없음) | `sources.py:547`의 `metadata`가 `video_id`·`channel_id`·`url` 셋을 그대로 싣는다. 청크는 기존 `raw_source_id`+`chunk_index`+char 구간을 얻는다 |
| D (쿼터·소멸·설정 누락 구분) | | **위반 해소** | `routers/youtube.py:186-192`가 503·404를 대칭으로 토큰까지 대조한다. 워커가 실제로 붙이는 토큰과 정확히 일치함을 확인했다 — `worker/youtube.py:446`(`503 youtube_quota_exceeded`) · `:450`(`404 youtube_channel_not_found`). 토큰 없는 503은 `YoutubeUnavailable`(502) |
| D (SEC-01 자격증명 격리) | | 통과 (퇴행 없음) | `YOUTUBE_API_KEY`는 `apps/api/src`·`packages/core/src` 어디에도 없다(주석 1줄뿐). 조치 3이 core로 옮긴 것은 정규식 상수 하나이고 자격증명이 아니다 |
| D (비밀 누출) | | 통과 (퇴행 없음) | 조치 3의 실패 경로가 남기는 `last_error`는 `sanitize_error`의 `ExtractionQualityError` 분기를 타 `"unsupported_source_type chars=0 pages=0 threshold=0"`이 된다 — 문제의 `video_id` 문자열이 `last_error`에 실리지 않는다. `TranscriptUnavailable`의 사유 토큰 전용 처리도 그대로다(`queue.py:124-129`) |
| E-15 | 마이그레이션 번호 순서 | 해당 없음 | 워킹트리에 신규 마이그레이션 0건. 브랜치가 함께 들고 오는 `0020`의 처치는 `docs/ops/migration-0021-record.md`에 기록돼 있다 |

### 호출자가 지목한 확인 항목

#### `attempted` 계산이 모든 분기에서 정확한가

`attempted == 0` ⟺ `insert_one`이 한 번도 호출되지 않음. 분기별로 확인했다.

| 분기 | 위치 | `attempted` | 실제 INSERT 시도 | 일치 |
| --- | --- | --- | --- | --- |
| `seen` 중복 | `sources.py:615-617` | 증가 없음 | 없음 (`continue`) | ✓ |
| `bad_video_id` | `:621-625` | 증가 없음 | 없음 (DB 접촉 전) | ✓ |
| `budget_reached` 후속 | `:627-632` | 증가 없음 | 없음 (`continue`) | ✓ |
| 정상 시도 | `:634-641` | +1 | `insert_one` 1회 | ✓ |

세부 검증:

- **중복(`seen`) + `attempted == 0` 조합**: `seen` 판정이 형태 판정보다 **앞**이므로 형태 불량 id도 `seen`에 들어간다. 그래서 `[짧다, 짧다]`는 결과 1줄 + `attempted == 0`이 되고 멤버십 확인이 돈다. 중복의 첫 등장이 형태 정상이면 그 건에서 `attempted`가 1이 되므로, 중복 제거가 `attempted`를 실제보다 낮게 만드는 경우는 없다.
- **`budget_reached`**: 이 플래그는 `_register_one_video`가 `budget_exceeded`를 돌려준 뒤에만 선다(`:642-643`). 그 반환에 도달하려면 `attempted`가 이미 1 이상이다. 따라서 `budget_reached` 스킵과 `attempted == 0`은 공존할 수 없다.
- **`_MAX_BATCH_VIDEOS` 경계**: 상한은 `YoutubeVideoBatchRequest.videos`의 `max_length=_MAX_BATCH_VIDEOS`(`:140`)가 핸들러 진입 **전에** 422로 자른다. 루프에 별도 절단이 없으므로 경계에서 `attempted`가 어긋날 자리가 없다. `min_length=1`이 빈 목록도 막으므로 "videos가 비어서 attempted가 0"인 경로도 없다.
- **카운트 시점**: `attempted += 1`이 `await` **앞**에 있다(`:634`). 그 사이에 있는 것은 문자열 연산뿐이라(`_canonical_video_url` · `_text_content_hash`) DB에 닿기 전에 예외가 날 경로가 없다. 반대로 `insert_one`이 23505(`SourceAlreadyIngested`) · 예산 거부 · 기타 `DatabaseError`로 끝나도 INSERT는 이미 시도됐으므로 `attempted`가 1인 것이 옳다.
- **`attempted == 0`인데 멤버**: `_assert_membership`이 통과하고 그대로 `202 {"results": [...]}`가 나간다. `test_member_with_only_malformed_selection_gets_per_video_results`(`:787`)가 202 + `bad_video_id`를 단언한다 — 새 확인이 정상 경로를 403으로 바꾸지 않는다.

**TOCTOU 없음**: 이 경로는 아무것도 쓰지 않으므로 조회와 쓰기 사이의 창이 애초에 없다. 정상 경로(`attempted >= 1`)에는 RPC가 추가되지 않아 판정자가 여전히 INSERT 하나다 — 원 설계 의도가 유지됐다.

#### 조치 2가 실제 쿼터 경로를 끊지 않는가

끊지 않는다. 워커가 붙이는 토큰이 라우터가 대조하는 문자열과 정확히 같다
(`worker/youtube.py:446` · `:450`). `test_video_quota_exhaustion_stays_distinguishable`
(`test_youtube_router.py:217`)와 `test_worker_channel_not_found_maps_to_its_own_reason`(`:186`)이
정상 방향을, `:195`와 `:206`이 위장 방향을 각각 못 박는다. 429(토큰 버킷 고갈)와
504/502(`youtube_unavailable`)는 토큰 대조에서 떨어져 `YoutubeUnavailable`이 된다 — 의도대로다.

#### 조치 3이 정상 자막 경로를 막지 않는가

막지 않는다. `_register_one_video`가 만드는 `metadata.video_id`는 라우터에서 이미 같은
패턴을 통과한 값이므로 워커의 재검증을 항상 통과한다. 워커 테스트 73건이 green이고
그중 정상 transcript 파싱 케이스가 포함돼 있다. 재검증 실패는
`ExtractionQualityError` → `NON_RETRYABLE_ERRORS`(`worker/errors.py`)로 즉시 dead가 되어
헛도는 재시도를 만들지 않는다.

#### r1에서 통과로 본 항목의 퇴행

없다. SEC-01 · 비멤버 쿼터 소비(`routers/youtube.py:242`·`:284`, 캐시 조회보다 앞) ·
멱등성 · 재시도 판정(`NON_RETRYABLE_ERRORS`에 기반 클래스 미포함 유지) ·
`last_error` 비밀 누출 전부 위 표에서 개별 확인했다.

## 조치가 필요한 항목

없다.

## 관찰 (판정에 반영하지 않음)

1. **폴백 멤버십 확인이 `viewer`이고 원래 판정자는 `editor`다.**
   - 위치: `apps/api/src/api/routers/sources.py:514` (`"min_role": "viewer"`) ↔ `supabase/migrations/0004_rls_policies.sql:217-219` (`raw_sources_insert_editor`가 `editor` 요구)
   - r1의 조치 문구는 `editor`를 제안했으나 구현은 `viewer`다. delta spec의 문구는
     "a workspace the requester is **not a member of**"(`specs/youtube-channel-import/spec.md:69`)이므로
     `viewer`가 스펙과 정확히 일치하며, 비멤버는 두 값 중 무엇을 써도 403이다 —
     **테넌트 경계는 완전히 닫혀 있다.**
   - 남는 것은 테넌트 **안**의 역할 비대칭뿐이다: viewer가 형태 정상 목록을 보내면 403,
     전부 형태 불량인 목록을 보내면 202(전 항목 `bad_video_id`)를 받는다. 어느 쪽도 행을
     만들지 않고 어느 쪽도 "성공"으로 보이지 않으므로 조용한 실패가 아니다. 다만 폴백이
     자기가 대신하는 판정자보다 느슨하다는 사실은 기록해 둔다 — 나중에 이 엔드포인트에
     "형태 불량이어도 무언가를 남기는" 분기가 생기면 그때는 실제 차이가 된다.
2. **`bad video_id` dead-letter의 `last_error`가 기존 사유와 같은 토큰이다.**
   `unsupported_source_type`이 "알 수 없는 source_type"과 "형태가 틀린 video_id" 양쪽에
   쓰인다. 비밀은 새지 않고(위 D 항목) 사용자가 취할 행동도 같지만("이 원문은 다시 만들어야
   한다"), 운영자가 로그만 보고 둘을 가를 수는 없다. r1의 조치가 지정한 사유이므로 이번
   라운드의 지적으로 올리지 않는다.
3. r1의 관찰 1(예산 상한에 처음 닿은 영상이 잡 없는 `raw_sources` 행으로 남는다) ·
   관찰 2(검색 리스너 토큰 버킷 고갈이 502로 보인다) · 관찰 3(`conftest.py`의
   `dead_letter_job` 픽스처) · 관찰 4(비공개 영상만 있는 페이지의 문구 조합)은 그대로
   유효하다. 이번 수정이 어느 것도 악화시키지 않았고 어느 것도 해소하지 않았다.

## 판정 근거

r1이 올린 세 건이 전부 코드와 회귀 테스트로 닫혔다. 조치 1은 "격리 판정자에 도달하지 않는
입력"을 없앴고, `attempted` 계산을 네 분기(중복 · 형태 불량 · 예산 스킵 · 정상)와 상한
경계에서 각각 따져본 결과 `attempted == 0`과 "INSERT 시도 0회"가 정확히 동치임을 확인했다.
정상 경로에는 RPC가 추가되지 않아 판정자가 하나로 유지되고 TOCTOU 창도 생기지 않았다.
조치 2는 워커가 실제로 붙이는 토큰과 대조 문자열이 일치함을 확인해 정상 쿼터 경로를
끊지 않으면서 위장만 막았다. 조치 3은 `service_role` 경로가 DB에서 읽은 값을 소비 직전에
재검증하게 만들었고, 실패 사유가 `last_error`로 새지 않는 것까지 확인했다.

퇴행 점검에서도 A-1 · SEC-01 · C-9 · D-14 · 재시도 판정 · 비밀 누출 전부 그대로였고,
마이그레이션·`anon` GRANT·벡터 검색·토크나이저·프롬프트 템플릿은 이 change가 여전히
건드리지 않는다. 남은 관찰 2건은 테넌트 경계를 넘지도, 데이터를 조용히 손상시키지도
않는다. 따라서 `pass`다.
