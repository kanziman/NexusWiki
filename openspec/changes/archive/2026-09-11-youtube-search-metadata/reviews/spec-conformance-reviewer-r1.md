# Spec Conformance 리뷰 — youtube-search-metadata r1

- 판정: needs_fix
- 대상: working tree(uncommitted) vs `HEAD f0c793e5928dfd8b0f26fce9f8c818ffc787f874`. 이 change는 현재 `main` 브랜치 자체에 unstaged 상태로 구현되어 있어 `git diff main...HEAD`는 비어 있다. `git status` 기준 unstaged 변경 전체(worker/API/dashboard의 youtube 관련 파일)를 대상으로 리뷰했다.
- 일시: 2026-09-11T10:02:05Z

## 검사 대상 파일

`apps/worker/src/worker/youtube.py` · `apps/worker/src/worker/__main__.py` · `apps/worker/tests/test_youtube.py` ·
`apps/api/src/api/routers/youtube.py` · `apps/api/tests/test_youtube_router.py` ·
`apps/dashboard/components/YoutubeChannelSearch.tsx` · `apps/dashboard/components/YoutubeVideoList.tsx` ·
`apps/dashboard/tests/YoutubeChannelSearch.test.tsx` · `apps/dashboard/tests/YoutubeVideoList.test.tsx` · `apps/dashboard/tests/YoutubeBatchImport.test.tsx` ·
`openspec/specs/youtube-channel-import/spec.md`

`apps/dashboard/app/w/[workspaceId]/sources/page.tsx`, `apps/dashboard/app/w/[workspaceId]/wiki/loading.tsx`는 같은 `git status`에 걸려 있지만 `tasks.md`에 나열되지 않은, 이 change의 범위 밖 파일이다(dead job 집계·spacing 토큰 버그 수정으로 보인다). 이 리뷰의 판정에는 포함하지 않았다.

## 실행한 검증

- `cd apps/worker && python -m pytest tests/test_youtube.py -q` → 26 passed
- `cd apps/api && python -m pytest tests/test_youtube_router.py -q` → 20 passed
- `cd apps/dashboard && pnpm test` → 447 passed (전체 스위트, youtube 관련 3개 파일 포함)

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Keyword channel discovery / Member searches channels by keyword | 충족 | `apps/worker/src/worker/youtube.py:225-280`(search_channels가 `_enrich_with_channel_statistics` 호출) · 테스트 `apps/worker/tests/test_youtube.py::test_search_results_are_enriched_with_channel_statistics`. API 통과: `apps/api/src/api/routers/youtube.py:47-53`(`YoutubeChannel` 모델에 필드 추가). 대시보드 타입·조건부 렌더: `apps/dashboard/components/YoutubeChannelSearch.tsx:293-309`. ⚠️ 단, 구독자/영상 수·핸들이 **실제 값으로 렌더되는** 대시보드 테스트는 없음(아래 "조치가 필요한 항목" 3번) |
| Keyword channel discovery / Member continues to the next result page | 충족 | `apps/dashboard/components/YoutubeChannelSearch.tsx:100-111`(`fetchPage`가 `order`·`regionCode`·`relevanceLanguage` state를 페이지 토큰과 함께 항상 포함) · API 캐시 키 5축: `apps/api/src/api/routers/youtube.py:271`, 테스트 `apps/api/tests/test_youtube_router.py::test_cache_distinguishes_query_region_and_page_token` |
| Keyword channel discovery / Non-member attempts channel search | 충족 | 기존 회귀, 이 change로 변경되지 않음: `apps/api/tests/test_youtube_router.py::test_non_member_cannot_consume_shared_search_quota` (282-294행) |
| Keyword channel discovery / Member changes the result order | 부분충족(미검증) | 코드 경로는 존재: `apps/worker/src/worker/youtube.py:243`(`params["order"] = order`가 `search.list` 호출에 포함), API→워커 페이로드 전달은 테스트됨(`apps/api/tests/test_youtube_router.py::test_worker_receives_order_and_relevance_language`, 177-196행). 그러나 `order`/`relevance_language`가 실제 **업스트림 `search.list` HTTP 요청 params**로 전달되는지 검증하는 워커 레벨 테스트가 없다(`apps/worker/tests/test_youtube.py`에 `order`·`relevance_language` 문자열이 전혀 등장하지 않음 — 확인함). tasks.md 4.4는 "워커·API·대시보드 테스트 추가(정렬 변경이 파라미터에 반영...)"라 적었지만 워커 쪽 테스트는 실제로 없다 |
| Keyword channel discovery / Channel statistics cannot be enriched | 부분충족(미검증) | "조회 전체 실패" 경로는 테스트됨: `apps/worker/tests/test_youtube.py::test_channel_statistics_failure_still_returns_core_fields`. 그러나 시나리오의 "omits a candidate"(일부 채널만 통계 응답에서 누락되는 부분 실패) 코드 경로 — `apps/worker/src/worker/youtube.py:339-340`(`stats_by_id.get(channel.channel_id)`가 `None`이면 원본 채널 그대로 반환) — 를 검증하는 테스트가 없다. tasks.md 3.5는 "일부 채널만 통계 없는 부분 실패" 테스트를 추가했다고 적었으나 `test_youtube.py`의 테스트 목록(`test_search_channels_parses_items_and_next_page_token`, `test_search_results_are_enriched_with_channel_statistics`, `test_channel_statistics_failure_still_returns_core_fields`, `test_channel_statistics_batch_requests_all_ids_in_one_call`)에 부분 실패 케이스는 없음. 코드 리뷰상 해당 브랜치는 THEN을 만족하는 것으로 보이나(핵심 필드 유지 + `subscriber_count=None` 등 구분 가능한 상태), 테스트 증거가 없다 |
| Channel video browsing / Member opens a selected channel | 충족 | `apps/worker/src/worker/youtube.py:462-511`(part에 `statistics` 추가, `view_count`/`like_count` 파싱) · 테스트 `apps/worker/tests/test_youtube.py::test_statistics_are_parsed_and_private_like_count_is_none_not_zero`, `::test_video_detail_call_requests_statistics_part`. 대시보드 렌더: `apps/dashboard/components/YoutubeVideoList.tsx:477-488` · 테스트 `apps/dashboard/tests/YoutubeVideoList.test.tsx`("조회수·좋아요 수를 표시하고, 없는 값은 조용히 생략한다") |
| Channel video browsing / Video has no captions available | 충족 | 파싱: `apps/worker/src/worker/youtube.py:_parse_caption_flag`(368행대) · 테스트 `apps/worker/tests/test_youtube.py::test_caption_flag_true_false_and_missing_are_distinguished`(true/false/누락 세 값 구분). 렌더+선택 유지: `apps/dashboard/components/YoutubeVideoList.tsx:492-499`(배지), `:438-446`(체크박스 disabled는 `result`에만 종속, `has_captions`와 무관) · 테스트 `apps/dashboard/tests/YoutubeVideoList.test.tsx`("자막이 없을 수 있는 영상에 배지를 표시하고 선택은 막지 않는다") |

