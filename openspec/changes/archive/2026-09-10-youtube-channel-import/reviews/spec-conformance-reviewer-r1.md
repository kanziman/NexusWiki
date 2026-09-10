# Spec Conformance 리뷰 — youtube-channel-import r1

- 판정: pass
- 대상: `git diff main...HEAD` (c0176fb) + 미커밋 작업 트리 (슬라이스 2~4)
- 일시: 2026-09-10T14:40:00+09:00

검토 범위는 커밋된 슬라이스 1과 아직 커밋되지 않은 슬라이스 2~4를 모두 포함한다.
`apps/worker/src/worker/transcript.py` · `apps/dashboard/components/YoutubeVideoList.tsx` ·
`apps/dashboard/tests/YoutubeVideoList.test.tsx` · `apps/dashboard/tests/YoutubeBatchImport.test.tsx` ·
`apps/worker/tests/test_transcript.py`는 아직 untracked 상태이므로 `/create-pr` 시 누락되지 않아야 한다.

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Keyword channel discovery / Member searches channels by keyword | 충족 | `apps/worker/src/worker/youtube.py:93-99`(channel_id·title·description·thumbnail 모델) · `:205-251`(`search.list` 파싱, `next_page_token`) · API `apps/api/src/api/routers/youtube.py:222-254` · UI `apps/dashboard/components/YoutubeChannelSearch.tsx:171-191` · 테스트 `apps/dashboard/tests/YoutubeChannelSearch.test.tsx:38` |
| Keyword channel discovery / Member continues to the next result page | 충족 | `apps/api/src/api/routers/youtube.py:229`(`page_token` 쿼리) → `:249-251` → 워커 `apps/worker/src/worker/youtube.py:223-224` · UI `apps/dashboard/components/YoutubeChannelSearch.tsx:84-91,203-211` · 테스트 `apps/dashboard/tests/YoutubeChannelSearch.test.tsx:103`, `apps/api/tests/test_youtube_router.py:142` |
| Keyword channel discovery / Non-member attempts channel search | 충족 | `apps/api/src/api/routers/youtube.py:83-95`(`has_workspace_role` → `WorkspaceForbidden`), `:240`(멤버십 확인이 캐시 조회보다 **앞선다**) · 테스트 `apps/api/tests/test_youtube_router.py:233`(비멤버 403), `:249`(미지의 워크스페이스도 403), `:221`(무자격 401) |
| Search quota conservation / Same keyword is searched again | 충족 | `apps/api/src/api/routers/youtube.py:98-142`(TTL+LRU 캐시), `:242-254`(캐시 히트면 `_call_worker_search` 미호출 — 외부 호출과 내부 홉을 함께 건너뜀) · TTL 기본 21,600초 `apps/api/src/api/settings.py:87` · 테스트 `apps/api/tests/test_youtube_router.py:35,43,51,61` |
| Exhausted external quota outcome / Quota is exhausted during channel search | 충족 | 워커 `apps/worker/src/worker/youtube.py:148-164`(`quotaExceeded`를 `keyInvalid`와 구분), `:185-192`, `:443-446`(503 전용 코드) → API `apps/api/src/api/routers/youtube.py:184-186` → `apps/api/src/api/errors.py:371-383,428` → UI `apps/dashboard/components/YoutubeChannelSearch.tsx:28-38` · 테스트 `apps/api/tests/test_youtube_router.py:94,105,116,207`, `apps/dashboard/tests/YoutubeChannelSearch.test.tsx:55,70` · 0건으로 위장하지 않음: 설정 누락도 쿼터로 접지 않는다 `apps/api/src/api/routers/youtube.py:169-171` |
| Channel video browsing / Member opens a selected channel | 충족 | `apps/worker/src/worker/youtube.py:290-374`(`channels.list`→`playlistItems.list`→`videos.list`, D4 준수 · 제목·게시일·길이·썸네일·`next_page_token`) · API `apps/api/src/api/routers/youtube.py:257-285` · UI `apps/dashboard/components/YoutubeVideoList.tsx:366-450` · 테스트 `apps/api/tests/test_youtube_router.py:167,186,195,259`, `apps/dashboard/tests/YoutubeVideoList.test.tsx:103,121` |
| Selective batch registration / Member registers a subset of a channel's videos | 충족 | `apps/api/src/api/routers/sources.py:589-616`(선택 목록만 순회, 영상별 결과 누적) · 영상당 독립 행 `:498-537`(행마다 새 `uuid4`, 영상별 `content_hash`) · 테스트 `apps/api/tests/test_sources_router.py:602`(행 2개·`raw_source_id` 상이), `apps/dashboard/tests/YoutubeBatchImport.test.tsx:66` |
| Selective batch registration / Some selected videos cannot be registered | 충족 | `apps/api/src/api/routers/sources.py:539-568`(`already_collected`·`budget_exceeded`·`bad_video_id`·`internal`을 영상별 `reason`으로), `:589-616`(첫 실패로 요청을 끊지 않음) · 테스트 `apps/api/tests/test_sources_router.py:672`(앞 건 실패해도 뒤 건 등록), `:764`(예산 상한) · UI `apps/dashboard/components/YoutubeVideoList.tsx:110-122,413-429` · 테스트 `apps/dashboard/tests/YoutubeBatchImport.test.tsx:118` |
| Selective batch registration / Registration targets another workspace | 충족 | `apps/api/src/api/routers/sources.py:556-561`(격리 위반만 예외로 승격 — 200 안의 `failed`로 접지 않음) → RLS `WITH CHECK` 42501 → 403 · 테스트 `apps/api/tests/test_sources_router.py:732`(403 + 행 0개), UI 분리 `apps/dashboard/tests/YoutubeBatchImport.test.tsx:185` |
| Transcript as source content / Video with an available transcript is registered | 충족 | 등록: `apps/api/src/api/routers/sources.py:512-524`(`source_type='transcript'`, `content=""` sentinel, `metadata{video_id, channel_id, url}`) · 본문 채움: `apps/worker/src/worker/handlers/parse.py:154-177` · 어댑터 `apps/worker/src/worker/transcript.py:181-204` · 테스트 `apps/api/tests/test_sources_router.py:569`(metadata 전량 단언), `apps/worker/tests/test_handlers.py:437`, `:493`(URL `fetch_source` 경로와 분리) |
| Transcript as source content / Citation resolves to a registered video | 충족 | `apps/worker/src/worker/handlers/parse.py:169-171`(자막 원문을 `raw_sources.content`로 저장) → `:182-205`(동일 본문을 `chunk_text`로 잘라 `char_start/char_end`와 함께 업서트) · 테스트 `apps/worker/tests/test_handlers.py:482-488`(`transcript[char_start:char_end] == chunk.content` 전량 단언) · 아래 「관찰 사항 1」 참고 |
| Distinguishable transcript failure / Selected video has no transcript | 충족 | 사유 3종 `apps/worker/src/worker/transcript.py:40-57,120-144` · 타입으로 재시도 가부 표현 `:88-117` · dead-letter 배선 `apps/worker/src/worker/errors.py:145-158` · `last_error`에 사유 토큰만 `apps/worker/src/worker/queue.py`(sanitize_error, `+7`) · 화면 문구 `apps/dashboard/components/JobStepper.tsx:56-96,289-307` · 테스트 `apps/worker/tests/test_transcript.py:141,170,194`, `apps/worker/tests/test_queue.py:261,288`, `apps/dashboard/tests/JobStepper.test.tsx:142,167,189` |
| Distinguishable transcript failure / 한 영상 실패가 나머지를 막지 않음 | 충족 | 영상마다 독립 `raw_sources` 행 + 독립 `parse` 잡(`apps/api/src/api/routers/sources.py:531-537` → `_insert_and_enqueue:258-284`) · 테스트 `apps/worker/tests/test_queue.py:308-330`(한 잡 dead, 다음 잡 succeeded) |
| Already collected video / Previously registered video is selected again | 충족 | 중복 키 = 정규화 영상 URL 해시 `apps/api/src/api/routers/sources.py:486-497,518` · 23505 → `SourceAlreadyIngested` → `status="already_collected"` `:539-547` · 행이 만들어지지 않으므로 chunk·page·embedding 잡 자체가 생기지 않음(`_insert_and_enqueue:242-256`은 INSERT 실패 시 인큐에 도달하지 않음) · 테스트 `apps/api/tests/test_sources_router.py:636`(제목이 달라도 동일 판정, `raw_sources` 1행 유지), `:707`(한 요청 안 중복 선택도 1행) · UI `apps/dashboard/components/YoutubeVideoList.tsx:79-85`(실패 문구로 뭉개지 않음) |

