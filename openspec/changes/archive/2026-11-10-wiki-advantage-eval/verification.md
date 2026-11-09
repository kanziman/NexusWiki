# 검증 기록 — wiki-advantage-eval

결과 해석은 `docs/ops/ask-sample-replay.md`의 「위키 유리 문항 재측정」 절에 있다. 이 파일은 재현과 대조에 필요한 사실만 둔다.

## 유효 시도 기록 (2026-11-10)

원본은 Git에서 제외되는 `.worktrees/wiki-advantage-20261110/`에 있다. `state.json`에는 로컬 재생 계정 자격증명이 있어 해시와 내용을 적지 않는다(권한 600).

| 파일 | 내용 | sha256 |
| --- | --- | --- |
| `budget.json` | 총 상한 890,000 · 컴파일 `mistralai/ministral-14b-2512` · 답변 3종 · 시험지 해시 `43713409…` | `226c76bce6579d7e03c6fb95a983020bea8fcc4a6dd9a347ca3706d3a2c1b97a` |
| `ingestion.json` | 문서 29 · 위키 39쪽 · 잡 174 · 실패 0 · 수집 지출 17,680 | `bfce82f97aae4976ec750fdf7d5e3c70996a42ffbdf48300745ef580d38c8cc9` |
| `query-vectors.json` | 고정 질의 벡터 44개 | `cdfe25668cb621beba613a508293224cf628b5ea5603a1b65dc9f90959279b7c` |
| `retrieve.json` | 검색 2조건(hit@8 40/40 · 40/40) | `3ed0e273e1977b0e09a0fce0def9cca33616318f01a30a31f5407b4d20035eff` |
| `registration.void-cost.json` | 무효: 답변 3종 등록. 점검 비용 규칙으로 0회차 계획 | `21c32d2cf964dbe863130199e06f9ae438dd2fc0b37de1d2cd959f8fb6349190` |
| `plan.void-cost.json` | 무효 계획(rounds 0) | `a2f7537d6014579f78142ac75afed712df67c4d6c1c9b50d98c5cda5e0148f8f` |
| `registration.json` | 답변 2종 · 재생 상한 867,068 · 효과 기준 {3, 2} · 최소 2회차 | `d9a8504e6731334ede8e94ac709ac5296cedc7eca5f526e4c34e5d58e1564a36` |
| `probes/anthropic_claude-haiku-5.5.json` | 점검 ok, 1,296 micros, 잘림 | `99506db13c5faf66ebd76a5630702ac67d0e551d3205740d3efa2639a2d93b45` |
| `probes/openai_gpt-6-luna.json` | 점검 ok, 283 micros | `684e9902e9c0701371aee1f3e8b505d30f8ffabbdbf36d0126a1b967fb3c8bcb` |
| `plan.json` | 2회차 · 2모델, 보수 투영 685,867 | `4f647d0a2803853e268e26686fadea7d2d0865fda96b5c72a1ed0c0e5bf32199` |
| `runs/r1-anthropic_claude-haiku-5.5.json` | 1회차 | `006c94df470852912919916a71c4c93ebdbc40f1e9f33728139d2155e520131f` |
| `runs/r1-openai_gpt-6-luna.json` | 1회차 | `94d4391e3df6371e2a32e7b75078551f233ceff501b238cd50d8965f8aa7e6cc` |
| `runs/r2-anthropic_claude-haiku-5.5.json` | 2회차 | `918304a00851ea70560d60e6de8f8f9c0a0f8a3ed579c7ca3389741c1310d746` |
| `runs/r2-openai_gpt-6-luna.json` | 2회차 | `d858a4ac1b492de4d6ac4e36cc2e9f671f22d3cc6c8292bcdb997b754757daee` |
| `scoreboard.jsonl` | 실행 8줄 | `01b8b5c86138fefccfe4170480683134f68766e6b7be0fd1d8101965ce17eea3` |
| `scoreboard.html` | 정적 성적표(효과 판정 · 유형별 · 거절) | `ba918615caa08d29ced0fa3e69ef1e8e569936c4aa66f75976b8d16e288add90` |

워크스페이스 `02073b3b…`, 월 한도 890,000(수집 전 psql로 설정). 재생 서버 예약액 `ASK_REPLAY_RESERVE_MICROS=20000`. 실행 코드 `33a4476+dirty`(이 change의 미커밋 작업 트리).

지출(재생 DB `sum_usage_events_since`, 워크스페이스별):

