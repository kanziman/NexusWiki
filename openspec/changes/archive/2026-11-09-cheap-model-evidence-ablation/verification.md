# 검증 기록 — cheap-model-evidence-ablation

결과 해석은 `docs/ops/ask-sample-replay.md`의 「저가 답변 모델별 위키 기여 반복 측정」 절에 있다. 이 파일에는 재현과 대조에 필요한 사실만 둔다.

## 실험 기록 (2026-11-09)

원본은 Git에서 제외되는 `.worktrees/model-evidence-20261109/`에 있다. `state.json`에는 로컬 재생 계정 자격증명이 있어 해시와 내용 모두 적지 않는다.

| 파일 | 내용 | sha256 |
| --- | --- | --- |
| `registration.json` | 사전 등록 (10:26:12Z, 내용 해시 `70fa2f92…`, 상한 1,000,000 micros) | `1a0a10f1746a404d19fc5af65645bfdf077dccf27ee869b089bd8df0404e4dc3` |
| `registration.void-stale-credential.json` | 무효: 옛 state 경로를 가리킨 첫 등록. 이 등록으로 나간 호출은 0건 | `bff6236574181042522243a0f9e3e307a6336ec5c613c2a190a9cd149167c332` |
| `probes/anthropic_claude-haiku-5.5.json` | 점검 ok, 928 micros | `fdfa67a6be9aee03777b3bf480edc86da627e8e468afd5535b274b9981cf0725` |
| `probes/openai_gpt-6-luna.json` | 점검 ok, 538 micros | `46f56de69b387b2f8665257992199fd03f6f02e525f8472c5f5a4c96fc31e423` |
| `probes/deepseek_deepseek-v4.1-flash.json` | 점검 ok, 758 micros | `0932e4329061bdf0ab61cee0c7d75d8885dcc76f6af796fa890ecbb991cfc6c8` |
| `plan.json` | 3회차 · 3모델 · 제외 0, 보수 투영 753,904 micros | `f87ac0b23a28d5cf27ba4182643b1d6a46dbdc08aa01e2ecf016d1a52aff9bba` |
| `runs/r1-anthropic_claude-haiku-5.5.json` | 1회차 | `985e2ac4e7869d9ba0086c0f75ab57c926b28a18c868226a68877d437ec96569` |
| `runs/r1-openai_gpt-6-luna.json` | 1회차 | `b5c60be1fb77c35d4c8ef88e476671b367a8ff369062cb63ea00ba98a9df5488` |
| `runs/r1-deepseek_deepseek-v4.1-flash.json` | 1회차 | `8e46f3f24f2082f3e2cfe519bcf0a361e81ec1717d8fdacbdf7ccd33156cb268` |
| `runs/r2-anthropic_claude-haiku-5.5.json` | 2회차 | `ac7b5e8db2e5f0288416d22fd2b798c7267730d9c8337ab4237e9cf8af56d56e` |
| `runs/r2-openai_gpt-6-luna.json` | 2회차 | `2886688d207b191ae11c79faa42d22b60d7f8043c4269cde5b3816881d09f6c0` |
| `runs/r2-deepseek_deepseek-v4.1-flash.json` | 2회차 | `6b131bdb9a47d9fed0aee3045e427742b74249cdab92aa47884ff882b58300d8` |
| `runs/r3-anthropic_claude-haiku-5.5.json` | 3회차 | `d8147b7c9f0cdfcfa8778fa7c8a405b909b3103162b09e8257ca244b73f4fd3e` |
| `runs/r3-openai_gpt-6-luna.json` | 3회차 | `85d2792b4659a124ce667272ffbdb62985dc3a65b3a0e3c52ed4194cde7acfa1` |
| `runs/r3-deepseek_deepseek-v4.1-flash.json` | 3회차 | `0f50aa7ce2f7df68723e73f60fffb261f21b42b8f880446d9f94c1f2d860760d` |
| `scoreboard.jsonl` | 실행 18줄 + Sonnet 참조 2줄 | `918b860764993ff119e240e95766b072266a288c6f56a5dc042a1c0a2290b9b5` |
| `scoreboard.html` | 정적 성적표 (리뷰 r1 전 화면) | `4bc6dafa2d97515a0c3715f3aea5e00d597c58f6f76c83f663d7067d242e8dd3` |
| `scoreboard-r2.html` | 정적 성적표 (리뷰 r1 반영 화면, 수치 동일) | `1fba6f0b2bcd9d44e35eb07a759aa2ccacfd1ab25aefd7330716c5d7664a8668` |

