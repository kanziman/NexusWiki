## Why

전체 검증에서 Storage가 RLS 거부를 `code` 없는 HTTP 400으로 반환해 파일 수집 API가 403 대신 502를 내는 회귀를 확인했다. 권한 거부와 저장소 장애를 구분하는 기존 계약을 복구한다. 추적: https://github.com/kanziman/NexusWiki/issues/204

## What Changes

- 기존 오류 코드와 전송 상태 판정을 유지하고, 응답 본문의 `statusCode`가 401 또는 403인 거부도 인식한다.
- 업로드와 삭제에 같은 판정을 적용하고 공급자 본문을 외부로 노출하지 않는다.
- 코드 없는 거부와 일반 장애를 구분하는 회귀 검증을 추가한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `source-ingestion`: Storage 권한 거부 응답 형식에 독립적인 403 매핑을 명시한다.

## Impact

`apps/api/src/api/storage.py`, Storage 단위 테스트, 기존 파일 수집 격리 테스트. 스키마·운영 설정 변경은 없다.
