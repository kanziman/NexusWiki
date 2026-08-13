---
phase: 02-security-spine-and-shared-domain
plan: 05
subsystem: shared-domain
tags: [tokenizer, korean-search, bigram, unicode, slug, packages-core, tdd]

# Dependency graph
requires:
  - phase: 01-bootstrap-and-ground-truth
    provides: packages/core 워크스페이스 멤버와 logging.py의 모듈 관례(헤더·상수 배치·keyword-only 시그니처)
  - phase: 02-security-spine-and-shared-domain
    provides: 02-02가 세운 pytest importlib 모드와 ruff TID 활성화 — 같은 패키지에 모듈 2개를 더 얹을 수 있는 상태
provides:
  - nexuswiki_core.tokenizer — normalize() / is_normalized() / bigram() / TSV_TOKENIZER_VERSION
  - nexuswiki_core.slug — slugify(*, title, taken) / SLUG_VERSION / SLUG_MAX_LENGTH
  - 색인·질의가 같은 함수를 쓴다는 계약을 예외로 집행하는 지점 (bigram의 전제 검사)
  - checklists.json > open_questions — 토크나이저 버전 컬럼 타입 불일치를 0007로 넘긴 항목
affects: [02-06, phase-03, phase-04]

# Actuals (#2632)
actuals:
  tokens: 7222
  tasks: 3
  commits: 5

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "전제를 반환값이 아니라 예외로 집행: 조용한 불일치를 소란스러운 실패로 바꾼다"
    - "퇴화 입력의 반환값을 코드와 테스트 양쪽에 계약으로 고정한다"
    - "슬러그도 검색과 같은 normalize()를 딛는다 — 정규화 지점이 하나뿐이다"

key-files:
  created:
    - packages/core/src/nexuswiki_core/tokenizer.py
    - packages/core/src/nexuswiki_core/slug.py
    - packages/core/tests/test_tokenizer.py
    - packages/core/tests/test_slug.py
  modified:
    - checklists.json

key-decisions:
  - "bigram()의 전제 위반을 assert가 아니라 ValueError로 끊었다 — assert는 python -O에서 통째로 사라져 프로덕션에서만 가드가 없는 상태가 된다"
  - "normalize()가 NFKC를 두 번 적용한다 — casefold가 호환 문자를 되살릴 수 있어 한 번만 적용하면 멱등성이 깨진다"
  - "슬러그 폴백 해시를 원본 title이 아니라 normalize(title)에 건다 — 같은 제목을 NFC·NFD·전각 중 무엇으로 써도 같은 폴백을 받는다"
  - "SLUG_MAX_LENGTH = 80, 충돌 접미를 붙일 때 base를 먼저 줄여 상한을 넘지 않게 한다"

patterns-established:
  - "정규화 순서를 docstring에 계약으로 못 박는다: 순서가 결과를 바꾸는 함수는 순서 자체가 API다"
  - "phraseto_tsquery의 <-> 인접성을 DB 없이 문자열 연속 부분열로 재현해 왕복 자가검색을 단위 테스트로 내린다"
  - "허용 문자 집합을 부정 정규식으로 정의하고 그 위에 ⚠️ 근거 주석을 붙인다"

requirements-completed: [DOM-05, DOM-06, DOM-07]