| 워크스페이스 | 용도 | micros |
| --- | --- | --- |
| `95457567…` | 월 한도 REST 403으로 문서 투입 전 중단 | 0 |
| `1dd3e48e…` | 무효: qwen 컴파일 수집 | 99,486 |
| `e83784ee…` | ministral 긴 문서 컴파일 점검 | 7,936 |
| `02073b3b…` | 유효 시도(수집 · 임베딩 · 점검 5 · 재생 8실행) | 272,425 |
| 합계 | | **379,847** |

유효 시도의 정산 안 된 Ask 비용 호출 0건, 사용량 행 576건.

## 판정

사전 등록 판정 `not_supported`(Haiku `supported` · Luna `not_supported`, 지지 모델 1 < 2). 금지 사실 채점이 옛 값을 대조로 언급한 올바른 답을 실패로 잡은 사례를 원문으로 확인했다(c01 · c03 · d01 답변). 판정은 바꾸지 않고, 결과 문서에 "기대 사실 포함만" 사후 진단을 따로 적었다: Haiku 늘 복구 m02 · m05(여러 문서 계산), Luna 0, 충돌 · 긴 문서 · 헷갈리는 문서는 두 조건 모두 거의 만점.

## 계획 이탈

- **월 한도 설정 경로**: 설계 D5는 로컬 service_role REST였으나 `workspaces` UPDATE 권한이 없어 403이었다. 문서 투입 전에 멈췄고, 재생 DB 컨테이너 psql로 바꿨다(UUID · int만 허용). 설계에 반영했다.
- **컴파일 모델**: `qwen/qwen3.8-flash`가 긴 문서 4개를 출력 상한 4,096에서 잘려 컴파일하지 못했다(3회 재시도). 스펙대로 그 수집은 재생하지 않고 무효로 보존했고(`.worktrees/wiki-advantage-20261109/VOID.md`), 추론을 하지 않는 `mistralai/ministral-14b-2512`를 긴 문서 4개로 먼저 점검한 뒤 새 예산(총 $1 − 앞선 지출)으로 다시 수집했다.
- **답변 모델 3종 → 2종**: 점검 비용 규칙(최대 점검 턴 비용 × 1.5)으로 3종은 0회차였다. 결과를 보지 않고 비용만으로 가장 비싼 DeepSeek을 빼고 재등록했다. 이를 위해 등록이 예산 개시 답변 모델의 부분집합을 허용하도록 고쳤다(테스트 포함).
- **잡 재시도**: 임베딩 잡 몇 개가 공급자 429로 `dead`가 되어, 제품 재시도 API(`POST /jobs/{id}/retry`, 요청자 JWT)로 복구했다. `jobs`를 직접 고치지 않았다. 질의 벡터 1개도 첫 시도에 실패해 다시 만들었다.
- **예약액**: 재생 서버 기본 예약 200,000이 월 한도 $0.89 근처에서 먼저 막히므로 `ASK_REPLAY_RESERVE_MICROS`를 추가해 20,000을 썼다.
- **리뷰 r1(격리) 반영**: `ingest-record`가 끝나지 않은 잡을 실패로 막고, 집계 조회를 1000행에서 멈추고, 수집 기록에 워크스페이스 id를 남기게 고쳤다. 실측의 `ingestion.json`은 고치기 전 코드로 만들어 `workspace_id`가 없지만, 기록 직전에 성공이 아닌 잡이 0건임을 재생 DB에서 확인했고(잡 174개 전부 `succeeded`), 행 수도 1000에 한참 못 미친다. 측정 장애가 있으면 전체 판정도 판정 불가로 하는 규칙을 스펙대로 맞췄다(이번 측정 장애 0이라 결과 불변).
- **리뷰 r1(스펙) blocked 2건, 사용자 결정**:
  - 여러 문서 검사 범위: 스펙을 "근거로 지정한 문서"로 좁히고 근거 밖 겹침은 경고로 했다. v1 시험지의 경고는 m09(`2,400원`이 `l_email`의 단가 협의 메일에 있음) 하나다. m09는 모든 실행 · 조건에서 오답이라 판정에 영향이 없다.
  - 재시도로 복구한 잡: 최종 상태 기준으로 판정한다. 이번 유효 시도의 복구 잡은 임베딩 4개다(`drain-retry.log`: `dead` 3개는 재시도 API 200 뒤 성공, `failed` 1개는 자동 재시도로 성공). `ingestion.json`은 이 기록 필드를 넣기 전 코드로 만들어 `recovered_jobs`가 없고, 이 절이 그 기록을 대신한다. 이후 실행은 `retry-dead`가 `job-retries.jsonl`을 남기고 `ingest-record`가 이를 기록한다.
- **금지 사실 규칙의 결함**: 위 「판정」 절. 거절 4문항은 #254 채점기 한계로 이번에는 원문 검토를 하지 않았다.
