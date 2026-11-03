## Why

프롬프트의 인용 정책이 템플릿 네 곳에 흩어져 낡은 지시와 섞여 있고, 편집자가 만든 템플릿은 규칙을 뺄 수 있다. 채팅 요청에는 데이터 수집 거부가 없다. 컴파일은 사람이 검증했거나 공개한 위키 본문을 승인도 이력도 없이 덮어쓰면서 검증 배지를 그대로 남긴다. 분쟁 중인 페이지는 일반 근거와 똑같이 모델에 전달된다.

## What Changes

- 모든 LLM 호출에 워커 경계에서 버전이 있는 공통 정책을 주입하고 `policy_version`을 사용량에 기록한다. 사용자 템플릿도 이 정책을 뺄 수 없다.
- 모든 채팅 요청에 `data_collection: deny`를 강제한다.
- 전역 Ask 템플릿에서 낡은 인용 지시를 제거한다.
- 컴파일 쓰기를 위험 등급으로 분류한다. 덮어쓰기는 이전 본문을 개정 이력으로 남기고, 검증되었거나 공개된 페이지는 승인 대기로 보류한다(`AI_CONTROL_RISK_MODE`).
- `editor` 이상이 보류된 변경을 승인하거나 거부한다.
- 분쟁 중인 근거를 모델 컨텍스트와 답변 화면에 표시한다.
- Control Room [리스크] 탭과 공개 쇼케이스의 Step 4 합성 증거를 추가한다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `usage-guardrails`: 공통 정책 주입과 데이터 수집 거부
- `wiki-compilation`: 위험한 쓰기 분류, 개정 이력, 승인 보류
- `grounded-answering`: 분쟁 근거 표시
- `ai-control-room`: 리스크 탭
- `ai-controls-showcase`: Step 4 전후 증거

## Impact

- `packages/core`: 정책 문구와 쓰기 분류 순수 함수
- `apps/worker`: `llm.py`, `llm_gateway.py`, `handlers/compile.py`, 승인 적용 핸들러
- `apps/api`: `services/ask.py`, `routers/control.py`
- `apps/dashboard`: Control Room, Ask 근거 경고, 쇼케이스
- `supabase/migrations`: 템플릿 정리, 개정 이력과 제안 테이블, 승인 RPC, 리스크 집계
