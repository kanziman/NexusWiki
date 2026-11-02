# Spec Conformance 리뷰 — ai-context-budget r2

- 판정: blocked
- 대상: `git diff 704e61c..a64bda8` (`a64bda8`), PR #194 브랜치 `feat/ai-context-budget`
- 일시: 2026-11-03T00:49:15+09:00

## 범위와 실행한 확인

r1 이후 추가된 `1e92dbe`, `a64bda8`을 중심으로 대조했다. 두 커밋이 건드리지 않은 `ai-control-room`과 `usage-guardrails` 시나리오는 r1 판정을 승계했고, 이번에 코드를 다시 읽지 않았다.

- 테스트 재실행: `uv run pytest packages/core/tests/test_context_budget.py packages/core/tests/test_router.py packages/core/tests/test_rrf.py apps/api/tests/test_ask_router.py apps/worker/tests/test_handlers.py apps/worker/tests/test_controlled_ai_evidence.py` 결과 128 passed
- `openspec validate --specs` 결과 38 passed
- `select_dual_evidence`와 `allocate_ask_context_budget`을 임시 스크립트로 직접 호출해 근거 구성을 실측했다. 저장소 파일은 바꾸지 않았다.

## 시나리오 판정

### 이번 라운드 대조 대상

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 컨텍스트 토큰 예산과 이중 근거 쿼터 / 위키가 검색 상위를 독차지해도 원문 근거가 프롬프트에 실린다 | 부분 충족 | 경로: `apps/api/src/api/services/retrieval.py:169-173`, `apps/api/src/api/services/ask.py:747-751`, `packages/core/src/nexuswiki_core/context_budget.py:70-102`. 테스트: `apps/api/tests/test_ask_router.py:962`, `packages/core/tests/test_context_budget.py:84`. 원문이 프롬프트에 실리는 것은 충족한다. 그러나 **원문이 모자라지 않은데도 절반을 채우지 못하는 입력이 있다**(조치 1) |
| Router 결정의 shadow 기록 / 내용이 같은 원문의 재컴파일 | 동작 충족, 계약 문구와 불일치 | 경로: `apps/worker/src/worker/handlers/compile.py:158-184`, `compile.py:260-292`, `packages/core/src/nexuswiki_core/router.py:80-102`. 테스트: `apps/worker/tests/test_handlers.py:854`, `apps/worker/tests/test_controlled_ai_evidence.py:212`. 다만 지문 입력이 스펙이 적은 `content_hash`와 다르다(조치 2) |
| Router 결정의 shadow 기록 / 지문이 같아도 기존 위키 페이지가 없을 때 | 충족 | `compile.py:274-291`, `router.py:86-102` · 테스트 `apps/worker/tests/test_handlers.py:872` |
| Router 결정의 shadow 기록 / 요구사항 본문의 "직전 성공 컴파일" 조건 | 충족 | `apps/worker/src/worker/db/service.py:469-` 가 `jobs.status=eq.succeeded`로 거른다. 이 필터 자체를 검증하는 테스트는 이번 범위에서 확인하지 않았다 |
| Router 결정의 shadow 기록 / 재처리로 본문이 바뀐 경우 (스펙 시나리오 아님, `a64bda8`의 AC) | 스펙 밖 | `compile.py:155-162` · 테스트 `apps/worker/tests/test_handlers.py:972`. 조치 2의 판단 대상이다 |

### 두 커밋의 영향을 받는 기존 시나리오

