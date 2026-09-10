## 1. 키워드 채널 검색

GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/126

**AC:** Given 워크스페이스 멤버가 LNB에서 YouTube 수집 페이지를 열었을 때, When 키워드를 입력해 검색하면, Then 채널 후보가 채널명·설명·썸네일과 함께 표시되고 결과가 더 있으면 다음 페이지를 이어서 볼 수 있다. 같은 키워드를 다시 검색하면 외부 검색 호출이 발생하지 않고, 쿼터가 소진된 상태에서는 "결과 없음"이 아니라 소진 사유가 표시된다.

**검증:** `uv run pytest apps/api/tests -k youtube` · `pnpm --dir apps/dashboard test -- tests/YoutubeChannelSearch.test.tsx` · `pnpm --dir apps/dashboard lint typecheck`

- [x] 1.1 워커에 `YOUTUBE_API_KEY`와 채널 검색 내부 리스너를 추가한다 — provider 키는 워커만 소유한다(design D5, 기존 `LLM_STREAM_INTERNAL_*` 패턴).
- [x] 1.2 API에 채널 검색 엔드포인트를 추가한다 — 키워드·지역·페이지 토큰을 받아 워커 내부 리스너로 프록시하고, 채널 후보와 다음 페이지 토큰을 돌려주며, 비멤버는 거부한다. `ApiSettings`에는 내부 호출자 토큰만 두고 허용 목록에 근거와 함께 등록한다.
- [x] 1.3 `(질의, regionCode, pageToken)` 키의 TTL 메모리 캐시를 API에 붙여 동일 검색이 외부 호출과 내부 홉을 모두 건너뛰게 한다(design D3).
- [x] 1.4 외부 쿼터 소진을 빈 결과와 구분되는 사유로 매핑한다 — 0건 응답으로 위장하지 않는다.
- [x] 1.5 LNB에 진입점을 더하고 `/w/[workspaceId]/youtube` 페이지에 검색 입력·결과 목록·더 보기를 구현한다.
- [x] 1.6 쿼터 소진 사유를 사용자가 이해할 수 있는 안내로 표시한다.

## 2. 채널 영상 목록과 단일 영상 수집 종단간

GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/127

⚠️ 이 슬라이스가 design의 최대 리스크(자막 공급자의 데이터센터 IP 차단)를 처음 만난다. 어댑터 경계를 여기서 확립한다.

**AC:** Given 검색 결과에서 채널 하나를 선택했을 때, When 그 채널의 영상 목록에서 영상 한 편을 골라 수집하면, Then 해당 영상의 자막이 원문 소스 본문이 되어 기존 파이프라인을 통과하고 위키 문서까지 생성되며, 그 인용은 저장된 자막의 char 구간으로 원문 영상까지 되짚을 수 있다.

**검증:** `uv run pytest apps/api/tests apps/worker/tests -k "youtube or transcript"` · `pnpm --dir apps/dashboard test -- tests/YoutubeVideoList.test.tsx`

- [ ] 2.1 채널 영상 목록 엔드포인트를 추가한다 — `channels.list`로 uploads 재생목록을 얻고 `playlistItems.list`로 페이징한다(design D4, `search.list` 금지).
- [ ] 2.2 `TranscriptProvider` 어댑터 경계를 워커에 정의한다 — 자막 본문을 돌려주거나 구분 가능한 사유로 실패한다(design D2). 스펙·태스크에 공급자 이름을 남기지 않는다.
- [ ] 2.3 `parse` 핸들러에 `transcript` 분기를 추가해 어댑터로 본문을 채운다. URL 분기의 `fetch_source` 경로와 섞지 않는다.
- [ ] 2.4 선택 영상 등록 경로를 추가한다 — `source_type='transcript'`, `content=""` sentinel, `metadata{video_id, channel_id, url}`, 중복 키는 정규화된 영상 URL 해시(design D1). 기존 `_insert_and_enqueue`를 재사용한다.
- [ ] 2.5 채널 선택 시 영상 목록(제목·게시일·길이·썸네일)과 더 보기를 렌더하고, 영상 한 편을 수집할 수 있게 한다.

## 3. 다중 선택 일괄 등록과 영상별 결과

GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/128

**AC:** Given 영상 목록에서 여러 편을 선택했을 때, When 일괄 수집을 실행하면, Then 선택한 영상만 각각 하나의 원문 소스로 등록되고 영상별 결과(등록됨·이미 수집됨)가 돌아오며, 이미 수집한 영상은 파생 레코드를 늘리지 않는다. 타 워크스페이스를 지정한 요청은 아무 소스도 만들지 않고 거부된다.

**검증:** `uv run pytest apps/api/tests -k "youtube_batch or already_collected"` · `pnpm --dir apps/dashboard test -- tests/YoutubeBatchImport.test.tsx`

- [ ] 3.1 등록 엔드포인트를 다중 영상으로 확장하고 영상별 결과를 돌려준다 — 한 건의 결과가 다른 건의 결과를 가리지 않는다.
- [ ] 3.2 이미 수집된 영상을 구분 가능한 결과로 돌려준다(기존 `SourceAlreadyIngested` 계약 재사용).
- [ ] 3.3 워크스페이스 경계를 검증한다 — 요청자가 속하지 않은 워크스페이스 지정 시 소스를 만들지 않고 거부한다(RLS 0행 → 403 매핑).
- [ ] 3.4 예산 상한에 닿은 경우 기존 402 경로와 `CreditLimitModal`이 그대로 동작하는지 확인한다.
- [ ] 3.5 영상 다중 선택 UI와 일괄 수집 실행, 영상별 결과 요약을 구현한다.

## 4. 자막 실패 사유 구분과 부분 실패 격리

GitHub sub-issue: https://github.com/kanziman/NexusWiki/issues/129

**AC:** Given 일괄 수집한 영상 중 일부가 자막을 얻을 수 없을 때, When 파이프라인이 그 영상들을 처리하면, Then 각 영상은 자막 없음·접근 불가·공급자 일시 장애가 구분되는 사유로 끝나고, 재시도가 무의미한 사유는 재시도를 소진하지 않으며, 같은 배치의 나머지 영상은 영향 없이 위키까지 완료된다.

**검증:** `uv run pytest apps/worker/tests -k "transcript_failure or partial"` · `openspec validate youtube-channel-import --strict`

- [ ] 4.1 어댑터 실패를 최소 3종(자막 없음 · 접근 불가 · 공급자 일시 장애)으로 구분해 올린다.
- [ ] 4.2 재시도가 무의미한 사유는 `max_attempts`를 소진하지 않고 종결시킨다 — 자막 없는 영상이 헛도는 것을 막는다(design D2).
- [ ] 4.3 한 영상의 실패가 같은 배치의 다른 영상 처리를 막지 않는지 검증한다.
- [ ] 4.4 원문 소스 목록에서 실패 사유를 사용자가 이해할 수 있는 문구로 표시하고, 실패한 소스를 지울 수 있게 한다.