coverage:
  - id: D1
    description: "packages/core의 단일 모듈이 normalize()와 bigram()을 제공하고 TSV_TOKENIZER_VERSION이 알고리즘·정규화 형식·casefold 여부·버전을 한 문자열에 인코딩한다 (DOM-05, D-19)"
    requirement: DOM-05
    verification:
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_tsv_tokenizer_version_encodes_algorithm_form_and_casefold"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_normalize_is_idempotent"
        status: pass
    human_judgment: false
  - id: D2
    description: "NFC·NFD·전각으로 각각 입력한 같은 한국어 문장이 서로를 검색해낸다 (DOM-06 왕복 자가검색)"
    requirement: DOM-06
    verification:
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_three_unicode_forms_retrieve_each_other"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_substring_query_is_a_contiguous_run_inside_the_indexed_bigrams"
        status: pass
    human_judgment: false
  - id: D3
    description: "정규화되지 않은 입력을 bigram()에 넣으면 실패한다 — 색인/질의 불일치가 조용히 통과하지 않는다 (T-02-26)"
    requirement: DOM-05
    verification:
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_bigram_rejects_input_that_was_not_normalized"
        status: pass
      - kind: integration
        ref: "uv run python -c \"...bigram(u.normalize('NFD','한국어'))\" (exit 1)"
        status: pass
    human_judgment: false
  - id: D4
    description: "빈 문자열과 1글자 입력에 대한 bigram() 반환값이 명시되고 예외를 던지지 않는다 (SPEC R8 Edge)"
    requirement: DOM-05
    verification:
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_bigram_of_empty_string_is_empty_string"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_tokenizer.py#test_bigram_of_single_character_is_that_character"
        status: pass
    human_judgment: false
  - id: D5
    description: "같은 title에 대한 1,000회 호출이 동일 슬러그를 낸다 (DOM-07 결정성)"
    requirement: DOM-07
    verification:
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_same_title_yields_the_same_slug_across_a_thousand_calls"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_slug_version_is_pinned"
        status: pass
    human_judgment: false
  - id: D6
    description: "기존 슬러그와 wiki_links.target_slug 양쪽을 합친 taken에 대해 -2·-3 충돌 해소가 일어난다 (T-02-28)"
    requirement: DOM-07
    verification:
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_collision_appends_two_then_three"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_taken_may_merge_existing_slugs_and_wiki_link_target_slugs"
        status: pass
    human_judgment: false
  - id: D7
    description: "한국어 title이 해시나 빈 문자열로 퇴화하지 않고, 정규화 결과가 빈 title에서만 결정적 폴백이 나온다 (prohibition, T-02-29/T-02-30)"
    requirement: DOM-07
    verification:
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_korean_title_is_not_degraded_to_hash"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_empty_normalization_uses_deterministic_fallback"
        status: pass
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_whitespace_only_title_still_returns_a_non_empty_slug"
        status: pass
      - kind: integration
        ref: "grep -icE 'romaniz|revised_romanization|hangul_to_latin|transliterat' packages/core/src/nexuswiki_core/slug.py (0)"
        status: pass
    human_judgment: false
  - id: D8
    description: "슬러그 허용 문자 집합에서 경로 구분자와 점이 제거되어 경로 조작 표면이 없다 (T-02-27)"
    verification:
      - kind: unit
        ref: "packages/core/tests/test_slug.py#test_spaces_become_hyphens_and_disallowed_characters_are_dropped"
        status: pass
    human_judgment: false
  - id: D9
    description: "TSV_TOKENIZER_VERSION 문자열과 smallint 컬럼의 불일치가 은폐되지 않고 0007(02-06-PLAN) 해소 항목으로 원장에 올라갔다 (T-02-31)"
    verification:
      - kind: integration
        ref: "node -e \"...open_questions.filter(q=>/tsv_tokenizer_version/.test(q)).length\" == 1"
        status: pass
      - kind: integration
        ref: "decisions 키 개수 11 유지 (결정이 아니라 미해결 질문으로 기록)"
        status: pass
    human_judgment: false
  - id: D10
    description: "0007이 두 컬럼을 text로 실제로 바꾸어 Phase 3의 색인 쓰기가 성립한다"
    verification: []
    human_judgment: true
    rationale: "이 플랜은 불일치를 원장에 올렸을 뿐 해소하지 않았다. 실제 해소는 02-06-PLAN이 소유하며, 미이행 시 P2-ING-02가 첫 색인 쓰기에서 처음 막힌다."

# Metrics
duration: 25min
completed: 2026-08-06
status: complete
---

# Phase 02 Plan 05: 공용 한국어 토크나이저와 결정적 슬러그 Summary

**색인과 질의가 같은 함수를 쓰도록 강제하는 `normalize`/`bigram` 쌍과, LLM이 아니라 순수 함수가 소유하는 `slugify`를 `packages/core`에 세웠다**

## Performance

