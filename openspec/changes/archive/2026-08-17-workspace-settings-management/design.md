# Design: workspace-settings-management

## Context & Invariants

1. **테넌트 격리 및 RLS**:
   - `workspaces` UPDATE/DELETE는 owner 전용 RLS(`workspaces_update_owner`)에 의해 보호된다.
   - `workspace_members` 초대는 owner 전용 RPC `invite_workspace_member`에 의해 제어된다.
2. **UI Role Gating**:
   - `WorkspaceGeneralSettings`: `currentRole === "owner"`일 때만 수정 가능.
   - `SettingsMembersPanel`: `canInvite = currentRole === "owner"`일 때만 `InviteForm`을 렌더링.
   - `canViewOperations = currentRole === "owner" || currentRole === "editor"`일 때만 `운영 현황` 탭 노출.
3. **디자인 토큰**:
   - v2 디자인 시스템 (`nexuswiki-design-system.css`) 토큰을 준수하며, 이모지를 사용하지 않는다 (불변식 §7.2 Zero Emojis).

## Component Architecture

```
apps/dashboard/app/w/[workspaceId]/settings/page.tsx (Server Component)
└── SettingsMembersPanel.tsx (Client Component - 3 Tabs)
    ├── Tab "general": WorkspaceGeneralSettings.tsx (New)
    ├── Tab "members": MembersList.tsx + (owner only: InviteForm.tsx)
    └── Tab "operations": OperationsPanel.tsx (owner/editor only)
```

## State & Data Flow

- **일반 설정 (`WorkspaceGeneralSettings`)**:
  - Props: `workspaceId`, `initialName`, `initialSlug`, `isOwner`
  - Supabase client로 `workspaces` 테이블 업데이트 (`name`, `slug`).
  - Validation: 이름(1~100자), 슬러그(`^[0-9a-z가-힣][0-9a-z가-힣-]*$`, 1~80자).
- **멤버 설정 (`SettingsMembersPanel`)**:
  - `activeTab`: `"general" | "members" | "operations"`.
  - `currentRole`: `"owner" | "editor" | "viewer"`.
