# Tenant Isolation 리뷰 — ai-context-budget r2

- 판정: pass
- 대상: `git diff 704e61c..a64bda8` (`a64bda8deb28aba01f5d8f05195b24a7ace2787f`). r1 이후 추가된 커밋 `1e92dbe`, `a64bda8`만 본다
- 일시: 2026-11-03T00:49:02+0900

## 검사 결과

| # | 항목 | 결과 | 근거 |
| --- | --- | --- | --- |
| A-1 | 사용자 경로의 service_role | 통과 | `select_dual_evidence`는 DB를 호출하지 않는 순수 함수다(`packages/core/src/nexuswiki_core/context_budget.py:70`). 후보는 요청자 JWT의 `user_db`로 부른 RPC 결과이며(`apps/api/src/api/services/ask.py:742`), 본문 조회도 같은 `user_db`와 `workspace_id=eq.` 필터를 쓴다. diff에 `service_client`, `service_role` 추가가 없다 |
| A-2 | 신규 테이블 RLS 동시 활성화 | 해당 없음 | `supabase/` 변경 없음 |
| A-3 | anon GRANT·정책 | 해당 없음 | `supabase/` 변경 없음 |
| A-4 | 워커의 명시적 workspace_id 필터 | 통과 | 지문 계산 입력인 `list_source_chunks`가 `workspace_id`와 `raw_source_id`로 거른다(`apps/worker/src/worker/db/service.py:315-326`). `latest_compile_fingerprint`(`service.py:469-493`)와 `list_wiki_pages_for_source`(`service.py:412-424`)도 동일하며 이번 diff에서 바뀌지 않았다 |
| A-5 | 자식 테이블 복합 FK | 해당 없음 | 신규 테이블 없음 |
| B-6 | 0행 → 403 매핑 | 해당 없음 | 사용자 경로에 새 UPDATE/DELETE가 없다. `/retrieval`의 `_require_member` 게이트는 그대로다 |
| B-7 | 42501 → 403 매핑 | 해당 없음 | 사용자 경로에 새 쓰기가 없다 |
| C-8 | 핸들러 멱등성 | 통과 | 아래 「a64bda8 검토」 참조. 업서트 키 `(workspace_id, slug)`는 그대로고, 지문 입력은 `chunk_index.asc`로 정렬되어 재실행해도 같은 값이 나온다 |
| C-9 | jobs 직접 UPDATE 금지 | 통과 | diff에 `jobs` 직접 쓰기가 없다. SKIP 경로는 기존 `complete_job_and_chain`을 쓴다(`apps/worker/src/worker/handlers/compile.py:170-182`) |
| D-10 | 벡터 검색 iterative_scan | 통과 | 벡터 RPC를 고치지 않았다. Ask가 이제 k 뒤쪽 후보까지 쓰지만, `search_chunks`와 `search_wiki_embeddings`는 함수 수준에서 `hnsw.iterative_scan = 'strict_order'`를 건다(`supabase/migrations/0011_retrieval.sql:76`, `:147`) |
| D-11 | 토크나이저 일치 | 해당 없음 | 토크나이저와 `p_tokenizer_version` 전달 코드 변경 없음 |
| D-12 | search_tsv 생성 컬럼 | 해당 없음 | 스키마 변경 없음 |
| D-13 | 프롬프트 str.format | 통과 | diff에 `.format(` 추가가 없다 |
| D-14 | LLM 컨텍스트 인용 앵커 | 통과 | 선택은 `EvidenceHit`를 그대로 넘겨 메타데이터가 보존된다. 원문 채널 RPC인 `search_chunks`(`0011_retrieval.sql:140-142`)와 `search_source_lexical`(`:117`) 모두 `raw_source_id`, `chunk_index`를 돌려준다. 별칭은 선택 후 `build_issuance_map`이 매기므로 프롬프트와 발급 맵이 어긋나지 않는다 |
| E-15 | 마이그레이션 번호 | 해당 없음 | 새 마이그레이션 없음 |

