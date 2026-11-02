## Why

최종 사용량 전에 끊긴 Ask는 현재 사용량이 비어 비용 0으로 기록되므로, 반복해서 끊으면 실제 발생할 수 있는 비용이 월 상한에 반영되지 않는다. 기존 감사 기록을 보존하면서 미확정 비용을 예산에 임시 반영하고, 공급자 비용을 조회할 수 있을 때 정산해야 한다.

## What Changes

- Ask 공급자 호출 전에 보수적인 임시 확보액을 예산에 반영하고, 진행 중·미확정 호출을 포함해 새 Ask 허용 여부를 판단한다. 병렬 실행과 프로세스 재시작에서도 미확정액을 잃지 않는다.
- generation ID를 확보한 중단 호출은 OpenRouter 비용 메타데이터와 사후 대조한다. 조회 불가·일시 오류를 비용 0 확정으로 처리하지 않고 미해결 상태와 임시 확보액을 유지한다.
- 확정 비용과 임시 확보액을 중복 합산하지 않는다. 같은 대조를 반복해도 합계가 늘지 않고, 기존 `usage_events`는 덮어쓰거나 삭제하지 않는다.
- Control Room에서 공급자 보고 비용·미확정 확보액·예산 판정액을 구분한다. 본문과 비밀 키는 기록하거나 화면에 노출하지 않는다.
- 용어: 임시 확보액은 예산 판정을 위한 잠정 금액, 확정 비용은 공급자 보고액, 미해결은 확정액을 아직 확보하지 못한 상태다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `usage-guardrails`: 중단 Ask의 영속적인 임시 확보, 사후 대조, 추기형 정산 및 예산 판정.
- `ai-control-room`: 확정 비용과 미확정 확보액을 구분하는 표시.

## Impact

- 워커 Ask 스트림·공급자 경계·사용량 기록·재처리, 예산 집계, DB 마이그레이션, Control Room API·화면과 관련 테스트가 대상이다.
- 기존 JWT·RLS·워크스페이스 경계와 trace 접근 권한을 유지한다. 공급자 키는 워커만 갖는다.
- ID를 남기지 않은 과거 호출의 실비 복원, #170의 턴 상태 복구, 전 공급자 청구 대조, 실제 유료 호출·운영 적용은 범위 밖이다.
- 미해결 상태가 길어지면 예산이 오래 점유되어 정상 Ask도 제한될 수 있다. 사용자는 이 임시 차감 정책을 승인했다.
- 추적: https://github.com/kanziman/NexusWiki/issues/172 . change 이름: `reconcile-interrupted-ask-cost`.

## References

- OpenRouter 스트리밍: https://openrouter.ai/docs/api/reference/streaming
- generation 비용 메타데이터: https://openrouter.ai/docs/api/api-reference/generations/get-generation
- API 존재는 확인했지만 중단된 모든 호출의 확정 비용을 반드시 조회할 수 있다고 가정하지 않는다.
