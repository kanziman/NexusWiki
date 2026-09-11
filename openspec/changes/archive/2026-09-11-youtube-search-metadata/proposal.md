## Why

YouTube Data API v3가 채널 검색·영상 목록 조회 시점에 이미 제공하는 필드 중 상당수를 이 앱이 요청조차 하지 않고 있다. 그중 하나(`contentDetails.caption`)는 이 기능의 핵심 실패 모드(자막 없는 영상 선택 → `no_transcript` 실패)를 사전에 막을 수 있는데도 버려지고 있다. 추가 쿼터 비용이 0이거나 무시할 수준(+1유닛)인 필드들이라 지금 확장한다.

## What Changes

- `videos.list` 응답의 `contentDetails.caption`을 읽어 `YoutubeVideo`에 노출 — 영상 목록에서 자막 없는 영상을 선택 전에 배지로 구분한다.
- `videos.list` 호출에 `part=statistics`를 추가해 `viewCount`·`likeCount`를 `YoutubeVideo`에 노출한다.
- 채널 검색 결과의 채널 ID(최대 20개)를 `channels.list(part=snippet,statistics)`로 배치 조회해 구독자 수·영상 수·핸들(`@customUrl`)을 `YoutubeChannel`에 추가한다.
- 채널 검색에 `order`(relevance 기본값·videoCount·viewCount)·`relevanceLanguage`·`region_code`(기존 API 파라미터, 지금까지 프론트엔드가 보내지 않아 항상 서버 기본값 `KR`로 고정돼 있었다) 드롭다운을 UI에 노출한다.

## Capabilities

### New Capabilities

(없음)

### Modified Capabilities

- `youtube-channel-import`: "Keyword channel discovery" 요구사항에 정렬·언어·국가 선택과 채널 통계(구독자 수·영상 수·핸들) 노출을 추가한다. "Channel video browsing" 요구사항에 자막 가용 여부와 조회수·좋아요 수 노출을 추가한다.

## Impact

- **워커**: `apps/worker/src/worker/youtube.py` — `YoutubeChannel`·`YoutubeVideo` 모델에 필드 추가, `search_channels()`에 정렬/언어 파라미터 및 채널 배치 조회 추가, `list_channel_videos()`의 `videos.list` 호출에 `part=statistics` 추가 및 caption 파싱 추가.
- **API**: `apps/api/src/api/routers/youtube.py` — 새 쿼리 파라미터(`order`, `relevance_language`) 통과, 기존 `region_code`는 이미 있으므로 변경 없음.
- **대시보드**: `YoutubeChannelSearch.tsx`(정렬·언어·국가 드롭다운, 채널 카드에 구독자 수 등 표시), `YoutubeVideoList.tsx`(자막 배지, 조회수 표시).
- **쿼터**: 채널 검색당 +1유닛(채널 배치 조회). 영상 목록 조회는 유닛 변화 없음(같은 호출에 `part`만 추가).
- **테스트**: 위 파일들을 다루는 기존 테스트에 새 필드·파라미터 케이스 추가.
