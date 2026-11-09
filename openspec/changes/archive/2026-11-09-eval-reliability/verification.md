# 검증 기록 — eval-reliability

## 6절 실측 시도 (2026-11-08)

상태: **미완료**. HTTP 한 문항 점검에서 내부 예산 402를 확인해 `repeat`를 시작하지 않았다. 계획한 HTTP 3회차는 모두 미실행이다. `tasks.md` 6.1·6.2를 완료 처리하지 않으며 change도 아카이브하지 않는다.

실행 코드: `a8280fa+dirty`의 `feat/eval-reliability` 작업 트리. #230은 GitHub에서 여전히 OPEN이지만 546xx에는 실행 중인 API·워커와 대기 잡이 없었고, 완료된 잡 96개만 있었다. 보존된 수집은 다시 만들지 않았다. 이번에 띄운 API·워커는 점검 뒤 중지했고 8031·8081 리스너가 없음을 확인했다. 기존 Docker 스택은 유지했다.

### 고정 입력 대조

| 입력 | 현재 값 (#232와 일치) |
| --- | --- |
| 수집 스냅샷 | `65809ec4e3b673c52b9370620dcf31f693b274e4b6f03c231dfc85ae073d4160` |
| 질문 fixture | `8250970cc6732378b0208fe9a239e17dbf793d3d087e452eed94ef3b647d5d83` |
| 답변 프롬프트 | `ba39770d282034a31a8b5c04da3b100f6d221c5d805c322c1939e6acfb87a9e6` |

정책 `hybrid-rrf-v2`, k=8. 점검은 모델 호출 전 실패해 결과의 모델은 `unknown`이다. 따라서 점검 결과를 과거 하네스와 같은 반복 묶음으로 넣지 않았다.

### 실행과 비용

사용자는 6절 실행과 로컬 재생 계정 비밀번호 재설정을 승인했고, 월 한도는 현재 값으로 유지하도록 지정했다. 승인 범위 안에서 비밀번호만 재설정하고 인증 정보는 Git 밖 권한 0600의 상태 파일에 두었다. 월 한도 $5와 기존 미정산 예약 $3.80은 변경하지 않았다.

검색은 HTTP 30문항 모두 정상 완료했다. 답할 수 있는 29문항의 hit@1 27/29, hit@8·이중 적중@8 28/29, MRR 0.939655, 요청·채널 실패 0건이다. q06이 상위 8 미적중이다. q01 점검은 `error`이며 워커 로그의 `/internal/llm-chat` 응답은 402다. 이 오류를 모델 정답성 실패로 해석하지 않는다.

실측 구간은 API 기동(13:47:55Z) 이후다. 비용 집계는 앞선 실험의 마지막 사용량 시각(12:34:28Z)과 분리되는 `occurred_at >= '2026-11-08T13:45:00Z'`를 사용했고, 이 구간에 임베딩 31회·31 micros, LLM 0회였다. 월 유효 예산은 시작 전 7,835,789 → 종료 후 7,835,820 micros다. 원 관측 월 합계는 4,035,821 micros, 미정산 예약은 3,800,000 micros다. 호출별 정산을 적용한 유효 예산은 원 관측 합계와 예약의 단순 합산보다 1 micro 작다. 전체 실행 상한 3,000,000 micros를 넘지 않았다.

새 HTTP 답변 회차와 변동폭은 없다. 기존 #232 `both × body` 하네스 1회만 현재 검색·라벨로 오프라인 보고서를 생성했다. 답할 수 있는 문항 28/29, 정확한 거절 1/1, 잘못된 거절 0/29, 알려진 실패 q06 1건·예상 밖 실패 0건이다. q06 보고 단계는 질문 모호성, 자동 단계는 검색 미적중이다. 과거 행의 채널 장애 정보 누락과 합성 샘플 한계는 보고서에 표시된다. 한 회차의 안정성 분류를 반복 안정성의 증거로 쓰지 않는다.

### 원본 해시

기준 경로: Git에서 제외되는 `.worktrees/reliability-evidence-20261108/`. `execution-status.json`은 수동 실행 상태 기록이며 `repeat`가 생성한 기록이 아니다.

| 파일 | sha256 |
| --- | --- |
| `preflight.json` | `c2e79510fa6a1eabc28ce1f9a3a99077372d2531e16abd7e4bcb5f367c810188` |
| `retrieval.json` | `a06a82c2c9b5b121af1ff337c00faf946cbdb65cc22c074971e11fdf96628947` |
| `probe.json` | `fc673e21228e8f48b015a0ae52543f7f41827120b961bce01bd19468f4822e7c` |
| `scorecard.jsonl` | `8be978fd03917d1a3158f1b781663f3ec05c7b200909c685ffd16d7c83431236` |
| `execution-status.json` | `8c9e9128822bd449631a0a1b0c414824b3ecdd9f7ef7ef2ab9ec86685d1c6290` |
| `budget-after.json` | `15aa60f3bd06135eb379dbcacc29a7d763a657b6728ada553a0277ebefc6a0a5` |
| `historical-harness-report.json` | `5da0aa4a881e59450b4efa37f5e7739e3fef35e0ddad22290adc64bb57aa525a` |
| `historical-harness-report.md` | `badc5f85a3f24dbc42add4fae72d11795196d296aaf5b3922bc72e9e73bf577d` |

기존 #232 `answer.json`은 `.worktrees/ablation-evidence-20261108/`에 있으며 sha256은 `4082cff3d121929338a57a7080bef626333c6524baf753f36f7abaf0cb3740a3`이다.

## 6절 실측 재개 (2026-11-09)

상태: **완료**. 계획 수정(HTTP 2회 · 전체 상한 $2.00)과 사용자의 유료 실행·월 한도 일시 증액 승인에 따라 실행했다. 실행 코드는 `9ae4244+dirty`(변경은 change 문서뿐)다.

### 고정 입력 대조

수집 스냅샷 `65809ec4e3b673c52b9370620dcf31f693b274e4b6f03c231dfc85ae073d4160`, fixture `8250970cc6732378b0208fe9a239e17dbf793d3d087e452eed94ef3b647d5d83`, 답변 프롬프트 `ba39770d282034a31a8b5c04da3b100f6d221c5d805c322c1939e6acfb87a9e6`로 #232와 일치한다. 모델 `anthropic/claude-sonnet-4.6`, 정책 `hybrid-rrf-v2`, k=8. 따라서 #232 `both × body` 하네스 회차를 묶음에 포함했다(설계 D11).

### 실행과 비용

| 단계 | 결과 | 비용 |
| --- | --- | --- |
| 검색 1회 | 30문항 정상, hit@1 27/29 · hit@8 28/29 · MRR 0.939655 · 요청/채널 실패 0건 | 임베딩 30 micros |
| 한 문항 점검 (q01) | `resolved` | 21,010 + 1 micros |
| `repeat` 2회차 | 상한 1,978,959 micros, 두 회차 `complete` | 1,522,385 micros(답변) + 60 micros(임베딩) |

`usage_events`(`occurred_at >= '2026-11-09T01:03:00Z'`, 워크스페이스 `51b80299…`): 임베딩 91회 91 micros, LLM 61회 1,543,395 micros, 합계 **1,543,486 micros**로 전체 상한 2,000,000 micros 이하다. 같은 구간의 `ask_cost_calls` 61건은 모두 `settled`이며 새 미정산 예약은 없다. 월 유효 예산은 시작 전 7,835,820 → 종료 후 9,379,306 micros다. 월 한도는 5,000,000 → 10,000,000 → 10,500,000(repeat 직전, 내부 예약 여유 확보)으로 일시 조정한 뒤 5,000,000으로 복원했다. 기존 미정산 예약은 삭제하지 않았다. API·워커 중지와 8031·8081 리스너 없음을 확인했다.

### 보고서 결과

HTTP 2회와 하네스 1회 모두 답할 수 있는 문항 28/29(회차별 Wilson 95% 82.8~99.4%), 정확한 거절 1/1, 잘못된 거절 0/29, 위조 앵커 0, 알려진 실패 1(q06) · 예상 밖 실패 0이다. 변동폭은 HTTP [28, 28], 전체 [28, 28, 28]이고 안정 통과 29 · 안정 실패 1 · 흔들림 0 · 미실행 0이다. q06은 보고 단계 질문 모호성, 자동 단계 검색 미적중이다. 회차가 2~3개이고 독립 표본이 아니므로 흔들림 0을 안정성 보장으로 읽지 않는다.

### 원본 해시

기준 경로: Git에서 제외되는 `.worktrees/reliability-evidence-20261109/`. 인증 상태는 복사하지 않고 기존 `.worktrees/reliability-evidence-20261108/state.json`(권한 0600)을 참조했다.

| 파일 | sha256 |
| --- | --- |
| `retrieval.json` | `5d35d0b6caa13942cbc4de7980e5ca25b611855252189c2866fbb8502e54e005` |
| `probe.json` | `ba030fc5c6e139d27a58c6e3940a4db41616ec52c5d975ab1d502743e3b7209b` |
| `probe-scorecard.jsonl` | `b152c1eb20bb21359c24c4ed233dc214c41f0fdebd3a734acc88972ceaaf1be4` |
| `budget-before.json` | `6675ddfd540765539b12934ec4f7f8fa9aa734a193f55b0141415a50f3da323a` |
| `budget-after.json` | `c5953288bec6ffcab5e94aee565b4cde474e288b20c3de4dc63d19d84ec2592b` |
| `runs/repeat.json` | `5b92bc078424e7f78546ad14c530394a34ddc41bafcbaf2382e2112983c978c1` |
| `runs/reliability-1.json` | `b1aa9e30f51409bc9c5b9b765383a5a027d05405c7d4faccdab952b5e77760f9` |
| `runs/reliability-2.json` | `b57380f56e8f4ef69517762b20bb38f427db5d0fd204c9d10de421ca75e2c9de` |
| `runs/scorecard.jsonl` | `4387444d314ae36e9761979d1a8d10ad88ff90d5722eac6346514fc0c97f8f55` |
| `reliability-report.json` | `636ffcc6e52e53b04e92877e29ff21d01143b2ee6ec766f80a7e451f4f1d2c35` |
| `reliability-report.md` | `57190d12f4d25c622c649d9693981f71acd497f95c948e4f8915d874ba6f2d91` |

#232 `answer.json`은 위 절의 해시(`4082cff3…`)와 같은 파일을 썼다.
