## Why

현재 위키 라이브러리에서는 컴파일된 다수의 위키 문서를 검증(`verified`)하거나 외부 공개 발행(`published`)하려면 개별 문서 상세 페이지에 일일이 진입하여 하나씩 처리해야 하는 번거로움이 있습니다. 대량의 지식 문서를 효과적으로 검증하고 외부에 한 번에 배포할 수 있는 일괄(Bulk) 검증 및 일괄 발행 기능이 필요합니다.

## What Changes

- **백엔드 일괄 검증 API**: `POST /workspaces/{workspace_id}/wiki/bulk-verify` 추가 (선택된 여러 위키 문서의 검증 상태를 `verified`로 일괄 갱신 및 감사 기록)
- **백엔드 일괄 공개 발행 API**: `POST /workspaces/{workspace_id}/wiki/bulk-publish` 추가 (선택된 검증 문서들을 `wiki_page_publications`에 일괄 스냅샷 upsert)
- **프론트엔드 다중 선택 및 일괄 액션 UI**:
  - `WikiLibrary.tsx`에 위키 문서 목록 다중 선택 체크박스(전체 선택 / 개별 선택) 지원
  - 선택 항목 존재 시 상단 플로팅/툴바 액션 바에 `[선택한 N개 일괄 검증]`, `[선택한 N개 일괄 발행]`, `[선택 해제]` 버튼 제공
  - 일괄 작업 성공 시 결과 토스트 알림 및 로컬 목록 상태 즉시 동기화

## Capabilities

### New Capabilities
<!-- 없음 -->

### Modified Capabilities
- `knowledge-quality`: 다수의 위키 문서를 한 번에 검증(`verification_status = 'verified'`)하고 요청자 감사 기록을 일괄 적용하는 요구사항 추가.
- `public-sharing`: 다수의 검증 완료된 위키 문서를 한 번에 `wiki_page_publications`에 스냅샷 등록/발행하는 일괄 발행 요구사항 추가.

## Impact

- `apps/api/src/api/routers/wiki.py`: `POST /bulk-verify`, `POST /bulk-publish` 엔드포인트 추가
- `apps/dashboard/components/WikiLibrary.tsx`: 체크박스 선택 상태 관리 및 일괄 액션 툴바 UI 추가
- `apps/dashboard/lib/wiki-publication.ts`: 일괄 발행 및 일괄 검증 클라이언트 헬퍼 추가
- `openspec/specs/knowledge-quality/spec.md`, `openspec/specs/public-sharing/spec.md`: 델타 스펙 반영