## 검증 실행 (이번 라운드에서 새로 실행)

- `uv run pytest apps/worker/tests` → 206 passed
- `uv run pytest apps/api/tests -k youtube` → 18 passed
- `uv run pytest apps/api/tests/test_sources_router.py` → 59 passed (로컬 스택 기동 상태, skip 없음)
- `pnpm --dir apps/dashboard test` → 76 files / 432 tests passed
- `openspec validate youtube-channel-import --strict` → valid

## 조치가 필요한 항목

없다. 모든 Scenario가 코드 경로와 테스트 증거로 충족된다.

## 관찰 사항 (판정에 영향 없음, 기록 목적)

1. **저장 본문과 청킹 본문의 앵커 제거 시점 차이.** `parse.py:169-171`은 자막 원문을 그대로
   `raw_sources.content`에 저장하고, `:182`에서 `strip_forged_anchors`를 통과한 문자열을 청킹한다.
   자막에 `[[wiki:…]]`/`[[src:…]]` 형태가 실제로 들어 있으면 "저장된 자막을 char 구간으로 자른
   것 == 청크 본문"이 어긋난다. 다만 이 순서는 URL·FILE 분기가 이미 따르고 있는 기존 계약이며
   (`test_handlers.py:425-428`이 같은 형태로 단언한다), 이번 change가 도입한 것이 아니다. 자막에서
   이 패턴이 나타날 개연성도 사실상 없다. 고치려면 전 소스 유형이 공유하는 저장 순서를 바꿔야
   하므로 이 change의 스펙 범위 밖이며, 별도 change로 다루는 것이 맞다.
