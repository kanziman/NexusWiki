## Context

- `workspaces` 테이블은 `raw_sources`, `source_chunks`, `wiki_pages`, `ask_threads`, `workspace_members`, `public_sharing_settings` 등 모든 자식 테이블과 `ON DELETE CASCADE` 외래키로 묶여 있습니다.
- `0004_rls_policies.sql`에 `workspaces_delete_owner` 정책(`DELETE FROM public.workspaces WHERE public.has_workspace_role(id, 'owner')`)이 이미 존재합니다.
- `WorkspaceGeneralSettings.tsx`는 현재 `name`, `slug`, `kind`, `allowPublicSharing` 설정만을 렌더링하고 있으며, 하단에 위험 구역(Danger Zone) 컴포넌트가 부재합니다.

## Goals / Non-Goals

**Goals:**
- `WorkspaceGeneralSettings.tsx` 하단에 시각적으로 명확히 구분되는 '위험 구역' (Danger Zone) 섹션 추가
- '워크스페이스 삭제' 버튼 클릭 시 Radix Dialog 기반의 확인 모달 오픈
- 모달 내에 현재 워크스페이스 이름을 명시하고, 사용자가 입력창에 동일한 이름을 입력했을 때만 '영구 삭제' 버튼 활성화
- 소유자(`isOwner === true`)만 삭제를 실행할 수 있도록 보장 (비소유자에게는 안내 메시지와 함께 비활성화)
- 삭제 요청 시 `supabase.from("workspaces").delete().eq("id", workspaceId).select()` 실행 (RLS 0행 반환 시 차단 에러 처리)
- 삭제 성공 후 남아 있는 다른 워크스페이스(스위처 목록 기반) 중 첫 번째 워크스페이스로 이동(`router.push(workspacePath(nextId))`), 남아 있는 워크스페이스가 없으면 `/onboarding`으로 리다이렉트

**Non-Goals:**
- 백엔드/DB 마이그레이션 변경 (기존 `workspaces_delete_owner` RLS 및 CASCADE 제약 완전 재사용)
- 워크스페이스 소프트 삭제(아카이빙/복구 기능) — 본 작업은 즉시 CASCADE 영구 삭제를 다룹니다.

## Decisions

### 1. Radix Dialog 기반 확인 모달 및 이름 일치 검증
- **결정**: `Dialog.Root`, `Dialog.Overlay`, `Dialog.Content`를 사용하여 배경 블러(`backdrop-blur-md`)와 함께 렌더링하고, 입력값 `confirmInput === workspaceName`일 때만 삭제 버튼이 활성화되도록 제어합니다.
- **대안 고려**: 단순 `window.confirm()` 브라우저 팝업 — UI 일관성이 떨어지고 오클릭 위험이 큼.

### 2. 삭제 후 네비게이션 전략
- **결정**: 사용자 세션이 소속된 워크스페이스 목록을 확인하여, 현재 삭제된 워크스페이스를 제외한 다른 워크스페이스가 1개 이상이면 첫 번째 유효 워크스페이스로 이동하고, 마지막 1개였으면 `/onboarding`으로 이동합니다.
- **대안 고려**: 무조건 `/`로 이동 — `/`는 다시 첫 워크스페이스를 조회해 리다이렉트하므로 불필요한 라우트 홉이 발생할 수 있음.

## Risks / Trade-offs

- [Risk] 삭제 도중 네트워크 에러 또는 권한 오류 발생 → Mitigation: `deleting` 로딩 스피너 및 모달 내 인라인 에러 알림 표시, 실패 시 모달을 닫지 않고 사용자에게 원인 전달.
- [Risk] 마지막 워크스페이스 삭제 후 라우팅 미아 상태 → Mitigation: `supabase.from("workspace_members").select("workspace_id")` 또는 클라이언트 context를 통해 남은 워크스페이스 확인 후 `/onboarding`으로 안전하게 전환.
