# 🤝 Handoff Document

- **작성 일시**: 2026-08-17T16:15 KST
- **브랜치**: `feat/workspace-shell-layout`
- **마지막 상태**: Phase 1: 홈 대시보드 (HOME-01 ~ HOME-06) 100% 완료

## 🎯 1. 현재 상태

마일스톤 2의 **Phase 1: 홈 대시보드 화면 구현**이 완료되었으며, 2건의 OpenSpec change 제안·구현·스펙 동기화·아카이브가 성공적으로 마무리되었습니다.

### Phase 1 구현 완료 내역

| ID | 카테고리 | 제목 | 핵심 내용 |
| --- | --- | --- | --- |
| `HOME-01` | Layout | 워크스페이스 셸 레이아웃 | v2 토큰 기반 좌측 LNB(`WorkspaceSidebar`), 반응형 셸(`WorkspaceShell`), `layout.tsx` (390~1680px 무가로스크롤) |
| `HOME-02` | Navigation | 카테고리 렌즈 필터 | `CategoryLensFilter.tsx` 5종 렌즈(전체/개념/엔티티/가이드/맵) 및 카운트 뱃지, 필터링 연동 |
| `HOME-03` | Ask UI | Ask 히어로 캔버스 | `AskHero.tsx` 다중 라인 질문 입력, 스코프 메뉴(전체/카테고리/주변), 스타터 칩 3종, `/ask` 라우팅 |
| `HOME-04` | Content | 2컬럼 지식 그리드 | `KnowledgeGrid.tsx` 컴파일된 위키 문서 피드(검증 완료 뱃지, 카테고리 표시) + 미완성 백로그 및 소스 연결 CTA |
| `HOME-05` | Navigation | 워크스페이스 스위처 | `WorkspaceSwitcher.tsx` v2 디자인 시스템 스타일링 및 새 워크스페이스 생성 링크 연동 |
| `HOME-06` | Code Fix | 어휘 정정 | `WorkspaceEntryChooser` 및 테스트 목 내 잔재 '프로젝트' 어휘 점검 및 '워크스페이스'로 통일 |

### 검증 상태

- **OpenSpec**:
  - `workspace-shell-layout` → spec sync & archive (`2026-08-17-workspace-shell-layout`)
  - `workspace-home-features` → spec sync & archive (`2026-08-17-workspace-home-features`)
- **TypeScript**: `pnpm typecheck` 통과 (`tsc --noEmit`)
- **Unit Tests**: `pnpm test` (Vitest 39개 파일, 143개 테스트 전원 통과)
- **Lint**: `pnpm lint` (ESLint 0 errors)
- **Build**: `pnpm build` (Next.js 15 production build 성공)

## 📋 2. 다음 구현 순서 (Phase 2: 워크스페이스 설정 & 멤버 관리)

1. **`SETTINGS-01`**: 설정 화면 레이아웃 (`apps/dashboard/app/w/[workspaceId]/settings/page.tsx` — 일반·멤버·운영 3탭 구조)
2. **`SETTINGS-02`**: 워크스페이스 기본 정보 편집 (`WorkspaceGeneralSettings.tsx` — 이름, 슬러그 조회/수정)
3. **`SETTINGS-03`**: 멤버 목록 & 초대 폼 (`SettingsMembersPanel.tsx`, `InviteForm.tsx`, `MembersList.tsx` — owner 게이트 버그 수정 포함)
4. **`SETTINGS-04`**: 운영 현황 카드 (`OperationsPanel.tsx` — 소스 수, 위키 수, 사용량 표시)
