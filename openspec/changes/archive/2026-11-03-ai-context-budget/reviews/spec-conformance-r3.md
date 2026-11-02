# Spec Conformance 리뷰 — ai-context-budget r3

- 판정: pass
- 대상: `git diff a64bda8..HEAD` (`92daa6a`), PR #194 브랜치 `feat/ai-context-budget`
- 일시: 2026-11-03T00:56:16+09:00

## 범위와 실행한 확인

r2 지적 4건의 해결 여부를 대조하는 최종 라운드다. `26235f9`, `92daa6a`가 건드리지 않은 시나리오는 r2 판정을 승계했고, 이번에 코드를 다시 읽지 않았다.

- 테스트 재실행: `uv run pytest packages/core/tests/test_context_budget.py packages/core/tests/test_router.py packages/core/tests/test_rrf.py apps/api/tests/test_ask_router.py apps/api/tests/test_retrieval_service.py apps/worker/tests/test_handlers.py apps/worker/tests/test_controlled_ai_evidence.py` 결과 139 passed
- 로컬 스택 E2E: `uv run pytest apps/api/tests/test_pipeline_e2e.py -rs` 결과 3 passed, skip 없음. 스택은 `supabase_kong_NexusWiki`(54421)이고 공급자는 대역이다(`apps/api/tests/fixtures/pipeline.py:80`)
- `openspec validate --specs` 결과 38 passed. change가 이미 아카이브되어 `openspec validate <change> --strict`는 돌리지 않았다
- `select_dual_evidence`를 임시 스크립트로 직접 호출해 근거 구성을 실측했다. 저장소 파일은 바꾸지 않았다
- `git diff --stat 26235f9..HEAD`는 `step1.json`뿐이다. 즉 증거의 `26235f9`와 HEAD는 코드가 같다

## 시나리오 판정

### r2 지적 대조

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 컨텍스트 토큰 예산과 이중 근거 쿼터 / 위키가 검색 상위를 독차지해도 원문 근거가 프롬프트에 실린다 (r2 조치 1) | 충족 | 2차 순회가 같은 종류 안에서 먼저 몫을 채운다 `packages/core/src/nexuswiki_core/context_budget.py:102-108`, 다른 종류는 3차에서만 채운다 `context_budget.py:110-114`. 테스트 `packages/core/tests/test_context_budget.py:130`. 배선 `apps/api/src/api/services/ask.py:747-750` |
| Router 결정의 shadow 기록 / 입력 지문 정의 (r2 조치 2) | 충족 | 스펙 "컴파일 본문 해시": `openspec/specs/ai-request-tracing/spec.md:59`, 아카이브 delta `.../specs/ai-request-tracing/spec.md:4`. 구현: `apps/worker/src/worker/handlers/compile.py:158-162`가 컴파일에 넣는 `source_content`의 sha256을 쓰고, 같은 값을 `compile.py:199`에 기록한다. 테스트 `apps/worker/tests/test_handlers.py:972`, E2E `apps/api/tests/test_pipeline_e2e.py:31` |
| Ask 컨텍스트 토큰 예산과 이중 근거 쿼터 / `candidates` 배선 (r2 조치 3) | 충족 | 구현 `apps/api/src/api/services/retrieval.py:169-173` · 테스트 `apps/api/tests/test_retrieval_service.py:267` |
| 위 시나리오의 delta spec 반영 (r2 조치 4) | 충족 | `.../specs/grounded-answering/spec.md:10`과 `openspec/specs/grounded-answering/spec.md:99`의 시나리오 본문이 같다 |
| 재현 가능한 통제 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 (r2 조치 4) | 충족 | `apps/dashboard/content/controlled-ai/step1.json`의 `after.commit` 7건이 모두 `26235f9`이고 `git merge-base --is-ancestor`로 HEAD의 조상임을 확인했다. `before.commit` `79b68fe`도 조상이다. 관측값 일치 `apps/worker/tests/test_controlled_ai_evidence.py:824` 통과 |

### r2 승계

| 대상 | 결과 | 근거 |
| --- | --- | --- |
| Ask 예산 / 긴 위키 근거가 있어도 원문 근거 보존, 한 종류만 있을 때, 같은 위키 문서 반환 | 충족 | 선택 함수 외 예산 조립은 바뀌지 않았다. `test_context_budget.py`, `test_ask_router.py`, `test_rrf.py` 재실행 통과 |
| Router / 내용이 같은 원문의 재컴파일, 지문이 같아도 위키 페이지가 없을 때, 직전 성공 조건 | 충족 | `git diff a64bda8..HEAD -- apps/worker apps/api/src` 변경 없음. `test_handlers.py` 재실행 통과 |
| `ai-control-room`, `usage-guardrails`, `ai-controls-showcase`의 나머지, `ai-request-tracing`의 나머지 | r1·r2 승계 | 두 커밋의 diff에 관련 구현 파일 없음. 이번에 코드를 다시 읽지 않았다 |

## r2 지적별 대조

### 1. 위키 8건 + 같은 원문 8건 — 해결

`requested_k=8` 실측 결과다.

