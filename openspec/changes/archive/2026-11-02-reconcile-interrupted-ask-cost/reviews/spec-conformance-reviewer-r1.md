# 스펙 일치 리뷰 1라운드

- 판정: **needs_fix**
- 대상: `reconcile-interrupted-ask-cost`의 proposal·delta spec·design·tasks와 현재 구현.
- 검토 범위: 승인된 사전 예약·추기형 정산·대조·비용 표시 및 유지해야 하는 기존 Control Room 계약. 운영 적용과 실제 유료 공급자 검증은 범위 밖이다.

## 수정 필요

### 1. 직접 비용 집계 RPC에서 UTC 일 단위 경계 보호가 빠졌다

- 근거: `supabase/migrations/0027_ask_cost_accounting.sql`의 `ask_cost_snapshot`은 authenticated에 EXECUTE를 허용하고 `p_since`를 그대로 `c.created_at >= p_since`, `e.occurred_at >= p_since`에 사용한다.
- 기존 계약: `openspec/specs/ai-control-room/spec.md`의 「집계 경계를 조금씩 옮긴다」는 집계 시작 시각을 UTC 일 단위로 내리도록 요구한다. 신규 delta도 기존 접근 경계를 유지한다.
- 위반 경로: editor가 `p_trace_id=null, p_ask_only=true`로 RPC를 직접 호출하고 시작 시각을 같은 날 안에서 초 단위로 이동하면 개별 호출의 비용과 미해결·운영자 확인 건수 변화를 분리할 수 있다. API 라우터만 시각을 내리므로 DB 직접 호출은 보호되지 않는다. `p_ask_only=false`도 editor에게 같은 Ask 건수를 반환하므로 단순 플래그 전환으로 우회되지 않게 해야 한다.
- 요구 조치: trace 상세를 제외한 집계의 기간 정규화를 DB 함수 안에서 수행하고, 같은 UTC 날짜의 서로 다른 초 단위 시작값이 같은 비용·건수를 반환하는 직접 RPC 회귀 테스트를 추가한다.

### 2. 정산 후 호출별 비용과 trace 합계의 의미가 달라졌지만 화면·기존 계약에 반영되지 않았다

- 근거: `apps/api/src/api/routers/control.py`의 `_call`은 원 `usage_events.cost_micros`를 반환한다. Ask 상세의 `totals.cost_micros`만 `ask_cost_snapshot.reported_micros`로 대체한다. `ControlRoom.tsx` 호출 테이블은 그 원 관측액을 여전히 「비용」으로 표시한다.
- 재현 가능한 상태: 원 관측액이 90이고 정산 확정액이 20이면 호출 행의 비용은 90, 상단 공급자 보고 비용은 20이다. 중단 시 0을 관측하고 사후 20으로 정산해도 같은 불일치가 생긴다. 현재 DB 테스트가 원 관측액 보존과 하향 정산을 각각 입증하지만, 정산 후 상세 화면의 합계와 행 의미를 검사하지 않는다.
- 기존 계약: `ai-control-room`의 「완료된 trace 상세」는 단계별 비용과 합계가 해당 trace 사용량 행과 일치한다고 명시한다. 승인된 새 설계는 원 관측액과 정산 후 유효액을 구분하기로 했지만 delta는 이 기존 시나리오를 수정하지 않았다.
- 요구 조치: 원 관측액을 보존하되 API·호출 테이블에서 관측액과 정산액을 명확히 구분하거나 호출별 유효 비용을 제공해 합계와 일치시킨다. 승인된 정산 의미에 맞게 기존 Control Room 요구사항의 delta를 함께 보완하고, 하향 정산·0원 관측 후 사후 정산의 실제 상세 API와 화면 회귀를 추가한다.

## 확인된 일치 항목

- 워크스페이스 행 잠금과 예약 INSERT가 한 트랜잭션이며, 공급자 호출 전 일회성 start 전이를 검사한다.
- 정책 누락·입력 초과·예약 DB 오류는 공급자 호출 전에 거부한다. 입력 바이트와 출력 max_tokens가 실제 요청에 적용된다.
- 서버 발급 call_id와 공급자 generation ID를 저장하고, ID 충돌·조회 실패·ID 부재에는 예약을 유지한다.
- 정산 이력 고유 키와 상태 잠금으로 중복 정산을 방지하고 기존 usage 행을 변경하지 않는다. 공통 투영은 정산액 또는 max(확보액, 관측액)을 반영한다.
- 정산 귀속 시각은 호출 생성 시각이므로 다음 달 정산이 새달 비용으로 중복 반영되지 않는다.
- 워커 대조는 임대·배치·타임아웃·재시도 한도를 가지며, 원시 공급자 응답을 DB에 저장하지 않는다.
- 신규 테이블 직접 접근과 회계 쓰기는 차단되고, trace snapshot은 현재 멤버인 작성자 검사를 포함한다.
- 확정액·미확정 점유액·예산 판정액이 상단 지표에 구분돼 표시되며, 모델 정책 미설정·실제 비용 상한 미보장·전환 절차를 운영 문서에 적었다.

## 검증

- 이번 리뷰에서 `openspec validate reconcile-interrupted-ask-cost --strict`와 `git diff --check`를 새로 실행해 통과했다.
- 부모 에이전트가 보고한 전체 Python 839개 통과·1개 스킵, 대시보드 464개 통과 및 신규 테스트 결과를 참고했다. 이 리뷰는 전체 테스트를 재실행했다고 주장하지 않는다.
- 위 두 스펙 공백을 해소한 뒤 2라운드 확인이 필요하다.