- **Duration:** 약 25분
- **Tasks:** 3 (TDD 2 + 원장 1)
- **Files:** 신규 4, 수정 1
- **Tests:** 39 → 62 (신규 23)

## Accomplishments

- **"조용한 실패"가 구조적으로 불가능해졌다.** 이 프로젝트에서 가장 비싼 버그 양식은 색인 시점과 질의 시점 토크나이저가 달라 검색이 오류 없이 비는 것이다. `bigram()`이 `is_normalized()`로 전제를 검사하고 위반 시 `ValueError`로 끊으므로, 호출자가 `normalize()`를 건너뛰면 검색 결과가 비는 대신 즉시 예외가 난다.
- **세 유니코드 형식이 실제로 서로를 검색해낸다.** NFC·NFD·전각으로 쓴 같은 문장이 같은 bigram 열로 수렴하고, 부분 문자열 질의가 색인 bigram의 연속 부분열로 들어 있음을 단언한다. 이 연속 부분열 검사가 `phraseto_tsquery('simple', bigram(q))`의 `<->` 인접성 의미론을 DB 없이 그대로 재현한다.
- **`wiki_pages`의 `(workspace_id, slug)` 업서트 키를 만드는 함수가 생겼다.** 지금까지 이 키는 존재했지만 그것을 채울 코드가 없었다. `slugify()`는 keyword-only 순수 함수이고, `taken`이 `wiki_pages.slug`와 `wiki_links.target_slug`를 합친 집합이어야 한다는 계약을 docstring이 명시한다.
- **한국어 title이 읽히는 URL을 낸다.** `slugify(title='한국어 위키 제목')`이 `한국어-위키-제목`을 낸다. 로마자화도, 비-ASCII 제거 폴백도 쓰지 않는다 — 후자는 한국어 사용자만 읽을 수 없는 URL을 만들어 설계 의도의 정반대가 된다. 관련 심볼 부재를 grep으로 확인한다.
- **계획 중 발견된 타입 불일치를 넘기지 않았다.** `TSV_TOKENIZER_VERSION`은 문자열인데 두 DB 컬럼은 `smallint`다. Phase 2 실행을 막지는 않지만 두 컬럼이 지금 행 0개라 `alter … type text`가 한 줄로 끝나는 창이 지금뿐이다. 원장에 한 줄로 올리고 해소 소유자를 같은 페이즈의 `0007`(02-06-PLAN)로 지정했다.

## Task Commits

1. **Task 1: 공용 토크나이저** — `441332d` (test, RED) → `5b1a941` (feat, GREEN)
2. **Task 2: 왕복 자가검색과 결정적 슬러그** — `6469d07` (test, RED) → `b8014f6` (feat, GREEN)
3. **Task 3: 버전 컬럼 타입 불일치를 원장에** — `4890c82` (docs)

## Files Created/Modified

### 신규

- `packages/core/src/nexuswiki_core/tokenizer.py` — `normalize()`(NFKC → casefold → NFKC 재적용 → 공백 정규화) · `is_normalized()` · `bigram()` · `TSV_TOKENIZER_VERSION`. 상수 바로 아래에 `smallint` 불일치를 가리키는 `⚠️` 주석.
- `packages/core/src/nexuswiki_core/slug.py` — `slugify(*, title, taken)` · `SLUG_VERSION` · `SLUG_MAX_LENGTH`. 허용 문자 집합 부정 정규식 위에 로마자화 배제 근거의 `⚠️` 주석.
- `packages/core/tests/test_tokenizer.py` (12 tests) — 정규화 수렴 3형식, 멱등성, 전제 거부, 퇴화 입력, 왕복 자가검색, 부분 문자열 질의, 버전 상수.
- `packages/core/tests/test_slug.py` (11 tests) — 1,000회 결정성, 한글 유지, 유니코드 3형식 동일 슬러그, 허용 문자, 길이 상한, 충돌 `-2`/`-3`, 두 출처 병합, 폴백 2종, 버전 상수.

### 수정

- `checklists.json` — `open_questions`에 항목 1개 추가 (8 → 9). `decisions`는 건드리지 않았다 (11 유지).

## Decisions Made