## 지정 확인 사항

### 1e92dbe — `/retrieval`로 candidates가 새는가

새지 않는다.

- 응답은 필드 2개짜리 `RetrievalResponse`를 명시적으로 조립하며, `result.evidence`와 `result.meta`만 읽는다(`apps/api/src/api/routers/retrieval.py:106`, `:108`).
- `candidates`는 `meta`에 들어가지 않고(`apps/api/src/api/services/retrieval.py:171-182`), 소비처는 `ask.py:747-750` 한 곳뿐이다.
- 최상위 키는 `test_retrieval_service.py:257`이 `{"evidence", "meta"}`로 고정한다.
- 통제 보고서는 건수만 싣는다(`ask.py:532-533`). 후보 id가 턴 기록이나 Control Room으로 가는 경로도 없다.
- 후보는 모두 같은 요청의 RLS 범위 안에서 나온 행이므로, 후보가 늘어도 테넌트 경계는 달라지지 않는다.

실제 `RetrievalService`에 가짜 DB를 붙여 실행해 관측했다. `evidence`는 위키 8건, `candidates`는 20건, `meta`에 `candidates` 키 없음, `meta.returned`는 8이었다. `/retrieval` 계약은 유지되고, `select_dual_evidence` 결과에는 원문이 포함됐다.

### a64bda8 — 지문과 SKIP_UNCHANGED

새로운 조용한 실패를 찾지 못했다. 시나리오별 결과는 다음과 같다.

| 시나리오 | 결과 |
| --- | --- |
| 재처리로 본문이 바뀜 | 지문이 달라져 재컴파일한다. 이번 수정의 목적이며 `test_handlers.py:972`가 고정한다 |
| 같은 본문으로 잡 재실행 | 정렬이 고정되어 있어 지문이 같고, 기존 페이지가 있으면 SKIP한다. LLM 이중 호출이 없다 |
| 시도 실패 후 재시도 | `latest_compile_fingerprint`가 `jobs.status = succeeded`로 거르므로(`service.py:477-489`), 사용량만 기록된 실패 시도를 처리 완료로 오판하지 않는다 |
| 업서트 도중 실패 후 재시도 | 잡이 아직 성공 상태가 아니라 직전 성공 지문과 달라 재컴파일하고, 슬러그 업서트로 수렴한다 |
| 예산을 넘는 꼬리 부분만 바뀜 | 지문은 잘린 뒤의 `source_content`를 해시하므로 SKIP한다. 재컴파일해도 LLM 입력이 같으므로 결함이 아니다 |
| `COMPILE_MAX_INPUT_TOKENS` 변경 | 잘린 본문이 달라지면 지문도 달라져 재컴파일한다 |
| 본문이 빈 채로 컴파일 진입 | `compile`은 `parse`의 체인으로만 인큐된다(`parse.py:259-263`). `parse`는 텍스트 공백(`parse.py:109-110`)과 추출 품질(`assert_extraction_quality`)에서 먼저 실패한다 |
| 배포 직후의 기존 지문 | 옛 공식의 값과 일치하지 않아 원문별 첫 재처리에서 LLM을 1회 더 호출한다. 비용은 들지만 SKIP 오판 방향이 아니므로 안전하다 |

## 조치가 필요한 항목

없음. 아래는 판정에 영향을 주지 않는 권고다.

