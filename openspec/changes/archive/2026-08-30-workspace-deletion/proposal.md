# Proposal: Workspace Deletion

## Why

사용자가 더 이상 사용하지 않는 워크스페이스를 정리할 수 있는 방법이 현재 대시보드 UI에 제공되지 않습니다. DB 스키마와 RLS 정책(`workspaces_delete_owner`) 및 CASCADE 외래키 제약은 이미 준비되어 있으나, 소유자(Owner)가 프론트엔드에서 안전하게 워크스페이스를 삭제하고 전환할 수 있는 '위험 구역(Danger Zone)' UI가 필요합니다.

## What Changes

- [설정 > 기본 정보] 화면 하단에 **'위험 구역 (Danger Zone)'** 섹션 및 **'워크스페이스 삭제'** 카드 추가
- 오직 워크스페이스 **소유자(Owner)**에게만 삭제 카드 및 버튼 활성화 (비소유자에게는 비활성화/안내 문구)
- 실수로 인한 영구 삭제를 방지하기 위해 **워크스페이스 이름을 정확히 입력해야 삭제 버튼이 활성화되는 확인 모달** 제공
- 워크스페이스 삭제 성공 시 Supabase 클라이언트를 통해 `DELETE /workspaces`를 수행하고, 남은 다른 워크스페이스가 있으면 해당 워크스페이스로 이동하고, 마지막 워크스페이스인 경우 새 워크스페이스 생성/온보딩 화면으로 안전하게 리다이렉트

## Capabilities

### New Capabilities
<!-- 없음 -->

### Modified Capabilities
- `workspace-settings`: 소유자의 워크스페이스 삭제 및 안전 확인 모달 요구사항 추가

## Impact

- **UI 컴포넌트**: `apps/dashboard/components/WorkspaceGeneralSettings.tsx`, 관련 스타일 및 테스트
- **DB/RLS**: 기존 `workspaces_delete_owner` RLS 정책 및 CASCADE 제약 활용 (신규 마이그레이션 불필요)
- **사용자 흐름**: 삭제 완료 후 워크스페이스 전환 및 라우팅 처리
