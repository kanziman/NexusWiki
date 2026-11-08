## 1. 판정과 집계 (순수 로직)

- [x] 1.1 검색 응답의 원문 근거 `document_id`가 raw_source id인지 실제 응답으로 확인하고, 다르면 `metadata`에서 raw_source id를 찾도록 판정 입력을 정한다
- [x] 1.2 `scripts/ask_replay.py`에 근거 한 개의 적중 판정 함수 추가: 원문은 정답 raw_source id, 위키는 `sources`에 정답 포함
- [x] 1.3 질문 단위 결과 함수 추가: 순위별 적중, 첫 적중 순위, 원문/위키 적중, 이중 적중@8, 여러 문서 질문의 "하나라도"와 "전부"
- [x] 1.4 요약 함수 추가: 답할 수 있는 질문만으로 hit@1·@3·@8, MRR, 원문만·위키만·이중 hit@8, 실패 요청 수, 답할 수 없는 질문의 근거 반환 건수. 지표 정의 문구 포함

## 2. 명령과 기록

- [x] 2.1 `retrieval-eval` 하위 명령 추가: loopback 가드, 사용자 토큰으로 검색 API 호출, `raw_sources`(제목 → id)와 `wiki_pages.sources`를 사용자 토큰으로 조회
- [x] 2.2 출력 경로가 이미 있으면 검색 호출 전에 거부, 기록에는 라벨 · git sha · 질문별 결과 · 요약만 저장(답변과 비밀 없음)
- [x] 2.3 요청 실패를 질문별 상태로 기록하고 미적중으로 센다
- [x] 2.4 `retrieval-compare` 하위 명령 추가: 두 기록의 공통 질문으로 지표를 나란히 보고
- [x] 2.5 (리뷰 r1) 검색 응답 `meta`의 채널 상태를 읽어 실패 채널이 있으면 `channel_failed`로 기록하고, 기록에 `policy_versions`를 남기며, 비교 표에 정책 버전을 표시한다
- [x] 2.6 (리뷰 r1) 정답 문서 매핑 실패는 `unmapped_expected`(검색 호출 없음), 청크 조회로도 원문을 못 찾은 근거는 `unresolved_evidence`로 기록하고, 제목이 같은 원문이 둘 이상이면 실행을 거부한다
- [x] 2.7 (리뷰 r1) 측정 실패 상태는 모든 지표에서 미적중으로 세고 `failed_requests` · `status_counts`로 보고하며, 여러 문서 질문의 정답 수는 질문의 `doc`에서 센다. 기록은 `x` 모드로 쓴다

## 3. 테스트

- [x] 3.1 `apps/worker/tests/test_ask_replay_script.py`에 스펙 시나리오 테스트 추가(원문 1위 적중, 위키 컴파일 원문 적중, 다른 문서 위키 미적중, 미적중, 한쪽만 적중, 여러 문서, 답할 수 없는 질문, 요청 실패, 덮어쓰기 거부, 비교)
- [x] 3.2 (리뷰 r1) 채널 장애 감지, 측정 실패 행의 미적중 처리, 실패한 여러 문서 질문의 분모 유지, 매핑 실패, 비교 표의 정책 버전 테스트 추가
- [x] 3.3 (리뷰 r2) 가짜 HTTP 전송으로 `retrieval-eval` 명령을 직접 돌려 상태를 정하는 분기(정상 · 채널 장애 · 매핑 실패 · 근거 미확인 · HTTP 실패)와 제목 중복 거부(검색 호출 전)를 고정

## 4. 실측과 문서

- [x] 4.1 재생 스택을 띄워 문서를 수집하고(약 $0.22) `retrieval-eval`을 1회 실행한다
- [x] 4.5 (리뷰 r1) 채널 상태를 남기도록 고친 코드로 다시 수집 · 측정하고(약 $0.22), 채널 장애 0건을 확인한 뒤 문서의 수치를 재측정 기준으로 바꾼다
- [x] 4.2 `docs/ops/ask-sample-replay.md`에 실행법, 지표 정의, 첫 측정 결과를 적는다
- [x] 4.3 `docs/ops/evaluation-map.md`의 검색 칸과 적용 원장을 측정 결과로 갱신한다
- [x] 4.4 재생 스택과 서버를 내린다

## 5. 검증

- [x] 5.1 새로 실행: 관련 테스트 · ruff check · ruff format --check · `openspec validate ask-replay-retrieval-eval --strict` · `openspec validate --specs`