| 후보 | 위키 | 원문 | 스펙 기대 | RRF 순서 유지 |
| --- | --- | --- | --- | --- |
| 위키 8 + 같은 소스 원문 8 | 4 | 4 | 4 / 4 | 예 |
| 위키 8 + 서로 다른 소스 원문 8 | 4 | 4 | 4 / 4 | 예 |
| 같은 소스 원문 8 + 위키 8 (순서 반대) | 4 | 4 | 4 / 4 | 예 |
| 위키 8 + 소스 A 원문 5 + 소스 B 원문 1 | 4 | 4 | 4 / 4 | 예 |
| 위키 8 + 원문 2 | 6 | 2 | 원문 부족, 위키로 채움 | 예 |
| 위키 2 + 같은 소스 원문 8 | 2 | 6 | 위키 부족, 원문으로 채움 | 예 |
| 위키 8만 | 8 | 0 | 한 종류만 | 예 |
| 같은 소스 원문 8만 | 0 | 8 | 한 종류만 | 예 |

r2에서 5 / 3이던 첫 행이 4 / 4가 됐고, 빈자리 채움 동작은 유지된다.

### 2. 지문 입력 문구 — 해결

호출자가 정한 범위대로 스펙과 구현의 일치만 봤다. 스펙 본문과 아카이브 delta 모두 "컴파일 본문 해시"이고, 구현도 그 값을 쓴다. `design.md:88`의 문구도 "동일 본문"으로 고쳐졌고, 결정은 `design.md:110`에 기록됐다.

재처리 E2E를 HEAD에서 실행해 통과를 확인했다. `apps/api/tests/test_pipeline_e2e.py:31`은 본문을 바꿔 재처리한 뒤 사용량 행이 늘어나는지, 즉 LLM이 다시 호출되는지 단언한다. `test_handlers.py:972`는 `content_hash`가 같고 본문만 다를 때 `STANDARD`로 호출하는지 단언한다.

"사용자가 작업 전체를 위임했다"는 전제는 호출자가 전달한 내용이고, 이 리뷰에서 사용자에게 직접 확인하지 않았다. PR에서 사람이 이 스펙 변경을 볼 수 있도록 아래 관찰 1과 함께 적어 둔다.

### 3. `candidates` 배선 테스트 — 해결

`test_retrieval_service.py:267`은 실제 `RetrievalService`를 `requested_k=1`로 호출해 `evidence`가 1건이고 `candidates`에 위키와 원문이 모두 남는지 단언한다. r2 제안의 "위키가 상위를 채우는 입력"을 글자 그대로 쓰지는 않았지만, k=1이면 `evidence`는 한 종류뿐이므로 다른 종류가 k 밖에 남는 것을 확인하는 셈이다.

코드를 읽고 판단하면, 배선이 끊겨 `candidates`가 기본값 `[]`이면 `candidates[0]`에서 실패하고, `candidates`가 잘린 값이면 종류 집합 단언에서 실패한다. 이 변이를 실제로 돌려 보지는 않았다.

### 4. delta spec과 `after.commit` — 해결

시나리오가 아카이브 delta에 들어갔고, `after.commit`이 브랜치 이력에 있다. `origin/feat/ai-context-budget`도 `92daa6a`이므로 원격에서도 찾을 수 있다.

## 조치가 필요한 항목

없음.

## 판정에 영향을 주지 않은 관찰

1. **`proposal.md:10`에 `content_hash` 표기가 남아 있다.** `proposal.md:18`의 "원문 해시"도 같은 맥락이다. 판정 기준인 spec과 design은 고쳐졌으므로 위반이 아니다. 다만 아카이브를 읽는 사람은 제안 시점 문구와 결정 후 문구가 다른 것을 보게 된다.
2. **`content_hash`가 같고 본문이 바뀐 경우의 전용 시나리오는 스펙에 없다.** 요구사항 본문의 지문 정의가 이 동작을 포괄하고 테스트도 있으므로 미충족은 아니다. r2가 함께 제안한 "`COMPILE_MAX_INPUT_TOKENS` 밖의 변경은 재컴파일을 일으키지 않는다"는 점도 스펙에 명시되지 않았다. "컴파일 본문"이 잘린 본문을 뜻한다고 읽으면 구현과 일치한다.
3. **`26235f9`는 squash merge 후 main의 조상이 되지 않는다.** 현재 `main`의 조상이 아니며, 이 저장소의 PR은 squash로 병합된다. 이번 지적의 기준인 브랜치 이력은 충족한다. `after.commit`이 main에 도달 가능해야 한다면 병합 후 갱신이 필요하다. 전례는 `b635b51`(#176)이 `0de7ea1`을 `184c5b4`로 바꾼 것이다.
4. **절반 선택은 선택 단계의 분배다.** r2가 적은 대로 토큰 예산 아래 최종 구성은 달라질 수 있고, 요구사항의 "최소 1건씩"은 지켜진다. 이번 커밋으로 바뀌지 않았다.

## 판정 근거

`pass`다. r2의 지적 4건이 HEAD에서 모두 해결됐고, 각각 코드 또는 기록과 테스트로 확인했다. r2를 `blocked`로 만든 지문 정의 쟁점은 스펙이 구현 쪽으로 고쳐져 불일치가 사라졌다. 남은 관찰은 스펙 미충족이 아니다.
