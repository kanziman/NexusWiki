## REMOVED Requirements

### Requirement: BYOK custom AI API key management
**Reason**: 이 기능은 명세대로 동작한 적이 없다. 워커 어디에서도 `workspace.custom_api_key`를 읽어 사용하지 않으므로, 소유자가 개인 키를 등록해도 청구·예산 판정에 어떤 영향도 주지 못했다. 일반 설정 패널이 "무제한 이용"을 약속하는 UI를 계속 노출하는 것은 사용자를 오도하므로 기능을 제거한다.
**Migration**: 일반 설정 패널에서 커스텀 API 키 입력·저장·삭제 UI를 제거한다. 이미 `workspaces.custom_api_key`에 값이 저장된 워크스페이스는 마이그레이션으로 해당 컬럼을 `null` 처리하며, 소유자가 별도로 취해야 할 조치는 없다.