1. **실제 `RetrievalService`의 `candidates` 채움을 고정하는 테스트가 없다** (심각도: 보통, 권고)
   - 위치: `apps/api/src/api/services/ask.py:747`, `apps/api/src/api/services/retrieval.py:173`, `apps/api/tests/test_ask_router.py:958`
   - 깨지는 것: `ask.py:747`의 `if result.candidates:`는 후보가 비면 조용히 `evidence`로 돌아간다. 테스트에서 `candidates`를 다루는 곳은 대역 `_WikiDominatedRetrieval`뿐이고, `test_retrieval_service.py`는 이를 검사하지 않는다. 따라서 `retrieval.py:173`이 회귀하면 단위 테스트는 통과한 채 위키 독점과 이중 인용률 0이 되돌아올 수 있다. design.md가 기록한 원래 결함("대역이 이미 양쪽 근거를 돌려줘서 보지 못했다")과 같은 구조다.
   - 조치: `test_retrieval_service.py`에 상위 k개가 위키로 채워질 때 `candidates`에 원문이 남는지 확인하는 단언을 추가한다.

2. **지문 계약 문구가 구현보다 뒤처졌다** (심각도: 보통, 권고. spec-conformance 영역)
   - 위치: `openspec/specs/ai-request-tracing/spec.md:59`, `openspec/changes/archive/2026-11-03-ai-context-budget/design.md:88`
   - 깨지는 것: 런타임 영향은 없다. 스펙은 여전히 지문 입력을 `content_hash`로 적고 있어, `compile.py:156`의 ⚠️ 주석이 금지한 `raw_sources.content_hash`로 되돌리는 변경이 스펙을 근거로 정당화될 수 있다. design.md의 「리뷰 후 결정」에도 `1e92dbe`만 기록되어 있고 `a64bda8`은 없다.
   - 조치: 스펙에 "컴파일할 본문의 해시"라고 명시하고 결정을 원장에 남긴다.

3. **단일 원문 워크스페이스에서는 위키와 원문이 절반씩 나뉘지 않는다** (심각도: 낮음, spec-conformance 영역)
   - 위치: `packages/core/src/nexuswiki_core/context_budget.py:98-101`
   - 깨지는 것: 원문이 하나뿐이고 청크와 위키가 충분하면 `per_source_limit=3` 때문에 원문은 3건에 그친다. 빈자리는 종류와 무관하게 RRF 순서로 채워져 위키 5, 원문 3이 된다(위 실행에서 관측). 원문 근거는 프롬프트에 실리므로 이중 Citation은 유지된다. 다만 스펙 시나리오의 "절반씩"과 다르다.
   - 조치: 이 비율이 의도라면 스펙 문구를 보정하고, 아니면 채움 단계에서 부족한 종류를 먼저 채운다.

## 검증 범위

- 새로 실행한 테스트
  - `packages/core/tests/test_context_budget.py`, `apps/worker/tests/test_handlers.py`, `apps/worker/tests/test_controlled_ai_evidence.py`: 62 passed
  - `apps/api/tests/test_ask_router.py`, `apps/api/tests/test_retrieval_service.py`: 54 passed
- 실행하지 않은 것: 로컬 스택이 필요한 `test_tenant_isolation_full_path.py`와 격리 왕복 테스트. 이번 diff에 정책, RPC, 사용자 경로 쓰기 변경이 없어 코드 대조로 판정했다.
- 범위 밖: `704e61c` 이전 변경분은 r1이 다뤘다. `run_compile`은 재컴파일 시 슬러그가 바뀐 옛 페이지를 지우지 않는데, 이번 diff가 만든 동작은 아니어서 판정에 넣지 않았다. 다만 재처리가 실제로 재컴파일로 이어지게 되었으므로, 옛 슬러그 페이지가 낡은 내용과 역참조를 유지한 채 남는 경로는 별도로 볼 가치가 있다.

## 판정 근거

r1 이후 두 커밋에서 검사 항목 위반을 찾지 못했다. `candidates`는 `/retrieval` 응답과 통제 보고서로 나가지 않고, 지문 변경은 실패 시도를 성공으로 오판하지 않으며 SKIP 오판 대신 재컴파일 쪽으로 기운다. 권고 3건은 테넌트 경계나 데이터 손상과 무관하고 현재 동작을 깨지 않으므로 `pass`로 판정한다.
