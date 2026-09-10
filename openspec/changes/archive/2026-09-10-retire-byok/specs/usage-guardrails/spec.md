## REMOVED Requirements

### Requirement: BYOK unlimited quota and limit modal integration
**Reason**: 이 요구사항은 계약으로 존재했지만 한 번도 구현되지 않았다. 워커의 `openrouter_client()`는 항상 운영자 소유 `OPENROUTER_API_KEY`만 사용했고, 권위 있는 예산 판정 함수(`enqueue_source_job`)도 `custom_api_key`를 확인한 적이 없다 — 커스텀 키를 등록해도 실제로는 여전히 표준 월간 예산 상한이 그대로 적용됐다. "무제한" 표시는 UI에만 존재하는 거짓 정보였으므로 철회한다.
**Migration**: 크레딧 한도 모달은 더 이상 BYOK 유도 링크를 제공하지 않는다. 모든 워크스페이스는 예외 없이 표준 월간 예산 상한(`Workspace budget preflight` 요구사항)을 따른다. 이미 등록된 커스텀 키는 워크스페이스 예산 판정에 아무 영향도 주지 않으므로 사용자 쪽에서 별도로 취해야 할 조치는 없다.