- **`bigram()`의 전제 위반을 `assert`가 아니라 `ValueError`로 끊었다.** D-19의 괄호 주석은 "assert 실패"라고 적혀 있으나, `assert`는 `python -O`에서 바이트코드째 제거된다. 프로덕션 이미지에서만 가드가 사라지는 것은 이 가드가 막으려는 실패 양식(조용한 불일치)과 정확히 같은 성질이므로, D-19의 **의도**를 지키려면 `-O`에 지워지지 않는 예외여야 한다. 메시지에 `normalize()`를 먼저 통과시키라는 지시와 현재 토크나이저 버전을 함께 싣는다.
- **`normalize()`가 NFKC를 두 번 적용한다.** `NFKC → casefold` 한 번만으로는 멱등이 아니다 — casefold가 일부 문자를 호환 형태로 되돌려 두 번째 호출에서 결과가 달라질 수 있다. Unicode의 `toNFKC_Casefold`가 정규화를 뒤에 다시 두는 이유와 같다. 멱등성은 SPEC R8이 요구하는 성질이므로 순서를 docstring에 계약으로 못 박았다.
- **슬러그 폴백 해시를 `normalize(title)`에 걸었다.** 플랜은 "원본 title의 안정적 해시 접두사"라고 적었으나, 원본에 걸면 같은 제목을 NFC로 쓴 사람과 NFD로 쓴 사람이 다른 폴백 슬러그를 받는다. D-20이 "슬러그도 같은 정규화를 딛는다"고 정한 이상 폴백만 정규화 앞단을 건너뛸 이유가 없다. `hash()`가 아니라 `sha256`을 쓰므로 실행 간 시드 문제도 없다.
- **`SLUG_MAX_LENGTH = 80.`** `wiki_pages.slug`에 길이 제약이 없어 DB가 정하는 값이 아니다. 충돌 접미(`-2`, `-3`, … `-10`)를 붙일 때 base를 접미 길이만큼 먼저 줄여 상한을 넘지 않게 한다.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] RED 시점 ruff가 미존재 모듈을 third-party로 분류해 import 블록을 잘못 정렬했다**

- **Found during:** Task 1 (RED 커밋 시 pre-commit)
- **Issue:** `nexuswiki_core.tokenizer`가 아직 디스크에 없어 ruff `I001`이 `pytest`와 같은 블록으로 합쳤고, 훅이 파일을 수정해 커밋이 중단되었다. 02-02-SUMMARY의 deviation 5와 같은 원인이다.
- **Fix:** RED 커밋에서는 ruff 출력을 그대로 받아들이고, GREEN 이후 모듈이 실재하게 되었을 때 `ruff check --fix`로 first-party 분류를 재적용했다.
- **Files modified:** `packages/core/tests/test_tokenizer.py`
- **Verification:** `uv run ruff check packages` exit 0
- **Committed in:** `441332d` (RED 형태) → `5b1a941` (정정)

### 계획과의 차이 (자동 수정 아님)

**2. `tokenizer.py`의 `⚠️` 주석이 Task 3이 아니라 Task 1 커밋에 들어갔다**

- 플랜은 이 주석을 Task 3의 `<files>`에 넣었으나, 주석의 자리는 `TSV_TOKENIZER_VERSION` 상수 바로 아래다. 상수를 만드는 Task 1에서 상수만 넣고 그 아래 경고를 뒤에 붙이면 두 커밋 사이에 "값은 있는데 그 값을 쓸 수 없다는 사실은 없는" 구간이 생긴다. 한 커밋으로 합쳤다.
- Task 3의 수용기준(파일이 `smallint`·`open_questions` 문자열을 포함하고 `0007`이 두 컬럼을 `text`로 바꾼다는 사실을 가리킨다)은 그대로 충족된다. Task 3 커밋은 `checklists.json` 한 파일이다.

**3. Task 2의 RED에서 왕복 자가검색 테스트 12건이 즉시 통과했다**

