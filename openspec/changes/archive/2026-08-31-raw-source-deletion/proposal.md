# Proposal: raw-source-deletion

## Why
현재 워크스페이스에 업로드된 원문 소스(PDF, 텍스트, Markdown 등)를 소유자가 직접 영구 삭제할 수 있는 기능이 부재합니다. 불필요하거나 잘못 등록된 소스를 정리하고, 관련 청크와 벡터 색인을 정리할 수 있는 안전한 삭제 수단이 필요합니다.

## What Changes
- 백엔드 `DELETE /workspaces/{workspace_id}/sources/{source_id}` 라우터 추가:
  - 워크스페이스 소유자(Owner) 권한 검증
  - `raw_sources` 삭제 (PostgreSQL RLS `raw_sources_delete_owner` 및 외래키 `ON DELETE CASCADE`로 `source_chunks`, `source_embeddings` 자동 정리)
  - Supabase Storage에 저장된 원본 파일(있는 경우) 정리
- 대시보드 UI 연동:
  - 소스 상세 화면(`SourceDetailContent`) 상단에 `[🗑️ 소스 삭제]` 버튼 및 영구 삭제 확인 모달 추가 (소유자 권한 시에만 노출)
  - 소스 목록 화면(`SourcesList`) 각 항목에 소유자 전용 `[삭제]` 액션 및 확인 모달 연동
  - 삭제 완료 시 토스트 피드백 표시 및 소스 목록으로 안전하게 라우팅

## Capabilities

### Modified Capabilities
- `source-management-wiki`: 원문 소스 영구 삭제(Owner-only Raw source deletion) 요구사항 및 CASCADE 연쇄 정리 시나리오 추가

## Impact
- `apps/api/src/api/routers/sources.py`: `DELETE /workspaces/{workspace_id}/sources/{source_id}` 엔드포인트 추가
- `apps/dashboard/components/SourceDetailContent.tsx`: 소스 삭제 버튼 및 확인 모달 연동
- `apps/dashboard/components/SourcesList.tsx`: 소스 목록 내 삭제 액션 연동
- `openspec/specs/source-management-wiki/spec.md`: 소스 삭제 요구사항 반영
