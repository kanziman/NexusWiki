# Spec Conformance 리뷰 — retire-byok r1

- 판정: pass
- 대상: 브랜치 `fix/provider-credit-exhausted`의 uncommitted 워킹트리 변경 (`git diff` — 아직 커밋 전). HEAD `3a960c2f43f0f844bf0c859e995595dcf4aaa722`
- 일시: 2026-09-10T00:00:00Z

## 시나리오 판정

REMOVED Requirement 두 건은 Given/When/Then Scenario 없이 Reason/Migration만 갖는다(OpenSpec REMOVED 델타 관례). 따라서 "철회 대상 동작이 실제로 더 이상 존재하지 않는가"를 판정 기준으로 삼았다 — 즉 제거 전 스펙이 약속했던 각 관찰 가능한 동작(무제한 표시, BYOK 입력 UI, `-1` cap/remaining)이 코드 경로에서 완전히 사라졌는지 확인했다.

| Requirement / 철회 대상 동작 | 결과 | 증거 |
| --- | --- | --- |
| usage-guardrails / "BYOK unlimited quota and limit modal integration" — 크레딧 한도 모달의 BYOK 유도 문구·버튼 | 충족(제거됨) | `apps/dashboard/components/CreditLimitModal.tsx` diff에서 "내 OpenRouter API 키 등록 시 무제한 사용" 블록과 "내 API 키 등록 (무제한)" 버튼 삭제, `KeyRound`/`Zap` import 삭제. "설정에서 사용량 확인" 링크로 대체. 테스트 `apps/dashboard/tests/CreditLimitModal.test.tsx:22-27`가 `/무제한/` 텍스트 부재를 명시적으로 assert. `npx vitest run tests/CreditLimitModal.test.tsx` 통과 확인 |
| usage-guardrails / "모든 워크스페이스는 예외 없이 표준 월간 예산 상한을 따른다" (Migration 절 서술) | 충족 | `apps/api/src/api/routers/jobs.py:209-224` `has_custom_key` 분기·`cap_micros=-1`/`remaining_micros=-1` 산출 로직 완전 제거, 항상 `monthly_budget_micros` 기준 계산. 회귀 테스트 `apps/api/tests/test_jobs_router.py:186-205` — `set_workspace_budget(owner, 7_000_000)` 세팅 후 `cap_micros == 7_000_000`, `remaining_micros == 7_000_000` assert. 로컬 스택 대상 `pytest tests/test_jobs_router.py -k budget` 2건 실제 통과 확인(RLS 경유 실제 왕복) |
| workspace-settings / "BYOK custom AI API key management" — 커스텀 API 키 입력·저장·삭제·마스킹·배지 UI | 충족(제거됨) | `apps/dashboard/components/WorkspaceGeneralSettings.tsx` diff에서 `maskApiKey`, `handleSaveApiKey`, `handleDeleteApiKey`, "AI 모델 및 커스텀 API 키 (BYOK)" `<section>` 전체(244줄) 삭제. `initialCustomApiKey` prop과 상태(`customApiKey`, `isEditingKey`, `inputKey`, `keySaving` 등) 모두 제거. `grep`(파이썬 기반 전체 스캔)으로 파일 내 BYOK/`customApiKey` 잔존 0건 확인 |
| workspace-settings / "이미 등록된 커스텀 키는 마이그레이션으로 null 처리" | 충족 | `supabase/migrations/0022_retire_byok_custom_api_key.sql:6-8`에서 `update public.workspaces set custom_api_key = null where custom_api_key is not null;` 실행. 로컬 스택에 실제 적용 확인(`schema_migrations` 최신 버전 `0022`) 및 `select count(*) from workspaces where custom_api_key is not null` → `0`으로 직접 검증. 컬럼 코멘트도 "BYOK는 UI·실제 라우팅 모두 비활성 상태…"로 갱신됨(설계 Risks 절의 완화책과 일치) |
| workspace-settings / prop 전달 경로 정리 (`initialCustomApiKey`) | 충족 | `apps/dashboard/app/w/[workspaceId]/settings/page.tsx` diff — `.select("name,slug,kind,custom_api_key")` → `.select("name,slug,kind")`, `initialCustomApiKey={...}` prop 전달 삭제. `apps/dashboard/components/SettingsMembersPanel.tsx` diff — 중간 전달 지점의 prop 정의·전달 모두 삭제 |
| 컴포넌트 트리 전반 — "무제한" 표현/BYOK UI 잔존 여부 (검토자 추가 확인) | 충족 | `AccountMenu.tsx`·`WorkspaceSidebar.tsx`에서 `budget.cap_micros < 0` 분기(BYOK "무제한 이용 중" 카드/위젯) 완전 삭제, `cap_micros > 0` 케이스만 남김(잔존 `Zap` import는 무료 크레딧 카드용 아이콘 재사용이며 BYOK와 무관 — 코드 확인). 저장소 전역 파이썬 스캔(`.ts/.tsx/.py/.sql`)에서 프로덕션 코드에 `BYOK`/`customApiKey`/`custom_api_key` 활성 참조 0건(테스트 주석의 "폐지됐다" 서술과 `apps/worker/src/worker/errors.py` 독스트링, `0020`/`0022`/`0021` 마이그레이션의 역사적 언급만 남음) |
| API — `/workspaces/{id}/budget`가 `custom_api_key` 존재 여부와 무관하게 항상 실제 상한 반영 | 충족(단, 테스트는 "custom_api_key가 실제로 값이 있는 상태"까지는 직접 재현하지 않음 — 아래 참고) | `jobs.py:212`에서 `columns="monthly_budget_micros"`로 `custom_api_key` 컬럼 자체를 더 이상 select하지 않으므로, 값이 있든 없든(마이그레이션으로 전부 null이긴 하나) 분기 로직 자체가 코드에서 사라짐. 회귀 테스트는 이 사실(코드 부재)을 조회하지 않고 표준 케이스의 산출값만 검증 — 참고 항목으로만 기록, 등급에는 영향 없음(코드 경로 부재가 곧 구현 확인이며 테스트 부재가 아님) |
| AccountMenu/WorkspaceSidebar 방어적 회귀 — API가 실수로 음수 `cap_micros`를 다시 돌려줘도 UI가 BYOK UI를 렌더링하지 않는가 | 충족 | `AccountMenu.test.tsx:136-153`, `WorkspaceSidebar.test.tsx:274-288`이 `apiFetch` 목을 `cap_micros: -1`로 세팅한 채로 "내 API 키 연결됨"/"무제한 이용 중" 텍스트의 **부재**를 `queryByText(...).not.toBeInTheDocument()`로 assert — 단순 케이스 삭제가 아니라 실제 회귀 방지 어서션 |
| design.md Non-Goal — BYOK 실제 라우팅 미구현, 컬럼 미삭제, `monthly_budget_micros` 상한 재설계 없음 | 충족 | `git status --porcelain supabase/migrations/` 확인 결과 `0022` 외 신규/수정 마이그레이션 없음(0009/0010 예산 판정 SQL 불변). `0022`는 `update`·`comment on column`만 포함, `drop column` 없음. `apps/worker/src/**/*.py` 전체 스캔에서 `custom_api_key` 참조 0건(워커 변경 없음이 proposal.md Impact와 일치) |

## 조치가 필요한 항목

없음.

## 판정 근거

두 REMOVED Requirement가 약속했던 모든 관찰 가능한 동작(BYOK 입력/저장/삭제 UI, "무제한" 배지·토스트·위젯 4곳, `cap_micros=-1`/`remaining_micros=-1` API 표시)이 코드에서 실제로 제거됐고, 각 제거는 실행 가능한 테스트(`vitest`, `pytest` — 로컬 Supabase 스택 대상 실제 RLS 왕복 포함)로 뒷받침된다. 남겨야 할 요구사항("User-facing free credit quota feedback and limit modal"의 "설정에서 사용량 확인" 링크)은 의도대로 유지됐고 별도 테스트로 검증된다. design.md의 두 Non-Goal(BYOK 라우팅 미구현, 컬럼 미삭제)도 실제 diff에서 확인된다. tsc/eslint/ruff 모두 통과, `openspec validate --specs --strict` 35/35 통과. 조용한 범위 축소·미검증 완료 주장·스펙 밖 동작 셋 중 어느 것도 발견되지 않았다.
