# Phase 2: Security Spine and Shared Domain - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-05
**Phase:** 2-Security Spine and Shared Domain
**Areas discussed:** DB 트랜스포트 스파이크, service key 격리 집행 강도, UserDb 403 매핑, 워커 하트비트 vs 잡 분할

---

## 영역 선택

| Option | Description | Selected |
|--------|-------------|----------|
| DB 트랜스포트 스파이크 (DOM-01) | RPC vs asyncpg+Supavisor, 판정 기준과 tie-break | ✓ |
| service key 격리 집행 강도 (SEC-01/02/03/05) | 린트로 충분한가, 구조적 분리가 필요한가 | ✓ |
| UserDb 403 매핑의 형태 (SEC-04/06) | 0행=403을 한 곳에서 강제하는 방법, 정상 빈 결과와의 구분 | ✓ |
| 워커 하트비트 vs 잡 분할 (DOM-08/09) | 0007에 heartbeat 컬럼 추가 vs COMP-04 잡 분할로 해결 | ✓ |

**User's choice:** 4개 영역 전부
**Notes:** 논의 전 스카우트에서 STATE.md의 Phase 2 블로커 하나(`jobs` 하트비트 컬럼 유무)가 해소됨 — 컬럼 없음을 `0003_jobs.sql:55-57`로 확인했고, 이것이 4번 영역의 실제 선택지를 만들었다.

---

## DB 트랜스포트 스파이크 — Q1: 판정 기준

| Option | Description | Selected |
|--------|-------------|----------|
| `current_setting()` 반환값 확인 | RPC 안에서 GUC 값을 읽어 반환. 가장 간단하지만 "설정됨"과 "플래너가 따랐음"이 다름 | |
| EXPLAIN 계획 + 반환 행 수 (추천) | `EXPLAIN (ANALYZE)`로 HNSW Index Scan 사용 여부 + post-filter 후 k개 충족 여부를 함께 확인. RTV-08 회귀 테스트와 같은 장치 | ✓ |
| 결과 집합 동등성 비교 | psql 직접 연결과 RPC 경로의 반환 id 집합 비교. 직접적이지만 코퍼스가 작으면 변별력 없음 | |

**User's choice:** EXPLAIN 계획 + 반환 행 수
**Notes:** → CONTEXT.md D-01. 이 선택이 Phase 4 RTV-08에 대한 선투자가 된다는 점을 CONTEXT의 `<specifics>`에 기록.

---

## DB 트랜스포트 스파이크 — Q2: 스파이크 코퍼스

| Option | Description | Selected |
|--------|-------------|----------|
| 합성 데이터 — 적대적 분포 (추천) | 랜덤 벡터 수만~십만 행, 타깃 워크스페이스가 1~2%만 차지해 post-filter를 강제. 비용 0, 재현 가능, 판정 조건 통제 | ✓ |
| 실제 문서 소량 임베딩 | 현실적이지만 양이 작아 post-filter 압박이 없고, Phase 3 수집 파이프라인이 없어 수작업 필요 | |
| 둘 다 | 합성으로 판정, 실데이터로 한국어 경로 확인. 더 철저하지만 스파이크 범위가 커짐 | |

**User's choice:** 합성 데이터 — 적대적 분포
**Notes:** → CONTEXT.md D-02. 이 질문의 배경은 "스파이크가 통과했지만 아무것도 판정하지 못하는" 실패 모드였고, 사용자 선택이 그 위험을 직접 제거한다.

---

## 이후 진행 방식 전환

**User's response (freeform):** "추천안대로 진행해줘"

이 시점부터 남은 질문(트랜스포트 tie-break, 산출물 위치, service key 격리 3문항, UserDb 403 4문항, 하트비트/잡분할 4문항)은 개별 질의 없이 Claude 권장안으로 확정했다. 각 결정은 CONTEXT.md에 근거 및 되돌리기 비용과 함께 기록됨 — D-03~D-05(트랜스포트), D-06~D-10(격리), D-11~D-14(403), D-15~D-18(큐).

---

## Claude's Discretion

사용자가 "추천안대로"로 위임한 영역. 전부 CONTEXT.md `<decisions>`에 근거와 함께 기록되어 있으며 planner/researcher가 뒤집을 수 있다(이유를 남길 것).

- **D-03** 트랜스포트 tie-break — GUC 3종 전부 적용될 때만 RPC, 하나라도 미달이면 asyncpg. 부분 적용 수용 시 Phase 4에서 반드시 되돌아온다는 판단
- **D-05** 결정 잠금 위치 — `checklists.json > decisions.db_transport` (프로젝트 수명 결정이므로 phase CONTEXT가 아님)
- **D-06** "역량 부재"의 위치 — 단일 이미지(Phase 1 D-01)라 import는 막히지 않으므로 집행 무게중심을 *키의 부재*에 둔다
- **D-07/D-08** `BaseAppSettings` 계층 + `service_client()` 팩토리 서명
- **D-11** 0행=403을 쓰기 경로 메서드에만 적용 (정상 빈 조회와 원리적으로 구분되는 유일한 방법)
- **D-12** 403 vs 404 — 열거 공격 방지를 위해 구분하지 않음
- **D-16** 하트비트 컬럼 미추가, 잡 분할로 해결 (DOM-09의 조건부 지시 + COMP-04와 일치)
- **D-18** `release_job()` 신설 — `attempts`가 claim 시점 증가라 자발적 반납이 독약 잡 카운트를 소모하는 문제
- **D-19/D-20** 토크나이저 버전 문자열 형식, 슬러그 규칙 (한글 로마자화 배제)
- **D-21** `0007` 내부 구성 순서와 스파이크 선행 의존
- **D-22** `LLM_MODEL` 불일치는 Phase 3으로 유지

## Deferred Ideas

- `jobs` 하트비트 컬럼 — Phase 3 실측 후 필요하면 `0008`
- `reap_stale_jobs` 최종 타임아웃 — Phase 3에서 LLM p99로 확정
- `LLM_MODEL` 기본값 불일치 — Phase 3 (COMP-01)
- `relaxed_order` vs `strict_order` 벤치마크 (RTV-04) — Phase 4
- 골든 질의 세트 (RTV-06) — Phase 4. Phase 2 합성 코퍼스와 혼동 금지
- `checklists.json`/`CLAUDE.md`의 `apps/fastapi-backend` 경로 표기 정리
