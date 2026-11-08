# 검증 기록 — retrieval-evidence-ablation

결과 해석은 `docs/ops/ask-sample-replay.md`의 「위키 기여 · 제목 머리말 임베딩 6조건 실험」 절에 있다. 이 파일은 재현과 대조에 필요한 사실만 둔다.

## 실험 기록 (2026-11-08)

원본은 Git에서 제외되는 `.worktrees/ablation-evidence-20261108/`에 있다.

| 파일 | 내용 | sha256 |
| --- | --- | --- |
| `registration.json` | 사전 등록(12:14:01Z), 답변 상한 3,000,000 micros | `561ac97854c7762e8062b5e847efc17e5b4d96b99ed0fb1e6f48af0a9f3bd30b` |
| `query-vectors.json` | 고정 질의 벡터 30개 | `f037e1daee4048da01abf1069b02816ab5d11a56584f1187842c9583d2f47636` |
| `retrieve.json` | 검색 6조건 | `cbe3f2148117948a16194df5ad2978847ef13e8b52202b98674a87229e6d2c30` |
| `answer.json` | 답변 3조건 × 30문항 | `4082cff3d121929338a57a7080bef626333c6524baf753f36f7abaf0cb3740a3` |
| `query-vectors.failed-502.json` | 무효: 공급자 502로 전부 실패한 첫 시도 | `f31546fc7cb25abc9817ed632cdd35034e066839f98cb3e9819af7d5d1a967ba` |

고정 입력: 수집 스냅샷 `65809ec4e3b673c5…`(전체 값은 `retrieve.json`의 `fixed_inputs`), 임베딩 버전 `baai/bge-m3@deepinfra/fp32-v1`, 정책 `hybrid-rrf-v2`, k=8, 그래프 꺼짐.

측정 전 검사: 모델 동일성 cosine 0.999635, 운영 RPC 동등성 30문항 불일치 0건, 제목 벡터 35/35. 답변 재생은 상한 전에 끝났다(`stopped: null`).

비용: 임베딩 67회 134 micros, 답변 90턴 2,199,514 micros. `retrieve.json`의 `cost`(임베딩 1회 3 micros)는 마지막 실행분만이다. 질의 벡터 30개와 제목 벡터 35개는 JSON 파싱 결함으로 멈춘 직전 실행에서 만들어 재사용했고, 합계 134 micros는 재생 DB `usage_events`(kind `embedding`)에서 실측했다. 리뷰 r1 뒤로 기록은 `embedding_scope: this_run_only`와 재사용 여부·재사용 비용을 함께 남긴다.

답변 단계 채널 장애: 이 실행의 답변 기록은 리뷰 r1 지적(`meta.missing_channels` 미기록) 이전 코드로 만들어 턴별 채널 실패 여부가 없다. 같은 고정 질의 벡터로 잰 검색 6조건은 채널 장애 0건이었고 90턴 모두 `resolved`였다. 이후 실행부터는 실패한 채널이 있으면 실행 장애로 분류한다.

## 계획 이탈

- **task 4.1의 스냅샷 해시 대조**: RRF v2 기록에는 수집 스냅샷 해시가 없어 해시로 대조하지 못했다. 대신 RRF v2 before·after API 로그에 찍힌 워크스페이스 id(`51b80299…`)와 원문 8개의 제목이 fixture와 일치함을 확인했다. 이번 기록부터 스냅샷 해시를 남겨 다음 실험은 `--expect-snapshot`으로 대조할 수 있다.
- **task 4.3의 "운영 임베딩 행이 실험 전 해시와 같다"**: 실험 전 해시를 남기지 않았다. 실험 후 해시는 원문 `52cde043a6644b0e179cf60ab85c450b`, 위키 `64a89bbd2fc60f4125e999507558c76e`(`md5(string_agg(id || embedding))`)다. 실험 코드는 운영 테이블에 쓰지 않으며(쓰기는 `ablation` 스키마, Ask 턴 저장, 사용량 기록뿐), 측정 시작 시 동등성 검사가 운영 벡터와 그 사본의 일치를 확인했다.
- **실행 중 고친 결함 3건**: 실패한 질의 벡터의 고정, 여러 줄 JSON 파싱, 커밋되지 않은 코드의 `git_sha` 표기. 모두 테스트를 추가했거나(앞의 둘) 동작을 확인했다(`+dirty`). 기록의 `git_sha`는 `016ad7b`로 찍혔지만 실제로는 그 위의 커밋되지 않은 작업 트리였다.
- **로컬 상태 변경**(사용자 승인): 재생 사용자의 로컬 비밀번호 재설정, 월 한도 $5 → $9 일시 조정 후 $5 복원. 미정산 예약은 지우지 않았다. `ablation` 스키마 삭제 확인(`pg_namespace` 0건).
