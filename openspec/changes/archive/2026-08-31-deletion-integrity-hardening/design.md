## Context

현재 API는 `raw_sources` 행을 먼저 삭제한 뒤 Storage 및 `wiki_pages.sources` 정리를 최선 노력으로 실행한다. 이 방식은 외부 Storage 장애와 PostgREST 행 상한·부분 실패를 성공 응답 뒤에 숨긴다. `wiki_pages.sources`, 공개 발행 인용, Ask 인용은 JSONB라 원문 FK가 없으며, 실제 Ask 인용 화면은 `CitationSidePanel`이 아니라 `AskConversation`에서 URL 상태를 바꾸는 `ContentViewer`다.

`service_role`은 워커 전용이고 사용자 요청은 요청자 JWT를 사용해야 한다. 작업 큐는 at-least-once이며 등록된 핸들러는 멱등이어야 한다. 이 제약을 유지하면서 데이터베이스 경계와 외부 Storage 경계를 분리해야 한다.

## Goals / Non-Goals

**Goals:**

- 참조 검사, 원문 삭제, Storage 정리 잡 생성을 하나의 DB 트랜잭션으로 묶는다.
- Storage 장애가 발생해도 삭제 대상이 추적 가능하고 재시도되도록 한다.
- 사용자에게 보이는 202·409·403 응답을 단일 오류 매핑 지점에서 일관되게 제공한다.
- 실제 통합 콘텐츠 뷰어에서 삭제된 인용을 유한한 폴백 상태로 끝낸다.

**Non-Goals:**

- 참조 중인 위키를 자동 삭제하거나 자동 재컴파일하지 않는다.
- 저장된 Ask 답변의 인용 스냅샷을 새 형식으로 마이그레이션하지 않는다.
- 범용 외부 객체 삭제 프레임워크를 새로 만들지 않는다.

## Decisions

### D-1. 참조 중인 원문은 삭제하지 않는다

보안 정의자 RPC가 요청자의 owner 역할과 대상 소유권을 확인한 뒤, `wiki_pages.sources`, `wiki_page_publications.published_citations`, `ask_messages.citations` 및 비종결 파이프라인 잡을 검사한다. JSONB 참조에는 원문 FK가 없으므로 삭제와 네 참조 생산자가 같은 원문별 advisory lock을 사용하고, 생산자는 잠금을 얻은 뒤 원문 존재를 다시 확인한다. 하나라도 남으면 프로젝트 전용 SQLSTATE를 발생시키고 API가 `409 source_in_use`로 변환한다.

원문 참조를 자동 제거하고 위키를 유지하는 안은 검증 상태와 본문은 그대로 둔 채 근거만 없애므로 기각한다. 영향받은 위키를 모두 자동 삭제하는 안은 삭제 범위가 사용자의 선택보다 넓어지므로 기각한다. 참조가 해소될 때까지 삭제를 거부하는 안은 이중 인용을 보존하고 삭제 범위를 명확하게 유지하므로 선택한다.

### D-2. DB 삭제와 Storage 정리는 트랜잭션 + 작업 큐로 분리한다

RPC는 참조가 없는 원문의 `storage_path`를 payload에 담은 `delete_source_storage` 잡을 먼저 삽입하고 같은 트랜잭션에서 원문을 삭제한다. API는 잡이 내구 저장된 뒤 `202 Accepted`를 반환한다. 워커는 service role로 객체를 삭제하며 404를 성공으로 취급한다. Storage 오류는 예외로 전파하여 기존 재시도·데드레터 회계를 사용한다.

Storage를 먼저 지우고 DB를 동기 삭제하는 안은 DB 실패 시 원본 보존 계약을 깨뜨리므로 기각한다. DB를 먼저 지우고 오류를 로그로만 남기는 안은 영구 고아 객체를 만들므로 기각한다. API가 Storage 삭제 완료까지 기다리는 안은 외부 시스템과 DB를 원자화할 수 없고 요청 시간도 늘리므로 기각한다.

### D-3. 삭제 대기 객체의 사용자 읽기를 차단한다

Storage SELECT 정책은 경로의 workspace뿐 아니라 둘째 세그먼트의 raw source 행 존재도 확인한다. DB 행이 삭제되는 즉시 일반 멤버는 정리 대기 객체를 읽을 수 없고, service role 워커만 삭제를 마칠 수 있다. 업로드는 Storage 객체를 먼저 만들기 때문에 INSERT 정책에는 이 존재 조건을 추가하지 않는다.

### D-4. 실제 URL 기반 콘텐츠 뷰어가 폴백 상태를 소유한다

`SourceChunkView`는 `loading`, `ready`, `unavailable` 상태를 구분한다. 위키 인용 조회가 실패하면 Ask 대화가 `missingCitation=wiki` URL 상태로 위키 탭을 열고, 콘텐츠 뷰어가 unavailable 상태를 렌더링한다. 사용되지 않는 `CitationSidePanel`의 신규 폴백 구현과 전용 테스트는 제거한다.

## Risks / Trade-offs

- [Risk] 참조가 남은 원문을 사용자가 즉시 삭제하지 못한다. → 409 안내에서 위키·공개본·Ask 이력·진행 작업을 먼저 정리해야 함을 명확하게 설명한다.
- [Risk] Storage 정리 잡이 dead 상태가 될 수 있다. → 객체는 일반 멤버에게 즉시 보이지 않으며 기존 dead-letter 재시도 경로로 운영자가 복구한다.
- [Risk] JSONB 인용 형식이 예상을 벗어나면 참조 검사가 누락될 수 있다. → UUID 캐스팅 없이 문자열 비교를 사용하고 wiki·publication·Ask 세 경로를 통합 테스트한다.
- [Risk] 병렬 개발 브랜치의 마이그레이션 번호가 충돌할 수 있다. → 게시 전 현재 저장소의 최대 번호와 예약된 병렬 브랜치를 다시 확인하고 번호 순서를 확정한다.

## Migration Plan

1. 다음 사용 가능한 마이그레이션에 Storage 경로 파서, SELECT 정책, 원문 삭제 RPC를 추가한다.
2. API와 worker를 함께 배포하여 새 잡 type이 미등록 상태로 claim되지 않게 한다.
3. worker 배포 후 API를 배포한다. 롤백 시 API를 먼저 되돌리고, 이미 생성된 정리 잡을 처리할 수 있도록 worker 핸들러는 유지한다.
