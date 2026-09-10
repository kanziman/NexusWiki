## 1. DB 마이그레이션 — 기존 커스텀 키 데이터 정리

이슈: https://github.com/kanziman/NexusWiki/issues/133

- [x] 1.1 `supabase/migrations/0022_retire_byok_custom_api_key.sql` 작성: `update public.workspaces set custom_api_key = null where custom_api_key is not null;` + 컬럼 코멘트를 "BYOK는 UI·실제 라우팅 모두 비활성 상태 — 워커가 읽지 않는다"로 갱신
- [x] 1.2 로컬 스택에 마이그레이션 적용 후 `custom_api_key`가 모두 null인지 확인

## 2. API — 예산 표시 정직화

이슈: https://github.com/kanziman/NexusWiki/issues/134

- [x] 2.1 `apps/api/src/api/routers/jobs.py`의 `workspace_budget`에서 `has_custom_key` 분기 제거 — 항상 `monthly_budget_micros` 기준으로 `cap_micros`/`remaining_micros` 계산
- [x] 2.2 관련 API 테스트에서 BYOK 무제한 케이스 제거, 표준 예산 케이스로 대체

## 3. 대시보드 — BYOK UI 제거

이슈: https://github.com/kanziman/NexusWiki/issues/135

- [x] 3.1 `WorkspaceGeneralSettings.tsx`에서 커스텀 API 키 입력/저장/삭제 UI, "무제한" 토스트, 상태 배지 제거
- [x] 3.2 `app/w/[workspaceId]/settings/page.tsx`에서 `initialCustomApiKey` prop 전달 제거 (중간 전달 지점 `SettingsMembersPanel.tsx` 포함)
- [x] 3.3 `CreditLimitModal.tsx`에서 "내 API 키 등록 시 무제한 사용" 안내와 유도 버튼 제거 (설정 링크 자체는 "사용량 확인" 동선으로 유지 — usage-guardrails의 남은 요구사항)
- [x] 3.4 `AccountMenu.tsx`에서 BYOK "무제한 이용 중" 카드를 제거하고 항상 무료 크레딧 잔여량 카드로 대체
- [x] 3.5 `WorkspaceSidebar.tsx`에서 BYOK "무제한 이용 중" 미니 위젯을 제거하고 항상 무료 크레딧 위젯으로 대체
- [x] 3.6 위 컴포넌트를 다루는 기존 테스트에서 BYOK 관련 케이스 제거/수정

## 4. 검증 및 스펙 동기화

이슈: https://github.com/kanziman/NexusWiki/issues/136

- [x] 4.1 워커·API·대시보드 테스트, ruff/eslint/tsc 전체 재실행 및 통과 확인 (worker 212 · API 254 · dashboard 433 전부 통과)
- [x] 4.2 `openspec validate retire-byok --strict` 통과 확인
- [x] 4.3 `/opsx:sync`로 `openspec/specs/usage-guardrails`, `openspec/specs/workspace-settings`에 REMOVED 반영