| Requirement / Scenario | 결과 | 증거 |
| --- | --- | --- |
| Ask 컨텍스트 토큰 예산과 이중 근거 쿼터 / 긴 위키 근거가 있어도 원문 근거가 함께 보존된다 | 충족 | 선택 후에도 `allocate_ask_context_budget`이 위키와 원문 최상위 1건씩을 보장한다 `context_budget.py:158-162` · 테스트 `packages/core/tests/test_context_budget.py:12`, `apps/api/tests/test_ask_router.py:848` |
| Ask 컨텍스트 토큰 예산과 이중 근거 쿼터 / 한 종류 근거만 있을 때 남은 예산을 사용한다 | 충족 | `context_budget.py:98-101`이 한 종류만 있는 후보를 k개까지 채운다 · 테스트 `packages/core/tests/test_context_budget.py:100` |
| Ask 컨텍스트 토큰 예산과 이중 근거 쿼터 / 벡터 채널과 어휘 채널이 같은 위키 문서를 반환한다 | 충족 | 두 커밋이 `rrf.py`를 바꾸지 않았다. 선택이 `EvidenceHit`을 그대로 넘긴다 `context_budget.py:102` · 테스트 `packages/core/tests/test_rrf.py` 통과 |
| 재현 가능한 통제 전후 증거 / Step 2 예산 및 단락 시나리오의 전후 비교 | 충족, 커밋 값 갱신 필요 | 관측값은 HEAD에서 일치한다 `apps/worker/tests/test_controlled_ai_evidence.py:824`. `after.commit`은 조치 4 참조 |

### r1 승계 (두 커밋이 건드리지 않음)

| 대상 | 결과 | 근거 |
| --- | --- | --- |
| `ai-control-room` 시나리오 전체 | r1 승계 | `git diff --stat 704e61c..a64bda8`에 관련 파일 없음 |
| `usage-guardrails` 시나리오 전체 | r1 승계 | 충돌 판정과 `max_tokens` 경로는 변경 없음. `compile.py`의 변경은 지문 계산뿐이다 |
| `ai-request-tracing` / 제목과 정확히 일치하는 질문, 근거가 없는 질문 | r1 승계 | `test_ask_router.py` 통과. 선택은 RRF 순서를 유지한다 `context_budget.py:102` |
| `ai-controls-showcase` / 충돌 판정 비용, 증거 파일 검사, 미구현 단계 | r1 승계 | `test_controlled_ai_evidence.py` 통과 |

## 조치가 필요한 항목

### 1. 원문이 한 소스에 몰리면 절반을 채우지 못한다 (코드 수정으로 해결)

근거 Scenario: "시스템은 위키와 원문을 절반씩 골라 컨텍스트를 조립하고, 한 종류가 모자라면 빈자리를 다른 종류로 채운다"

`per_source_limit=3`에 걸린 원문 자리를 채우는 2차 순회(`context_budget.py:98-101`)가 종류를 가리지 않고 RRF 순서로 고른다. 위키가 앞서 있으면 그 자리는 위키가 가져간다.

| 후보 (`requested_k=8`) | 위키 | 원문 | 스펙 기대 |
| --- | --- | --- | --- |
| 위키 8 + 서로 다른 소스의 원문 8 | 4 | 4 | 4 / 4 |
| **위키 8 + 같은 소스의 원문 8** | **5** | **3** | **4 / 4** |
| 위키 8 + 원문 2 | 6 | 2 | 6 / 2 (원문 부족) |

굵은 행은 이 수정의 동기였던 "위키 독차지" 입력이고, 원문이 모자라지도 않다. 원문 하나만 수집한 워크스페이스에서 그대로 나오는 모양이다. `per_source_limit`은 스펙과 design 어디에도 없다. docstring은 "근거가 모자라면 그 제한을 풀어 채운다"고 적지만, 제한이 풀리기 전에 위키가 자리를 가져간다. 기존 테스트 `packages/core/tests/test_context_budget.py:110`은 위키가 정확히 4건이거나 원문만 있는 입력만 봐서 이 경우를 놓친다.

제안: 다른 종류로 넘어가기 전에 같은 종류 안에서 소스 제한을 먼저 풀어 원문 몫을 채운다. 위키 8 + 같은 소스 원문 8에서 4 / 4를 단언하는 회귀 테스트를 추가한다.

### 2. 지문 입력이 스펙의 `content_hash`와 다르다 (사람의 결정 필요, blocked 사유)

근거: `openspec/specs/ai-request-tracing/spec.md:59`와 delta spec의 "입력 지문(`content_hash`, `template_id`, `model`)이 직전 성공 컴파일과 같고 ... 공급자 LLM 호출을 MUST 생략"

