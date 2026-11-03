## ADDED Requirements

### Requirement: Storage 권한 거부의 안전한 매핑
시스템은 원본 파일 업로드와 삭제의 Storage 권한 거부를 HTTP 403과 고정된 안전한 응답으로 MUST 반환한다. 공급자가 HTTP 400으로 감싸고 본문의 `statusCode`에 401 또는 403을 반환해도 동일하다. 공급자 오류 본문은 외부에 노출하지 않고, 일반 저장소 장애는 502로 구분한다.

#### Scenario: 코드 없는 Storage 권한 거부
- **WHEN** Storage가 업로드 또는 삭제 요청에 오류 코드 없이 HTTP 400과 본문 `statusCode` 403을 반환한다
- **THEN** API는 HTTP 403을 반환하고 공급자 메시지나 내부 경로를 노출하지 않는다

#### Scenario: 일반 Storage 장애
- **WHEN** Storage가 권한 거부가 아닌 내부 장애를 반환한다
- **THEN** API는 HTTP 502를 반환한다
