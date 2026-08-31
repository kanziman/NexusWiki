## Context
PostgreSQL DB 레벨에는 이미 `0004_rls_policies.sql`에 `raw_sources_delete_owner` 정책이 적용되어 있고, `0002_search_schema.sql`에 `source_chunks`가 `raw_sources`와 `on delete cascade`로 묶여 있습니다.
이번 변경은 이를 안전하게 호출할 수 있는 백엔드 API 라우터(`DELETE /workspaces/{workspace_id}/sources/{source_id}`)와 대시보드 UI 연동을 제공합니다.

## Goals / Non-Goals

**Goals:**
- 백엔드 `DELETE /workspaces/{workspace_id}/sources/{source_id}` 엔드포인트 구현:
  - 호출자 권한 확인 (UserDb를 통해 실행하여 RLS 정책 검증 및 0행 삭제 시 WorkspaceForbidden 처리)
  - 소스가 파일인 경우 Supabase Storage 버킷 내 원본 파일 객체 안전하게 제거
- 프론트엔드 UI:
  - `SourceDetailContent.tsx`: 헤더 우측에 `[🗑️ 소스 삭제]` 버튼 및 Radix Dialog 기반 확인 모달 연동 (소유자 전용)
  - 삭제 완료 시 토스트 알림 노출 후 `/w/{workspaceId}/sources`로 리다이렉트
  - `SourcesList.tsx`: 소스 목록에서 삭제 후 로컬 상태 갱신

**Non-Goals:**
- 소스 삭제 시 위키 문서의 즉각적 재컴파일 파이프라인 자동 실행 (초기 스펙에 따라 레드링크 전환 및 기존 위키 보존, 향후 재컴파일 잡 연계로 분리)

## Decisions

- **D-1: RLS 기반 삭제 및 반환 행 검증**
  - 결정: `_user_db(request, credentials).delete("raw_sources", match={"id": source_id, "workspace_id": workspace_id})`를 호출하고 삭제된 행 수가 0개이면 `WorkspaceForbidden` 또는 404를 반환한다.
  - 근거: `service_role`을 쓰지 않고 요청자 JWT의 RLS를 온전히 타게 하여 테넌트 격리와 소유자 권한을 보장한다.
- **D-2: Storage 파일 정리**
  - 결정: 소스 삭제 전 또는 직후 `storage_path`가 존재하는 파일 소스인 경우 `UserStorage`를 통해 버킷 내 파일을 삭제한다.
- **D-3: 프론트엔드 소유자 권한 및 확인 모달**
  - 결정: `useWorkspace()`의 `isOwner` 또는 `role === "owner"`인 사용자에게만 삭제 버튼을 노출하고, 실수 방지를 위해 확인 모달(Dialog)을 띄운다.

## Risks / Trade-offs

- [Risk] 소스 삭제 시 해당 소스를 인용하던 위키의 Citation 링크가 깨질 수 있음 → Mitigation: DB 외래키가 `on delete set null` 또는 인용 좌표 기준으로 렌더링되므로 앱 크래시 없이 미완성 백로그로 안전하게 처리됨.
