# 테넌트 격리 리뷰 2라운드

판정: **pass**

대상: `reconcile-interrupted-ask-cost` 현재 작업 트리와 r1 이후 추가된 호출별 비용 조회 RPC.

## r1 지적 해소

`ask_cost_snapshot`은 trace가 없는 모든 조회에서 함수 내부의 `v_since`를 UTC 일 시작으로 정규화한다. 금액·미해결 건수·운영자 확인 건수·확보 초과 건수의 모든 비교가 이 값으로 바뀌었다. `p_ask_only=false`의 일반 예산 조회로 우회하는 경로도 같은 정규화를 거친다. 작성자 전용 trace 조회는 기존 접근 판정 뒤 요청 경계를 사용한다.

직접 PostgREST RPC에 예약 생성 시각과 같은 초의 마이크로초 0·999999를 전달하는 회귀가 `p_ask_only=true/false` 양쪽에서 같은 금액과 건수를 확인한다. API가 먼저 내리는 것만으로 통과시키지 않는다.

## 새 조회 표면 확인

- `ask_cost_trace_calls`는 null trace를 거부하고 함수 내부에서 `ask_cost_snapshot`의 현재 멤버십·Ask 작성자 검사를 실행한 뒤에만 호출별 투영을 반환한다. security definer 호출 중에도 `auth.uid()`는 요청자 신원을 사용한다.
- 호출별 조회는 workspace와 trace를 함께 필터링한다. 원 관측 usage 연결은 기존 복합 FK의 workspace 일치 보호를 받는다.
- public·anon·service_role 실행 권한을 회수하고 authenticated에만 부여한다. 고정 search_path를 사용한다. generation ID·공급자 응답·본문·키는 반환하지 않는다.
- 다른 작성자의 Ask에는 owner·viewer 모두 직접 RPC에서 403을 받는 회귀가 있다. 멤버십 상실 뒤 snapshot은 403이며 새 호출별 함수도 같은 검사 경로를 재사용한다.
- API는 작성자 게이트를 통과한 Ask 분기에서만 호출별 투영을 읽는다. 연결된 원 관측 행은 목록에서 제외하고 정산 투영 한 건으로 대체하므로 정산이 호출 수를 늘리지 않는다. 원 관측액과 정산액을 별도 필드로 제공하면서 원 usage 행은 보존한다.
- r1에서 확인한 쓰기 RPC의 service_role 제한, 워크스페이스 필터·잠금, 중복 정산 방지, 실패 시 예약 유지 경계가 유지된다.
- 관측 행의 model은 서버에 저장된 호출 정책 모델, provider는 `openrouter`로 고정됐다. 공급자 응답의 임의 문자열을 이 두 필드에 저장하는 경로를 추가하지 않는다.

## 독립 검증

- `uv run pytest apps/api/tests/test_ask_cost_db.py -q`: **4 passed**.
- `openspec validate reconcile-interrupted-ask-cost --strict`: 통과.
- `git diff --check`: 통과.

이번 검토에서 추가 수정 사항이나 테넌트 경계 우회는 발견하지 못했다. 운영 DB 적용, 실제 공급자 취소 청구·대조 성공, 실제 브라우저 확인은 검증하지 않았다. 확보액이 외부 청구의 절대 상한이 아니라는 승인된 한계는 그대로다.
