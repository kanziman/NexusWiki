# Spec Conformance 리뷰 — fix-storage-rls-error-mapping r1

- 판정: pass
- 대상: `fb34a5e` 이후 작업 트리의 `apps/api/src/api/storage.py`, `apps/api/tests/test_user_storage.py` 및 이 change의 산출물
- 일시: 2026-11-03T08:52:13+09:00
- 범위: Storage 권한 거부의 오류 형식 호환성. Step 4의 다른 변경은 제외했다.

## 시나리오 판정

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Storage 권한 거부의 안전한 매핑 / 코드 없는 Storage 권한 거부 | 충족 | `apps/api/src/api/storage.py:291`이 본문 `statusCode`의 정수·문자열 401/403을 허용하며 업로드 `:264`, 삭제 `:286` 모두 같은 판정을 사용한다. `WorkspaceForbidden`은 `apps/api/src/api/errors.py:259`에서 고정된 403 본문으로 변환된다. `apps/api/tests/test_user_storage.py:263`은 두 작업과 네 상태 형식을 조합하고 공급자 경로가 예외 값·속성에 실리지 않는지 검사한다. |
| Storage 권한 거부의 안전한 매핑 / 일반 Storage 장애 | 충족 | `apps/api/src/api/storage.py:300`의 허용 목록 밖 응답은 업로드 `:272`, 삭제 `:288`에서 `StorageUnavailable`이 된다. `apps/api/src/api/errors.py:370`은 고정된 502를 반환한다. `apps/api/tests/test_user_storage.py:289`는 두 작업에서 500 본문 상태·잘못된 상태·배열·null을 장애로 유지하고, `:307`, `:321`은 기존 서버 장애와 공급자 본문 비노출을 검증한다. |

## Requirement 본문 및 범위 확인

- 기존 HTTP 401/403 및 공급자 거부 코드 판정을 먼저 유지한다(`storage.py:292`). 모든 HTTP 400을 권한 거부로 뭉개지 않는다.
- 새 판정은 오류 본문의 `message`, 내부 경로, `error` 문자열을 예외에 복사하거나 외부 응답으로 반환하지 않는다. 거부는 기존 중앙 예외 핸들러를 그대로 사용한다.
- 업로드 중복 객체 및 삭제의 성공·404 처리 순서는 바뀌지 않았다(`storage.py:262`, `:282`). 요청자 JWT·경로·권한 정책도 바뀌지 않았다.
- proposal·design·delta spec·tasks의 단일 호환성 슬라이스가 작업 트리 구현과 일치한다. 전체 검증 task 1.2는 아직 미완료로 남아 있어 검증 완료를 앞서 주장하지 않는다.

## 조치가 필요한 항목

없음.

## 검증과 한계

- 부모가 전달한 이번 세션의 관련 검증 결과는 59 passed다. 부모는 전체 pytest를 별도 실행 중이다.
- 리뷰어는 코드와 테스트를 독립 대조했으며, 요청에 따라 DB·큐 테스트를 추가 실행하지 않았다.
- 이 판정은 스펙 준수 리뷰의 통과이며, 전체 테스트 완료나 아카이브·커밋 가능 상태를 의미하지 않는다. task 1.2의 전체 검증 결과는 별도로 확인해야 한다.

## 판정 근거

두 시나리오의 조건과 결과가 업로드·삭제 양쪽 구현 및 회귀 테스트에 존재한다. 공급자 본문을 노출하지 않는 기존 예외 경계를 보존하며, 권한 거부와 일반 장애의 구분을 명시된 허용 목록만큼 확장했다. 미충족 요구사항이나 범위 밖 사용자 동작을 찾지 못해 `pass`로 판정한다.