## 조치가 필요한 항목

1. **`order`/`relevance_language`가 실제 `search.list` 호출에 반영되는지 검증하는 워커 테스트 누락** — `apps/worker/src/worker/youtube.py:225-249`의 `search_channels()`는 `order`·`relevance_language`를 `search.list` params에 담아 보내지만, `apps/worker/tests/test_youtube.py`에는 이를 확인하는 테스트가 없다. 근거 시나리오: "Member changes the result order" — `search.list`가 `order=videoCount`로 호출되는지가 THEN의 핵심인데 이를 어서션하는 테스트가 없다. tasks.md 4.4는 이 테스트가 추가됐다고 명시했다. 제안: `_search_handler`가 `request.url.params["order"]`·`["relevanceLanguage"]`를 검증하는 테스트를 `test_youtube.py`에 추가한다.

2. **채널 통계 배치 조회의 "부분 실패"(일부 채널 ID만 응답에서 누락) 경로에 대한 워커 테스트 누락** — `apps/worker/src/worker/youtube.py:339-340`의 `stats_by_id.get(channel.channel_id) is None` 분기가 실제로 검증되지 않았다. 근거 시나리오: "Channel statistics cannot be enriched"의 "omits a candidate" 절반. 현재 테스트는 "전체 실패"(`stats_status=403`)만 다룬다. 제안: `search.list`가 채널 2개를 반환하고 `channels.list`가 그중 1개 ID만 포함한 응답을 주는 테스트를 추가해, 누락된 채널이 핵심 필드만으로 그대로 반환되는지 확인한다.

3. **구독자 수·영상 수·핸들이 실제 값으로 렌더되는지 검증하는 대시보드 테스트 누락** — `apps/dashboard/components/YoutubeChannelSearch.tsx:293-309`가 `subscriber_count`/`video_count`/`handle`을 조건부로 렌더하지만, `apps/dashboard/tests/YoutubeChannelSearch.test.tsx`의 `channel()` 헬퍼는 이 세 필드를 항상 `null`로 고정하고 있어(17-27행) 실제 값이 들어왔을 때 배지가 뜨는지 확인하는 테스트가 없다. tasks.md 3.5는 "정상 병합" 케이스에 대한 대시보드 테스트가 추가됐다고 적었으나, 실제로는 워커 레벨(정상 병합)만 테스트되고 대시보드 렌더링은 검증되지 않았다. 제안: `channel("UC1", "채널", { subscriber_count: 45000, video_count: 120, handle: "@x" })` 같은 케이스로 배지 텍스트(`구독자 45,000명` 등)가 렌더되는지 확인하는 테스트를 추가한다.

## 판정 근거

핵심 구현(워커의 `channels.list` 배치 병합·부분 실패 시 원본 유지, `caption`/`statistics` 파싱, API 캐시 키 5축 확장, 대시보드의 정렬/언어/지역 드롭다운과 캡션 배지)은 모두 코드상 스펙 시나리오의 WHEN/THEN 경로를 실제로 만들고 있고, 전체 테스트(worker 26·API 20·dashboard 447)가 통과한다. 다만 `tasks.md`가 "테스트 추가"를 명시적으로 주장한 세 지점(정렬 파라미터 전달, 채널 통계 부분 실패, 채널 카드 통계 렌더)에서 실제로는 대응 테스트가 없다 — 코드 리뷰로는 THEN이 충족된다고 판단되지만, 이 리뷰 규칙상 "증거 없이 구현된 것 같다"고 적을 수 없다. 세 항목 모두 스펙이나 설계를 바꿀 필요 없이 테스트 코드만 추가하면 해결되는 범위 안 문제이므로 `blocked`가 아니라 `needs_fix`로 판정한다.
