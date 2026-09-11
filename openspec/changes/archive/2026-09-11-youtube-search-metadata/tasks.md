## 1. 영상 목록 — 자막 가용 여부 배지

이슈: https://github.com/kanziman/NexusWiki/issues/142

- [x] 1.1 `apps/worker/src/worker/youtube.py`: `YoutubeVideo`에 `has_captions: bool | None` 추가, `list_channel_videos()`가 `videos.list` 응답의 `contentDetails.caption`("true"/"false"/누락)을 파싱해 채운다
- [x] 1.2 `apps/api/src/api/routers/youtube.py`: 새 필드를 응답 모델에 통과
- [x] 1.3 `apps/dashboard/components/YoutubeVideoList.tsx`: `has_captions === false`인 영상에 "자막 없을 수 있음" 배지 표시(선택은 막지 않음)
- [x] 1.4 워커·대시보드 테스트 추가(caption "true"/"false"/필드 누락 세 케이스)

Given: 채널 영상 목록을 조회했을 때 공급자가 특정 영상에 캡션이 없다고 보고하면
When: 영상 목록을 렌더링하면
Then: 그 영상에 자막 없음 배지가 표시되고, 선택 자체는 여전히 가능하다

검증: `cd apps/worker && pytest tests/test_youtube.py -k caption` · `cd apps/dashboard && pnpm test -- YoutubeVideoList`

## 2. 영상 목록 — 조회수·좋아요 수

이슈: https://github.com/kanziman/NexusWiki/issues/143

- [x] 2.1 `apps/worker/src/worker/youtube.py`: `videos.list` 호출에 `part=statistics` 추가, `YoutubeVideo`에 `view_count: int | None`·`like_count: int | None` 추가 및 파싱
- [x] 2.2 `apps/api/src/api/routers/youtube.py`: 새 필드 통과
- [x] 2.3 `apps/dashboard/components/YoutubeVideoList.tsx`: 조회수(및 있으면 좋아요 수) 표시
- [x] 2.4 워커·대시보드 테스트 추가(정상 값, 필드 누락, 비공개로 숨김된 좋아요 수 케이스)

Given: 영상 상세에 조회수·좋아요 수가 포함될 때
When: 영상 목록을 렌더링하면
Then: 각 영상 카드에 조회수가 표시되고, 좋아요 수가 없는 영상은 해당 항목이 조용히 생략된다(0으로 표시되지 않는다)

검증: `cd apps/worker && pytest tests/test_youtube.py -k statistics` · `cd apps/dashboard && pnpm test -- YoutubeVideoList`

## 3. 채널 검색 — 구독자 수·영상 수·핸들

이슈: https://github.com/kanziman/NexusWiki/issues/144

- [x] 3.1 `apps/worker/src/worker/youtube.py`: `YoutubeChannel`에 `subscriber_count`·`video_count`·`handle` 추가(전부 optional). `search_channels()`가 `search.list` 결과의 채널 ID를 모아 `channels.list(part=snippet,statistics, id=...)` 배치 호출 1회를 이어서 실행하고 결과를 병합
- [x] 3.2 `channels.list` 호출 실패 시 통계 없이 핵심 필드만으로 채널 후보를 그대로 반환(검색 전체를 실패시키지 않음) — design.md 결정 반영
- [x] 3.3 `apps/api/src/api/routers/youtube.py`: 새 필드 통과
- [x] 3.4 `apps/dashboard/components/YoutubeChannelSearch.tsx`: 채널 카드에 구독자 수·영상 수·핸들 표시(값이 없으면 해당 배지 숨김)
- [x] 3.5 워커·대시보드 테스트 추가(정상 병합, `channels.list` 실패 시 핵심 필드만 반환, 일부 채널만 통계 없는 부분 실패)

Given: 채널 검색이 20개 후보를 반환했을 때
When: 채널 통계 배치 조회가 성공하면
Then: 각 채널 카드에 구독자 수·영상 수·핸들이 함께 표시된다
Given: 채널 통계 배치 조회가 실패했을 때
When: 검색 결과를 반환하면
Then: 통계 없이도 채널 ID·이름·설명·썸네일은 그대로 반환된다

검증: `cd apps/worker && pytest tests/test_youtube.py -k channel_stats` · `cd apps/dashboard && pnpm test -- YoutubeChannelSearch`

## 4. 채널 검색 — 정렬·언어·지역 선택

이슈: https://github.com/kanziman/NexusWiki/issues/145

- [x] 4.1 `apps/worker/src/worker/youtube.py`: `YoutubeSearchRequest`에 `order`("relevance"|"videoCount"|"viewCount", 기본 relevance)와 `relevance_language`(optional) 추가, `search_channels()`가 `search.list` 파라미터로 전달
- [x] 4.2 `apps/api/src/api/routers/youtube.py`: 새 쿼리 파라미터(`order`, `relevance_language`)를 라우트에 추가하고, 기존 캐시 키(`query, region_code, page_token`)에 `order`·`relevance_language`를 포함시켜 정렬/언어를 바꿨는데 캐시된 옛 결과가 나오지 않도록 한다
- [x] 4.3 `apps/dashboard/components/YoutubeChannelSearch.tsx`: 정렬(관련도/영상 많은 순/조회수 많은 순)·언어·국가(기존 `region_code`, 이번에 처음 노출) 드롭다운 3개 추가, 검색 요청에 포함
- [x] 4.4 워커·API·대시보드 테스트 추가(정렬 변경이 파라미터에 반영, 캐시 키가 정렬/언어별로 분리됨)

Given: 사용자가 정렬을 "영상 많은 순"으로 바꿨을 때
When: 검색을 실행하면
Then: `search.list`가 `order=videoCount`로 호출되고, 같은 키워드로 정렬을 바꾸기 전 캐시된 결과가 재사용되지 않는다

검증: `cd apps/api && pytest tests/test_youtube_router.py -k cache_key` · `cd apps/dashboard && pnpm test -- YoutubeChannelSearch`

## 5. 검증 및 스펙 동기화

이슈: https://github.com/kanziman/NexusWiki/issues/146

- [x] 5.1 워커·API·대시보드 테스트, ruff/eslint/tsc 전체 재실행 및 통과 확인 (worker 218 · API 256 · dashboard 447 전부 통과)
- [x] 5.2 `openspec validate youtube-search-metadata --strict` 통과 확인
- [x] 5.3 `/opsx:sync`로 `openspec/specs/youtube-channel-import`에 MODIFIED 반영
