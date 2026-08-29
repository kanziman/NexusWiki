## Why

공개 뷰어(`/p/...`), `wiki_page_publications` 사이드카, 워크스페이스 공개 킬스위치는 이미 있다. 위키 상세 리더에는 검증된 문서를 발행하고 공개 링크를 복사하거나 발행을 취소하는 표면이 없어, 준비된 발행 계약을 멤버가 사용할 수 없다.

GitHub umbrella: https://github.com/kanziman/NexusWiki/issues/82

## What Changes

- 위키 상세 리더(`WikiPageContent`) 헤더에 editor 이상용 공개 발행 컨트롤을 추가한다.
- 검증된 문서는 원클릭으로 현재 본문과 인용 출처 스냅샷을 `wiki_page_publications`에 저장한다.
- 발행된 문서는 공개 링크 복사와 발행 취소를 제공한다.
- 미검증 문서와 viewer는 발행 컨트롤을 쓸 수 없다.

## Capabilities

### New Capabilities

- 없음.

### Modified Capabilities

- `public-sharing`: 위키 리더에서 검증된 문서의 공개 발행·링크 복사·발행 취소 요구사항을 추가한다.

## Impact

- `apps/api`: 요청자 JWT 기반 위키 발행/취소 엔드포인트
- `apps/dashboard`: `WikiPageContent` 헤더 컨트롤, 위키 상세 라우트·ContentViewer 초기 발행 상태
- 공개 `/p/` 본문 조판을 내부 위키 리더와 맞춘다. 킬스위치·공개 셸은 재구현하지 않는다.
