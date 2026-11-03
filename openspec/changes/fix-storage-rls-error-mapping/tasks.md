# Tasks

Umbrella: https://github.com/kanziman/NexusWiki/issues/204

## 1. Storage 권한 거부 매핑 복구 (#205)

- [x] 1.1 업로드·삭제에서 코드 없는 본문 상태 401/403을 권한 거부로 처리하고 기존 장애 구분을 보존한다.
- [x] 1.2 단위 회귀와 실DB 교차 테넌트 테스트, 전체 pytest·lint·strict validation을 실행한다.

Given 코드 없는 Storage 거부, When 원본 업로드 또는 삭제, Then 안전한 403이며 일반 장애는 502다.

검증: `uv run pytest -q`, `uv run ruff check apps packages`, `openspec validate fix-storage-rls-error-mapping --strict`.

사용자는 2026-11-03 별도 change 수정 진행을 승인했다. 단일 호환성 슬라이스의 범위·설계·실행은 해당 승인에 따른다.

검증 결과: 단위·실DB 회귀 59 passed, 전체 pytest 1092 passed / 1 skipped(미커밋 코드의 증거 최신성 검사), Ruff·strict validation 통과. 두 리뷰 게이트 r1 모두 pass.
