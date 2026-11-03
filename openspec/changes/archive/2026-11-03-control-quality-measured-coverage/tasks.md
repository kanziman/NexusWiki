# Tasks — control-quality-measured-coverage

- Umbrella Issue: https://github.com/kanziman/NexusWiki/issues/215

## 1. 품질 탭에서 측정된 데이터와 미측정 데이터를 구분한다 (https://github.com/kanziman/NexusWiki/issues/216)

의존성: 없음. 예상: 0.5일.

- [x] 1.1 `0036` 마이그레이션, 품질 API, 품질 패널을 연결해 답변 턴과 구조화 호출의 측정 건수를 전체 건수와 함께 표시하고, 위반·수리·대체·오류 지표를 측정된 데이터로 한정한다. 측정 건수가 0인 경로는 측정 기록 없음으로 표시한다.

Given 답변 턴 6건 중 4건에만 품질 기록이 있고 구조화 호출 2건 중 1건에만 `policy_version`이 있을 때, When editor가 품질 탭을 열면, Then 측정 4건 / 전체 6건과 측정 1건 / 전체 2건이 표시되고 지표는 측정된 데이터만 집계한다.
Given 턴은 있지만 품질 기록이 모두 없거나 형식이 잘못됐을 때, When 품질 탭을 열면, Then 위반 지표 대신 측정 기록 없음이 표시되고 조회는 실패하지 않는다.
Given viewer 또는 비멤버일 때, When 품질 API를 호출하면, Then viewer는 본인 Ask 측정 건수만 받고 수집 집계는 받지 못하며, 비멤버는 HTTP 403을 받는다.

검증: `uv run pytest apps/api/tests/test_control_router.py`, `cd apps/dashboard && npx vitest run tests/ControlRoom.test.tsx`, 로컬 스택 마이그레이션 적용

## 2. 품질 탭과 리스크 탭에 집계 기준을 표시한다 (https://github.com/kanziman/NexusWiki/issues/217)

의존성: 1. 예상: 0.5일.

- [x] 2.1 품질 탭의 답변·호출 묶음에 최근 N일, 근거 묶음에 전체 페이지 기준을 표시하고, 리스크 탭을 최근 N일 지표와 현재 상태 지표로 나눠 표시한다.

Given 데이터가 있는 품질 탭, When 멤버가 화면을 보면, Then 묶음별 기간 기준이 화면 텍스트로 보인다.
Given 리스크 탭, When 멤버가 화면을 보면, Then 개정·승인 반영·거부는 최근 N일로, 승인 대기·반영 중은 현재 상태로 구분되고 viewer에게 승인 버튼과 본문은 없다.

검증: `cd apps/dashboard && npx vitest run tests/ControlRoom.test.tsx && pnpm typecheck && pnpm lint`

## 3. 운영 문서를 실제 상태로 현행화한다 (https://github.com/kanziman/NexusWiki/issues/218)

의존성: 1. 예상: 0.5일 이내.

- [x] 3.1 `stack.md`의 마이그레이션 적용 표기를 `migration list --linked` 결과와 맞추고 `0036`을 추가한다. 백필 운영 문서에 `마케팅 올스타` 위임 실행 기록, 후보 파일의 외부 공유 경계, 아카이브 후 계약 경로를 반영하고, 머지 전 `0036` 선적용 순서를 적는다.

Given 운영 원장이 `0035`까지 일치할 때, When `stack.md`를 읽으면, Then `0027`~`0035`에 운영 미적용 표기가 없고 `0036`만 운영 미적용으로 표시된다.
Given 백필 운영 문서, When 운영자가 읽으면, Then 2026-11-03 실행의 범위와 건수, 나머지 3개 워크스페이스의 미실행 상태, 위임 없이 에이전트가 운영에 쓰지 않는다는 경계가 확인되며 본문은 들어 있지 않다.

검증: `npx -y supabase@2.111.0 migration list --linked`, `npx --no-install openspec validate control-quality-measured-coverage --strict`

## 완료 게이트

구현 후 관련 테스트, 전체 pytest, Ruff, 대시보드 typecheck·lint·테스트를 새로 실행하고 리뷰 게이트를 최대 3라운드로 돌린다. push·PR은 사용자 요청 후 수행하며, 운영 `0036` 적용과 머지는 운영자가 한다.