- Task 2가 `test_tokenizer.py`에 추가한 왕복 자가검색·부분 문자열 테스트는 Task 1이 이미 만든 코드를 검증하는 DOM-06 확인 장치이므로 처음부터 green이다. 플랜이 이 순서를 명시적으로 지시했다(Task 2 `<action>` 첫 문단). Task 2의 실제 RED는 `test_slug.py`의 `ModuleNotFoundError`였고, `slug.py` 작성 후 green으로 뒤집혔다.

---

**Total deviations:** 1 auto-fixed (blocking) + 2 문서화된 차이
**Impact on plan:** 범위 확대 없음. 산출물 목록과 수용기준은 플랜 그대로다.

## Issues Encountered

- pre-commit이 Task 1 RED 커밋을 한 번 거부했다(ruff가 파일을 수정). 재-stage 후 재커밋으로 해소했으며 `--no-verify`는 쓰지 않았다.

## Known Stubs

없음. 두 모듈 모두 실제 동작하는 순수 함수이고 23개 테스트가 전 경로를 덮는다. 미완인 것은 코드가 아니라 **DB 컬럼 타입**이며, 그것은 Known Stub이 아니라 `checklists.json > open_questions`에 올라간 미해결 질문이다(02-06-PLAN이 소유).

## Threat Flags

없음. 이 플랜은 새 패키지를 설치하지 않고(표준 라이브러리 `unicodedata` · `hashlib` · `re`만 사용) 네트워크 엔드포인트·인증 경로·스키마를 건드리지 않는다. 플랜 `<threat_model>`의 T-02-26 ~ T-02-31 여섯 항목은 전부 `mitigate`로 처리되어 위 coverage D3·D6·D7·D8·D9가 테스트로 고정한다.

## User Setup Required

`user_setup: []` — 없다.

## Next Phase Readiness

**준비된 것**

- 02-06이 `0007` 섹션에서 `source_chunks.tsv_tokenizer_version`과 `wiki_pages.tsv_tokenizer_version`을 `text`로 바꾸고, `checklists.json > open_questions`의 마지막 항목을 `[해소 YYYY-MM-DD]` 접두로 닫으면 된다. 항목은 배열 원소 한 개다.
- Phase 3의 `P2-ING-02`(청킹)와 `P2-BE-02`(검색)가 `from nexuswiki_core.tokenizer import bigram, normalize, TSV_TOKENIZER_VERSION`으로 색인·질의 양쪽에서 같은 함수를 쓸 수 있다.
- Phase 3의 컴파일러가 LLM이 낸 `title`을 `slugify(*, title, taken)`에 넘겨 `(workspace_id, slug)` 업서트 키를 만든다. 호출 시 `taken`에 `wiki_pages.slug`와 미해소 `wiki_links.target_slug`를 **합쳐** 넘겨야 한다.

**확인이 필요한 것**

- ⚠️ **`0007`이 두 컬럼을 `text`로 바꾸기 전에는 색인 쓰기가 성립하지 않는다.** 지금 두 컬럼은 행이 0개라 무해하지만, 02-06이 이 변경을 빠뜨리면 Phase 3의 첫 색인 INSERT에서 처음 드러난다.
- 질의 측 코드를 쓸 때 bigram 문자열을 `to_tsquery`에 그대로 넣지 말 것 — 공백으로 이어져 syntax error가 난다. `phraseto_tsquery('simple', bigram(q))`를 쓴다(`0002_search_schema.sql:78-88`, 프로젝트 anti-pattern 목록).

## Self-Check: PASSED

- 신규 파일 4개 전부 디스크에 존재 (`tokenizer.py`, `slug.py`, `test_tokenizer.py`, `test_slug.py`)
- 커밋 5개 전부 git 이력에 존재 (`441332d`, `5b1a941`, `6469d07`, `b8014f6`, `4890c82`)
- 플랜 `<verification>` 6개 항목 전부 통과: `uv run pytest -q` 62 passed · 두 버전 상수 테스트 고정 · 3형식 왕복 자가검색 · 1,000회 결정성 · `open_questions` 8 → 9 · `uv run ruff check` exit 0
- `pre-commit run --all-files` 전부 Passed

---
*Phase: 02-security-spine-and-shared-domain*
*Completed: 2026-08-06*