`a64bda8`은 지문의 첫 입력을 `raw_sources.content_hash`에서 잘린 뒤 컴파일 본문의 sha256으로 바꿨다(`compile.py:155-162`). 코드 주석과 커밋 메시지가 `content_hash`를 그 컬럼의 뜻으로 쓰고 있고, 스키마에 그 이름은 이 컬럼뿐이다(`supabase/migrations/0001_core_schema.sql:105`). 그런데 이 커밋은 스펙을 고치지 않았다. design의 "리뷰 후 결정"도 Ask 수정만 다루고, D5는 여전히 "동일 `content_hash`"로 시나리오를 설명한다(`design.md:88`).

스펙 문구를 컬럼으로 읽으면 `content_hash`, 템플릿, 모델이 같고 페이지가 있으므로 MUST 생략이다. 테스트 `apps/worker/tests/test_handlers.py:972`는 정확히 그 입력에서 LLM 호출을 단언하므로 스펙과 반대다. 시나리오 제목 "내용이 같은 원문"으로 읽으면 구현이 맞다. 즉 스펙이 두 해석을 모두 허용한다.

코드만으로는 해결되지 않는다. 컬럼 기반으로 되돌리면 문구는 맞지만, 재처리된 원문을 건너뛰어 위키가 조용히 낡는 결함이 돌아온다.

제안: 구현 쪽 해석을 채택하기를 권한다. 사람이 승인하면 `ai-request-tracing` 스펙의 지문 정의를 "컴파일 입력 본문의 해시"로 고치고, 위 입력을 시나리오로 추가하며, design에 결정을 기록한다. 함께 알아 둘 점이 두 가지 있다.

- 지문은 잘린 본문 기준이므로 `COMPILE_MAX_INPUT_TOKENS` 밖의 변경은 재컴파일을 일으키지 않는다. 컴파일 입력이 같으니 이치에 맞지만, 스펙에 적어 둘 내용이다.
- 배포 전에 기록된 지문은 공식이 달라 일치하지 않는다. 배포 후 첫 재컴파일은 한 번 LLM을 호출한다. 안전한 방향이지만 일회성 비용이 있다.

### 3. 실제 `RetrievalService`가 `candidates`를 채우는지 검증하는 테스트가 없다 (코드 수정으로 해결)

근거 Scenario: "융합 결과의 상위 k개가 전부 위키이고 그 뒤에 원문 근거가 있다"

Ask 통합 테스트는 대역이 `candidates`를 직접 넣는다(`apps/api/tests/test_ask_router.py:940-958`). `apps/api/tests/test_retrieval_service.py`에는 `candidates` 단언이 없다. 구현 자체는 코드를 읽어 맞음을 확인했다(`retrieval.py:169-173`). 그러나 `candidates`의 기본값이 빈 목록이고 Ask가 빈 목록이면 조용히 `evidence`로 돌아가므로(`ask.py:747`), 이 배선이 끊겨도 어떤 테스트도 실패하지 않고 이 결함이 그대로 재발한다. design이 이 결함을 놓친 이유로 적은 "대역이 이미 양쪽 근거를 돌려줘서"와 같은 유형의 공백이다.

제안: `test_retrieval_service.py`에 위키 채널이 상위 k를 채우는 입력에서 `evidence`는 k개이고 `candidates`에는 뒤의 원문이 남는다는 단언을 추가한다.

### 4. 새 시나리오가 delta spec에 없고, 증거의 `after.commit`이 어떤 브랜치에도 없다 (기록 정리)

