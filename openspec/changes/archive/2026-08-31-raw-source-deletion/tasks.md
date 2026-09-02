## 1. 백엔드 API 구현

- [x] 1.1 `apps/api/src/api/routers/sources.py`에 `DELETE /workspaces/{workspace_id}/sources/{source_id}` 라우터 추가
- [x] 1.2 `apps/api/tests/test_sources_router.py`에 원문 소스 삭제(소유자 성공, 일반 멤버 403 거부, 비존재 404) 테스트 추가

## 2. 프론트엔드 UI 연동

- [x] 2.1 `apps/dashboard/components/SourceDetailContent.tsx`에 소유자 전용 `[🗑️ 소스 삭제]` 버튼 및 영구 삭제 확인 모달 연동
- [x] 2.2 `apps/dashboard/components/SourcesList.tsx`에 소스 목록 내 삭제 액션 및 모달 연동
- [x] 2.3 프론트엔드 단위/컴포넌트 테스트 추가 및 검증 (`pnpm test`)

## 3. 검증 및 스펙 아카이브

- [x] 3.1 `openspec validate raw-source-deletion --strict` 검증 및 delta spec 반영 후 아카이브