2. **스펙에 없는 추가 결과: `youtube_channel_not_found`.** 채널 소멸을 404로 구분하는 경로
   (`apps/api/src/api/errors.py:198-211,430`, `apps/worker/src/worker/youtube.py:83-90`)는 delta spec의
   어느 시나리오도 요구하지 않는 사용자 관찰 가능 동작이다. 스펙의 "빈 결과로 위장하지 않는다"
   원칙과 같은 축이고 계약을 바꾸지 않으므로 범위 이탈로 보지 않되, `/opsx:sync` 시
   `openspec/specs/`에 반영 여부를 판단해야 한다.
3. **한 요청 안 중복 선택의 결과 축약.** `sources.py:589-596`은 같은 `video_id`를 두 번 고른
   요청에 결과 한 줄만 돌려준다. 스펙 문구("returns an outcome for each selected video")를
   글자대로 읽으면 두 줄이지만, 두 번째 줄이 "이미 수집됨"이 되어 **이전에 수집해 둔 것과
   구분되지 않는 거짓 결과**를 만든다. UI는 `Set` 선택이라 이 요청을 만들 수 없다. 의도된 선택으로
   판단한다(테스트 `test_sources_router.py:707`이 그 근거를 명시).
4. **커밋 상태.** 슬라이스 2~4가 아직 작업 트리에만 있다. 신규 파일 5개가 untracked이므로
   `/create-pr` 전에 `git add`가 누락되면 PR에 어댑터 자체가 빠진다.

## 판정 근거

delta spec의 12개 Scenario 전부가 코드 경로와 대응 테스트로 확인됐고, 이번 라운드에서 새로 실행한
워커·API·대시보드 테스트와 `openspec validate --strict`가 모두 통과했다. `tasks.md`의 `- [x]` 주장
가운데 대응 구현·테스트가 없는 항목은 발견되지 않았다(1.1~4.4 전수 대조). 조용한 범위 축소로 의심할
지점 — 영상별 결과의 축약, 채널 소멸 404 — 은 각각 기록으로 남겼으나 스펙 요구를 빠뜨리거나
계약을 넘어서는 동작이 아니다.
