## Why

Step 1이 측정을, Step 2가 입력 예산을 맡았지만 LLM **출력**은 여전히 믿고 저장한다. 인용이 하나도 없는 답변이 `resolved`로 저장되고, 공백·placeholder 페이지가 스키마를 통과하며, 코드 펜스 하나가 유료 재시도가 되고, 스키마 오류가 큐 재시도와 곱해져 컴파일 1건이 최대 9회 호출된다. 이중 Citation이 제품의 존재 이유이므로 출력 계약을 코드로 강제한다.

## What Changes

- 구조화 출력: 전체를 감싼 코드 펜스 하나는 결정론적으로 벗겨 재시도 없이 통과시키고, 공백·placeholder 페이지를 거부한다.
- 구조화 출력 시도를 3회에서 2회로 줄이고, 스키마 소진을 큐가 재시도하지 않는다. 재시도에 직전 출력을 그대로 다시 싣지 않는다.
- Ask: 스트림 뒤 인용 계약을 검증해 위반이면 1회 수리하고, 그래도 실패하면 발급 앵커만 쓰는 결정론적 답변으로 끝내 `fallback` 상태로 저장한다. 근거 부족을 밝힌 답변은 위반이 아니다.
- 컴파일: 페이지가 근거로 삼은 원문 청크를 발급 앵커와 대조해 저장한다(위키→원문 추적이 청크 단위가 된다).
- 충돌 판정: 한 쌍의 스키마 소진이 잡 전체를 실패시키지 않는다.
- Control Room [품질] 탭과 공개 쇼케이스의 Step 3 합성 증거를 추가한다.
- 운영 복구 수단으로 `AI_CONTROL_QUALITY_MODE`(`off`/`shadow`/`enforce`)를 둔다.

## Capabilities

### New Capabilities

없음.

### Modified Capabilities

- `grounded-answering`: Ask 인용 계약, 수리, Fallback 상태
- `wiki-compilation`: 코드 펜스 처리, 의미 검증, 시도 상한, 페이지 근거 청크, 충돌 판정 쌍 격리
- `ai-control-room`: 품질 탭
- `ai-controls-showcase`: Step 3 전후 증거

## Impact

- `apps/worker`: `llm.py`, `llm_gateway.py`, `errors.py`, `handlers/compile.py`, `handlers/conflict.py`
- `apps/api`: `services/ask.py`, `routers/control.py`, `settings.py`
- `apps/dashboard`: Ask 상태 표시, Control Room, 쇼케이스
- `supabase/migrations`: `fallback` 상태, `wiki_page_evidence`, 컴파일 템플릿 갱신, 품질 집계 RPC
- 배포: 마이그레이션을 코드보다 먼저 적용해야 한다. `fallback` 상태를 모르는 DB에 새 코드가 쓰면 턴 종결이 실패한다.
