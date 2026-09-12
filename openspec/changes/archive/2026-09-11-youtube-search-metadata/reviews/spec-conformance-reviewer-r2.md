# Spec Conformance 리뷰 — youtube-search-metadata r2

- 판정: pass
- 대상: working tree(uncommitted) vs `HEAD f0c793e5928dfd8b0f26fce9f8c818ffc787f874`. r1과 동일하게 이 change는 `main`에 unstaged 상태로 구현되어 있어 `git diff main...HEAD`는 비어 있다. `git status` 기준 unstaged 변경 전체(worker/API/dashboard의 youtube 관련 파일)를 대상으로 재검증했다.
- 일시: 2026-09-11T10:14:12Z

## 실행한 검증

- `cd apps/worker && python -m pytest -q` → 220 passed
- `cd apps/api && python -m pytest -q` → 256 passed
- `cd apps/dashboard && pnpm test` → 448 passed (전체 스위트)
- `cd apps/dashboard && pnpm vitest run tests/YoutubeChannelSearch.test.tsx --reporter=verbose` → 12 passed
- `cd apps/worker && python -m pytest tests/test_youtube.py -k "order_and_relevance_language_are_forwarded or channel_statistics_partial_failure" -v` → 2 passed
- `cd apps/worker && ruff check src/worker/youtube.py tests/test_youtube.py` → 클린
- `cd apps/dashboard && pnpm exec eslint tests/YoutubeChannelSearch.test.tsx components/YoutubeChannelSearch.tsx` → 클린

## r1 지적 3건 재검증

| # | r1 지적 | 상태 | 증거 |
| --- | --- | --- | --- |
| 1 | `order`/`relevance_language`가 실제 `search.list` 업스트림 호출 params에 반영되는지 검증하는 워커 테스트 없음 | 해소 | `apps/worker/tests/test_youtube.py:300-316` `test_order_and_relevance_language_are_forwarded_to_search_list` — `_search_handler(seen=seen)`로 실제 업스트림 요청 URL을 캡처해 `seen["/youtube/v3/search"].params["order"] == "videoCount"`, `params["relevanceLanguage"] == "ko"`를 직접 단언. `_search_handler`의 `seen` 파라미터(`apps/worker/tests/test_youtube.py:189-201`)가 handler에 들어온 실제 `request.url`을 경로별로 저장하므로, `search_channels()`가 실제로 만드는 HTTP 요청을 검증한다. 단독 실행 시 통과 확인 |
| 2 | 채널 통계 배치 조회의 "일부 채널만 누락"(부분 실패) 경로를 검증하는 워커 테스트 없음 | 해소 | `apps/worker/tests/test_youtube.py:319-380` `test_channel_statistics_partial_failure_keeps_missing_channel_core_fields` — `search.list`가 UC1·UC2 두 채널을 반환하고 `channels.list`가 UC1 통계만 응답하는 상황을 구성. `by_id["UC1"].subscriber_count == 10`(통계 있는 채널은 병합됨)와 `by_id["UC2"].title == "채널2"` + `subscriber_count/video_count/handle`이 모두 `None`(누락된 채널이 목록에서 사라지지 않고 핵심 필드만 유지, `youtube.py:339-340`의 `stats_by_id.get(...)` 분기)을 단언. Scenario "Channel statistics cannot be enriched"의 "omits a candidate" 절반을 정확히 재현 |
| 3 | 구독자 수·영상 수·핸들이 실제 값으로 렌더되는지 확인하는 대시보드 테스트 없음 | 해소 | `apps/dashboard/tests/YoutubeChannelSearch.test.tsx:17-36`에서 `channel()` 헬퍼가 `overrides`(`subscriber_count`/`video_count`/`handle`)를 받도록 확장됨. `:258-279` "구독자 수·영상 수·핸들을 배지로 렌더한다" 테스트가 `subscriber_count: 45000, video_count: 120, handle: "@cookingchannel"`로 채널을 렌더한 뒤 `screen.getByText("@cookingchannel")`, `screen.getByText("구독자 45,000명")`, `screen.getByText("영상 120개")`를 단언. 컴포넌트 렌더 경로(`apps/dashboard/components/YoutubeChannelSearch.tsx:284-309`, `formatChannelCount`가 `toLocaleString("ko-KR")` 사용, `:29-32`)와 텍스트 포맷이 정확히 일치함을 코드 대조로 확인 |

## 시나리오 판정 (r1 대비 갱신분만; 나머지는 코드 미변경으로 r1 결과 유지)

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Keyword channel discovery / Member searches channels by keyword | 충족 | r1과 동일 + 3번 지적 해소로 렌더 테스트까지 확보: `apps/dashboard/tests/YoutubeChannelSearch.test.tsx:258-279` |
| Keyword channel discovery / Member continues to the next result page | 충족 | r1과 동일, 코드 미변경 |
| Keyword channel discovery / Non-member attempts channel search | 충족 | r1과 동일, 코드 미변경 |
| Keyword channel discovery / Member changes the result order | 충족 | 1번 지적 해소: `apps/worker/tests/test_youtube.py:300-316` |
| Keyword channel discovery / Channel statistics cannot be enriched | 충족 | 2번 지적 해소: `apps/worker/tests/test_youtube.py:319-380` (부분 실패) + 기존 `test_channel_statistics_failure_still_returns_core_fields` (전체 실패), 두 갈래 모두 커버 |
| Channel video browsing / Member opens a selected channel | 충족 | r1과 동일, 코드 미변경 |
| Channel video browsing / Video has no captions available | 충족 | r1과 동일, 코드 미변경 |

## 판정 근거

r1에서 지적한 세 항목 모두 구현 코드 변경 없이 테스트만 추가되었고, 세 테스트 모두 실제 스펙 THEN 절을 직접 단언하는 방식으로 작성되어 있다(업스트림 요청 params 직접 캡처, 부분 실패 시 개별 채널의 필드 상태 단언, 실제 컴포넌트가 만드는 텍스트 포맷과 일치하는 배지 문구 단언). 세 테스트를 개별 실행해 통과를 확인했고, worker(220)·api(256)·dashboard(448) 전체 스위트도 보고된 수치와 일치하게 통과했으며 ruff/eslint도 클린이다. r1에서 이미 충족으로 판정된 나머지 시나리오는 코드 변경이 없어 재확인만으로 충분했다. 미충족 Scenario가 남아있지 않으므로 `pass`로 판정한다.