- 시나리오 "위키가 검색 상위를 독차지해도"는 `openspec/specs/grounded-answering/spec.md:99`에만 있고 `openspec/changes/archive/2026-11-03-ai-context-budget/specs/grounded-answering/spec.md`에는 없다. `feature-planning-workflow`는 delta spec을 계획의 기준으로 두므로, 아카이브와 main spec이 어긋난다. 조치 2와 함께 어느 쪽을 정본으로 할지 정해 맞추기를 권한다.
- `apps/dashboard/content/controlled-ai/step1.json`의 `after.commit` 7건이 모두 `3744e4f`다. 이 커밋은 `704e61c`로 대체되어 HEAD의 조상이 아니고, 이를 포함하는 브랜치도 없다. 관측값은 HEAD에서 맞지만(`test_controlled_ai_evidence.py:824`) 공개 화면이 찾을 수 없는 해시를 표시한다. 직전 main의 증거는 main에 도달 가능한 `184c5b4`를 가리키므로, 병합 후 커밋으로 갱신하는 단계에서 해소할 수 있다. 그 단계를 빠뜨리지 않도록 확인이 필요하다.

## 판정에 영향을 주지 않은 관찰

- 절반 선택은 선택 단계의 분배이고, 토큰 예산 아래 최종 구성은 달라진다. 3단계가 RRF 순서로 채워 위키가 먼저 예산을 쓴다(`context_budget.py:215`). 위키 4 + 원문 4를 선택한 상태에서 6000토큰으로 실측하면, 위키 본문이 길 때 최종 구성은 위키 2 + 원문 1 또는 위키 1 + 원문 1이었다. 요구사항의 "최소 1건씩"은 지켜지므로 위반으로 보지 않았다. 다만 시나리오의 "절반씩 ... 조립"을 최종 프롬프트 구성으로 읽을 의도였다면 추가 작업이 필요하다.
- `requested_k=1`은 API가 허용한다(`apps/api/src/api/routers/ask.py:41`). 이때 위키 몫이 0이라 위키가 1위여도 원문 1건만 고른다. 한 건으로는 이중 근거가 불가능하므로 위반으로 보지 않았다.
- `/retrieval` 응답은 `evidence`만 내보내므로(`apps/api/src/api/routers/retrieval.py:106`) 검색 계약은 바뀌지 않았다.

## 판정 근거

`blocked`다. 조치 2가 스펙 문구 수정 또는 그 해석에 대한 사람의 결정을 요구하기 때문이다. 코드를 스펙 문구에 맞추면 재처리 원문을 건너뛰는 결함이 돌아오므로 코드 수정만으로는 닫을 수 없다. 구현의 방향 자체는 타당해 보이며, 결정이 필요한 범위는 지문 정의 한 줄이다. 조치 1과 3은 그 자체로는 `needs_fix`이며 스펙 범위 안에서 코드로 고칠 수 있다. 사람이 조치 2를 승인하고 스펙을 고친 뒤 조치 1, 3을 반영하면 3라운드에서 재판정할 수 있다.

## 리뷰 중 나타난 미커밋 변경

리뷰 시작 시 작업 트리는 깨끗했다. 보고서 작성 중 이 리뷰어가 만들지 않은 미커밋 변경이 나타났다. 위 판정의 대상은 커밋 `a64bda8`이므로 이 변경을 판정에 반영하지 않았다. 누가 어떤 승인으로 만들었는지는 이 리뷰에서 확인할 수 없다.

| 파일 | 내용 | 관련 조치 | 남은 것 |
| --- | --- | --- | --- |
| `openspec/specs/ai-request-tracing/spec.md` | 지문 정의를 "컴파일 본문 해시"로 수정 | 조치 2 | 아카이브 delta spec은 여전히 `content_hash`이고, 본문이 바뀐 경우의 시나리오는 없다. 사람의 승인 여부를 확인할 수 없다 |
| `openspec/changes/archive/2026-11-03-ai-context-budget/design.md` | 지문 변경 결정을 기록 | 조치 2 | D5(`design.md:88`)의 "동일 `content_hash`" 문구는 그대로다 |
| `apps/api/tests/test_retrieval_service.py` | `candidates` 단언 테스트 추가 | 조치 3 | 커밋 필요 |

`packages/core/src/nexuswiki_core/context_budget.py`에는 변경이 없으므로 조치 1은 그대로 남아 있다. 이 변경이 커밋되고 스펙 수정이 사람의 승인을 받았다면, 3라운드의 쟁점은 조치 1과 조치 4로 좁혀지고 예상 등급은 `needs_fix`다.