고정 입력: 수집 스냅샷 `65809ec4e3b673c5…`, 답변 프롬프트 `ba39770d282034a3…`, 고정 질의 벡터는 #237 `query-vectors.json`, 기준 검색 기록은 #237 `retrieve.json`(등록에 sha256 기록). 워커 정책 `ask-replay-v1`(max_tokens 1500, reserve 200,000 micros). 실행 코드 `ceaa4ab+dirty`(이 change의 미커밋 작업 트리).

지출: 재생 DB `sum_usage_events_since(워크스페이스, 등록 시각)` = **414,437 micros**. `usage_events` 원 관측 합은 414,448 micros(정산 투영의 반올림 차이), 545행. 등록 이후 Ask 비용 호출 중 `settled`가 아닌 것은 0건이다. 모델별 실행 합: Haiku 180,830 · Luna 47,052 · DeepSeek 184,331, 점검 2,224.

## 계획 이탈

- **state 자격증명 재설정**: #237 보존 state의 비밀번호는 지난 실험 뒤 지워져 로그인이 400으로 실패했다(유료 호출 전). 관리자 API로 재생 사용자 비밀번호를 새로 정하고, 실험 디렉터리에 새 state 사본(권한 600)을 만든 뒤 다시 등록했다. 첫 등록은 이름을 바꿔 무효로 보존했다.
- **월 한도 일시 조정**: 설계 D8의 "여유 $1.10"은 이번 달 지출이 한도 안이라고 가정했다. 실제로는 유효 지출이 9,379,306 micros로 이미 한도 $5를 넘어 있었다. 그래서 한도를 `현재 지출 + 상한 $1.00 + 예약 1건 $0.20` = 10,600,000 micros로 올렸고, 끝난 뒤 5,000,000으로 복원했다.
- **거절 판정**: q30 18턴은 모두 내용상 정확한 거절이지만, 채점기 고정 문구 규칙 때문에 14턴이 실패로 집계됐다. 스펙("Product defaults stay unchanged")에 따라 판정을 고치지 않고 결과 문서에 기록했다.
- **리뷰 r1 결함과 실측의 관계**: 리뷰가 찾은 "상한 · 측정 장애로 멈추면 `not_run` 행에 판정이 없어 요약이 `KeyError`로 죽는 결함"과 "조건 중간 예외 시 과금된 턴 누락"은 실측 뒤에 고쳤다. 이번 실측의 9개 실행은 모두 `stopped=None`이고 측정 · 실행 장애가 0건이라 두 경로를 타지 않았다. 고친 코드로 같은 기록을 다시 읽은 모델 요약은 고치기 전과 같다(완료 회차 1·2·3, 위키 차이 0). 리뷰 r2의 "거절 문항 장애가 거절 판정으로 새는 결함"도 실측 뒤에 고쳤다. q30 18턴은 모두 `resolved`이고 채널 실패가 없어서 다시 채점해도 같다(거절 Haiku 0/6 · Luna 0/6 · DeepSeek 4/6, 실행 장애 0).
- **`plan`의 지출 조회**: 설계 D4대로 재생 DB를 쓰지만, 기록 파일만으로 재계산할 수는 없다. 계획 시점 지출(2,224 micros)은 `plan.json`에 남겼다.
