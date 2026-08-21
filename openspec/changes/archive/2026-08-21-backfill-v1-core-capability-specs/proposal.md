## Why

NexusWiki v1.0의 핵심 제품 계약은 GSD 산출물과 `checklists.json`, 코드 및 검증 기록에는 존재하지만 현재 `openspec/specs/`에는 최근 UI 변경 중심의 계약만 남아 있다. 공식 워크플로우와 향후 위키 QA가 제품의 실제 경계 동작을 참조할 수 있도록 이미 구현·검증된 핵심 계약을 OpenSpec의 정본 capability로 복원한다.

## What Changes

- 사용자 요청 경로의 JWT/RLS 격리와 service role 사용 경계를 문서화한다.
- 파일·URL·텍스트 수집, 원본 보존, 중복 및 추출 품질 처리를 문서화한다.
- 위키 컴파일, 링크 동기화, 임베딩, 재처리 멱등성 계약을 문서화한다.
- 백그라운드 잡의 claim, 단계 전이, 재시도, 취소, reaping 및 오류 공개 경계를 문서화한다.
- 5채널·2웨이브 하이브리드 검색과 RRF, 그래프 및 장애 격리 정책을 문서화한다.
- 서버 발급 인용, 근거 교집합, 위조 앵커 제거와 SSE 답변 계약을 문서화한다.
- 지식 충돌 및 사람 검증 감사 계약을 문서화한다.
- 비용 상한과 사용량 관측의 운영 보호장치를 문서화한다.
- 기존 동작이나 API를 변경하지 않고, GSD v1.0 아카이브와 현재 구현이 함께 증명하는 계약만 백필한다.

## Capabilities

### New Capabilities

- `tenant-data-isolation`: 요청자 JWT, RLS, service role 및 비공개 실패 경계를 정의한다.
- `source-ingestion`: 비동기 소스 등록, 중복 감지, 원본 보존과 추출 품질 경계를 정의한다.
- `wiki-compilation`: 검증된 LLM 컴파일, 결정적 식별자, 링크·임베딩 동기화와 재처리를 정의한다.
- `background-job-lifecycle`: 잡 claim, 체인, 재시도, 취소, reaping 및 오류 공개 정책을 정의한다.
- `hybrid-retrieval`: 5채널 검색, RRF 융합, HNSW·그래프 정책과 부분 장애 처리를 정의한다.
- `grounded-answering`: 근거 별칭, 인용 무결성, 근거 없음 처리와 SSE 답변 순서를 정의한다.
- `knowledge-quality`: 지식 충돌 상태와 사람 검증 감사 정보의 전이를 정의한다.
- `usage-guardrails`: 워크스페이스 비용 상한, 사용량 기록과 안전한 운영 관측을 정의한다.

### Modified Capabilities

없음. 기존 UI·내비게이션 capability의 요구사항은 변경하지 않는다.

## Impact

- 신규 canonical spec 8개가 `openspec/specs/`에 추가된다.
- 근거는 Git commit `34fee23`의 v1.0 GSD 요구사항·검증 기록, `checklists.json`의 결정, 현재 API/worker/core/migration/tests이다.
- 애플리케이션 코드, 데이터베이스 스키마, API, 의존성 및 사용자 동작은 변경하지 않는다.
- 추적 이슈: https://github.com/kanziman/NexusWiki/issues/55
