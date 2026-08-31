## Context

현재 위키 검증(`PATCH /workspaces/{workspace_id}/wiki/{wiki_id}/verify`)과 공개 발행(`PUT /workspaces/{workspace_id}/wiki/{wiki_id}/publication`)은 단일 문서 단위로만 처리됩니다. 위키 라이브러리(`WikiLibrary.tsx`)는 카드/리스트 뷰를 제공하지만 다중 선택 인터랙션이 없습니다.

## Goals / Non-Goals

**Goals:**
- 백엔드에 `bulk-verify` 및 `bulk-publish` API 엔드포인트 제공.
- RLS 기반 에디터/소유자 권한 격리 및 감사 추적(`verified_by`, `published_by`) 유지.
- `WikiLibrary.tsx`에서 다중 선택 체크박스, 선택 상태 관리, 일괄 검증/발행 액션 바 및 즉각적인 UI 반영 지원.

**Non-Goals:**
- 미검증/충돌 상태인 문서의 강제 공개 발행 (검증 및 충돌 없음 조건을 우회하지 않음).
- 위키 문서 일괄 삭제 (본 작업 범위 외).

## Decisions

### Decision 1: 백엔드 일괄 처리 엔드포인트 분리
단일 문서 API를 클라이언트에서 수십 회 루프로 호출하는 대신, 단일 요청으로 원자적 혹은 일괄 처리할 수 있는 `POST /workspaces/{workspace_id}/wiki/bulk-verify` 및 `POST /workspaces/{workspace_id}/wiki/bulk-publish` 라우터를 추가합니다.
- *대안*: 클라이언트 루프 호출 — 네트워크 오버헤드가 크고 부분 실패 시 트랜잭션/상태 일관성 관리가 복잡해짐.

### Decision 2: 일괄 발행 시 미검증/만료 문서 필터링
일괄 발행 시 선택된 문서 중 `verification_status !== 'verified'`, `disputed === true`, `expires_at 만료` 상태인 문서는 실패로 전체 배치를 중단시키지 않고, 발행 가능한 문서만 스냅샷 처리한 뒤 발행된 문서 수와 슬러그 목록을 반환합니다.
- *대안*: 하나라도 미검증이면 전체 롤백 — 사용자 경험상 일부 미검증 문서가 섞여 있을 때 전체 작업이 차단되어 불편함.

### Decision 3: 위키 라이브러리 일괄 액션 툴바 UI
위키 문서 목록 상단에 '전체 선택' 체크박스를 제공하고, 각 카드/행에 체크박스를 배치합니다. 1개 이상 선택되면 화면 상단에 선택 개수와 함께 `[일괄 검증]`, `[일괄 발행]`, `[선택 해제]` 버튼이 포함된 툴바를 노출합니다.

## Risks / Trade-offs

- [대량 인용 스냅샷 조회 부하] → 일괄 발행 시 각 문서의 citations을 효율적으로 조회하여 스냅샷 저장.
- [권한 없는 멤버의 일괄 시도] → RLS와 라우터 핸들러에서 403 Forbidden으로 단호히 차단.
