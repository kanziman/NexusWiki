---
phase: 03-ingest-and-compile-pipeline
plan: 03
subsystem: shared-domain
tags: [chunking, tokenizer, enum, supply-chain, dockerfile, tdd, pure-function]
requires:
  - "supabase/migrations/0001_core_schema.sql (CHECK 열거 7종의 원문)"
  - "supabase/migrations/0003_jobs.sql:31-36 (jobs.type에 CHECK를 걸지 않은 유일한 예외)"
  - "supabase/migrations/0009_pipeline_ops.sql (jobs.status 6값 확장 · usage_events.kind — 03-02 산출물)"
  - "packages/core/src/nexuswiki_core/tokenizer.py (버전 상수 규약 · 순수 모듈 형식 원본)"
  - "Dockerfile (단일 이미지 · builder/runtime 2스테이지 — 01-CONTEXT.md > D-01)"
provides:
  - "nexuswiki_core.domain — StrEnum 10종 + DB_CHECK_ENUMS 8항 대조표"
  - "nexuswiki_core.chunking — CHUNKER_VERSION · CHUNK_TARGET_TOKENS · CHUNK_OVERLAP_TOKENS · Chunk · count_tokens · chunk_text"
  - "packages/core 의존성에 pypdf==6.15.0 · tiktoken==0.13.0 (uv.lock 고정)"
  - "Dockerfile TIKTOKEN_CACHE_DIR — BPE 어휘를 빌드 시점에 이미지에 굽는다"
  - "마이그레이션 CHECK 리터럴을 실제로 읽어 파이썬 enum과 대조하는 테스트 파서"
affects:
  - "COMP-02 워커 기동 가드 — DB_CHECK_ENUMS가 enum_check_values(0009 §7)와 대조할 대상"
  - "ING-05 parse 핸들러 — chunk_text가 source_chunks의 char_start/char_end/chunker_version을 채운다"
  - "03-06 extract.py — pypdf가 이 플랜에서 설치됐다"
  - "COMP-06 embed 핸들러 — EmbeddingScope가 jobs_dedup_idx의 target_id 접미 규약"
  - "Phase 4 골든 세트(RTV-06) — CHUNK_TARGET_TOKENS/OVERLAP이 반증 대상 상수로 노출됨"
tech-stack:
  added:
    - "pypdf==6.15.0 (BSD-3-Clause, github.com/py-pdf/pypdf)"
    - "tiktoken==0.13.0 (MIT, github.com/openai/tiktoken)"
  patterns:
    - "버전 상수에 알고리즘+파라미터를 전부 인코딩해 재처리 범위를 좁힌다 (TSV_TOKENIZER_VERSION 규약)"
    - "무거운 리소스는 lru_cache로 첫 호출에 만든다 — import 부작용 금지"
    - "테스트가 SQL 마이그레이션을 실제로 읽어 파이썬 상수와 대조한다 (베껴 적기 방지)"
    - "네트워크를 타는 런타임 다운로드는 빌드 시점 캐시 워밍으로 옮긴다"
key-files:
  created:
    - packages/core/src/nexuswiki_core/domain.py
    - packages/core/src/nexuswiki_core/chunking.py
    - packages/core/tests/test_domain.py
    - packages/core/tests/test_chunking.py
  modified:
    - packages/core/pyproject.toml
    - uv.lock
    - Dockerfile
decisions:
  - "D-P4 청크 토큰은 tiktoken cl100k_base로 센다 — bge-m3의 XLM-R SentencePiece를 의도적으로 근사(과대평가 방향)"
  - "D-P5 목표 512토큰 · 오버랩 64토큰 · 재귀 분리자 — 문헌 근거 없는 경험적 출발점, Phase 4가 반증 대상"
  - "D-P6 페이지 수준 축소 재처리는 페이지 삭제가 아니라 sources 역참조 제거 (기록만, 구현은 03-04/03-08)"
  - "오버랩은 예산과 무관하게 마지막 조각 하나를 반드시 겹친다 — 예산만으로는 산문에서 오버랩이 0이 된다"
  - "청크 내용은 조각을 이어붙이지 않고 원문에서 다시 잘라 넣는다 — ING-05 왕복 속성의 유일한 구조적 근거"
  - "workspaces.kind는 CHECK가 있어도 DB_CHECK_ENUMS에 넣지 않았다 — 소비자 없는 대조 항목을 만들지 않는다"
metrics:
  duration: "20m"
  completed: 2026-08-08
actuals:
  tokens: 13199
  tasks: 2
  commits: 3
status: complete
---

# Phase 3 Plan 03: 공유 도메인 모듈과 첫 외부 패키지 Summary

워커·API가 함께 쓸 순수 모듈 두 개(`domain.py` · `chunking.py`)를 `packages/core`에 세우고, 저장소
역사상 처음으로 외부 Python 패키지 2종을 차단형 공급망 검증을 거쳐 정확 핀으로 들였다. 그리고
`tiktoken`이 런타임에 인터넷으로 나가는 경로를 빌드 시점 캐시로 닫았다.

## 무엇을 했나

| Task | 내용 | 커밋 |
|---|---|---|
| 0 | 공급망 legitimacy 체크포인트 — 사람이 승인 (이 에이전트 이전 세션) | — |
| 1 | `pypdf==6.15.0` · `tiktoken==0.13.0` 도입 + Dockerfile BPE 캐시 워밍 | `653edac` |
| 2 (RED) | `test_domain.py` · `test_chunking.py` — 실패하는 계약 테스트 26개 | `953a809` |
| 2 (GREEN) | `domain.py` · `chunking.py` 구현 | `abf0bc9` |

## 설치된 정확 버전

`uv`가 해석해 `uv.lock`에 고정한 값이며, 추측이 아니라 실제 해석 결과다.

| 패키지 | 고정 버전 | 라이선스 | 저장소 |
|---|---|---|---|
| `pypdf` | **6.15.0** | BSD-3-Clause | `github.com/py-pdf/pypdf` |
| `tiktoken` | **0.13.0** | MIT | `github.com/openai/tiktoken` |

`pypdf`가 BSD-3인 것이 이 플랜의 통과 조건이었다 — `checklists.json`과 REQUIREMENTS.md `Out of Scope`가
PyMuPDF를 기각한 사유가 AGPL이므로, 대체재가 AGPL이면 같은 이유로 쓸 수 없었다.

전이 의존 5종이 함께 들어왔다: `regex==2026.7.19` · `requests==2.34.2` · `urllib3==2.7.0` ·
`charset-normalizer==3.4.9` (모두 `tiktoken` 경유). 워크스페이스는 43 → 48패키지가 됐다.

## 관측 결과

### BPE 캐시가 실제로 이미지에 있다 — 네트워크를 끊고 확인했다

주장이 아니라 관측이다. `docker build .` 성공 후:

```
docker run --rm --network none nexuswiki-build-check python -c "...tiktoken.get_encoding('cl100k_base')"
→ TIKTOKEN_CACHE_DIR = /app/.tiktoken
→ cached files = ['9b5ad71b2ce5302211f9c61530b329a4922fc6a4']
→ offline encode ok: [24486, 89059, 255, 32179, 49464, 255, 169, 24153]
```

`--network none`에서 인코딩이 성공했다는 것은 런타임 스테이지가 어휘 파일을 **자기 안에** 갖고 있다는
뜻이다. 위협 T-03-15(런타임 BPE 다운로드)가 이 관측으로 닫혔다.

### 실제 한국어 문서에서의 청킹 (`03-CONTEXT.md`, 16,696자 / 10,064토큰)

| 항목 | 값 |
|---|---|
| 청크 수 | 31 |
| 청크 토큰 | min 183 · max 511 · avg 407 (상한 512) |
| 청크 문자수 | avg 672 |
| 오버랩 문자수 | min **0** · max 530 · avg 138 |
| `content[char_start:char_end] == content` | 전건 True |
| 첫 청크 0에서 시작 · 마지막 청크 `len(content)`에서 끝 | True |

⚠️ **오버랩 min이 0이다.** 청크가 조각 하나로만 이루어진 경우 다음 청크가 그 조각 바로 뒤에서
시작한다(겹치지 않고 맞닿는다). 이것은 결함이 아니라 아래 정정 1의 의도된 경계 조건이며, 전체
덮기는 그래도 유지된다 — 다만 "모든 인접 쌍이 겹친다"는 아니라는 사실을 여기 남긴다.

### 게이트

`uv sync --frozen --all-packages` exit 0 · `docker build .` 성공 ·
`uv run pytest -rs` **173 passed** (기존 147 + 신규 26) · `uv run ruff check apps packages` exit 0 ·
`pre-commit run --all-files` 통과.

플랜의 수용 기준 커맨드 전건:

| 확인 | 기대 | 실측 |
|---|---|---|
| `('jobs','type') in DB_CHECK_ENUMS` | `False` | `False` |
| `len(DB_CHECK_ENUMS)` | `8` | `8` |
| `chunk_text('   \n  ')` | `[]` | `[]` |
| `CHUNKER_VERSION` | `512`·`64` 포함 | `recursive-cl100k-512-64-v1` |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] 오버랩이 산문에서 아예 생기지 않았다**

- **Found during:** Task 2 GREEN — RED 테스트 26개 중 `test_adjacent_chunks_overlap_on_prose_input` 하나만 빨갛게 남았다
- **Issue:** 플랜의 지시("직전 윈도의 끝에서 `CHUNK_OVERLAP_TOKENS` 만큼 되돌아간 지점에서 시작")를
  글자 그대로 구현하면, 되돌릴 수 있는 것은 **조각 단위**인데 산문의 조각은 문단 하나(~130토큰)라
  64토큰 예산에 들어가는 조각이 하나도 없다. 결과적으로 오버랩 인덱스가 항상 `end_index + 1`이 되어
  **모든 인접 청크가 정확히 맞닿기만 하고 한 글자도 겹치지 않았다**. `CHUNK_OVERLAP_TOKENS = 64`는
  설정되어 있는데 효과가 0인 상태였고, 오류도 경고도 없다. D-P5가 오버랩을 둔 이유(문단 경계에서
  잘린 문장이 어느 한쪽 청크에는 온전히 들어간다)가 조용히 사라지는 자리다.
- **Fix:** `_overlap_start`가 `min(end_index, index + 1)`을 돌려주게 해 **예산과 무관하게 마지막 조각
  하나는 반드시 겹치도록** 했다. 청크가 조각 하나뿐일 때만 겹치지 않는다 — 그 조각을 되풀이하면
  다음 청크가 거의 전부 오버랩이 되어 진전이 멈추기 때문이고, 그 경우는 `previous_end_index` 가드가
  받는다. 인과를 함수 docstring에 `⚠️`로 남겼다.
- **Files modified:** `packages/core/src/nexuswiki_core/chunking.py`
- **Commit:** `abf0bc9`
- **⚠️ 계약 문구 정정:** 이 정정으로 플랜 must_have의 "인접 청크가 **설정된 토큰만큼** 겹치며"는
  글자 그대로는 더 이상 참이 아니다. 실제 계약은 "인접 청크는 오버랩 예산 **이상** 겹치되, 청크가
  조각 하나뿐이면 겹치지 않고 맞닿는다"이다. 나머지 세 절(상한 · `chunk_index` 연속 · 빈틈 없음)은
  그대로 참이다.

### 플랜이 지시하지 않았으나 더한 것

**2. [Rule 2 - 검증 강화] 테스트가 마이그레이션 SQL을 실제로 읽어 대조한다**

플랜은 `<behavior>`에 "값 집합이 `0001:138`의 CHECK와 같다"를 요구했다. 파이썬 리터럴을 파이썬
리터럴과 비교하는 테스트로 만들면 그 단언은 **손으로 베껴 적은 값이 손으로 베껴 적은 값과 같다**는
뜻밖에 되지 않는다 — 마이그레이션이 나중에 값을 늘려도 아무 테스트도 깨지지 않고, 워커는 DB가
거부하는 값을 조용히 만들어 낸다. 그래서 `test_domain.py`가 `supabase/migrations/*.sql`을 파일명
순서로 읽어 `check (col in (...))` 리터럴을 뽑고 `DB_CHECK_ENUMS`와 대조한다.

두 가지 함정을 실제로 처리해야 했다:

- `kind` 컬럼이 `workspaces`(`personal`/`team`)와 `usage_events`(`llm`/`embedding`) 양쪽에 있다 →
  CHECK 하나하나를 **직전 `create/alter table` 문**에 귀속시킨다
- `jobs.status`는 `0003`(5값)과 `0009`(6값) 양쪽에 있다 → 파일명 순서로 **뒤가 이긴다**

파서 자체가 vacuous해지는 것을 막는 자가검사(`jobs.status` 6값 · `workspaces.kind` 2값)도 함께 뒀다.

**3. [Rule 2 - 상한 보장] 조각 토큰 합이 아니라 실측으로 상한을 지킨다**

조각별 토큰 수를 더해 윈도를 만들면 BPE가 조각 경계를 넘어 병합될 때 실제 값과 어긋난다. 상한은
합이 아니라 실제로 센 값으로 지켜야 하므로 `_pack`이 패킹 후 `count_tokens(원문 슬라이스)`로 다시
확인하고 넘으면 줄인다. 조각 하나는 `_atomic_spans`가 이미 상한 이하임을 보장하므로 종료한다.

### 플랜 대비 판단을 달리한 것

**4. `("workspaces","kind")`를 `DB_CHECK_ENUMS`에 넣지 않았다**

플랜은 8개 키를 명시했고 `workspaces.kind`는 그 목록에 없다. 파서를 붙이고 나서 이 컬럼에도 CHECK가
있다는 것이 드러났지만(`0001:35`), 워크스페이스 종류를 읽거나 쓰는 애플리케이션 경로가 아직 없어
**소비자 없는 대조 항목**을 만들지 않았다. 그 경로가 생기면 한 줄을 더한다. 이 판단과 그 조건을
`DB_CHECK_ENUMS`의 docstring에 남겼다.

그 결과 대조 테스트는 단방향이다 — "표에 있는 항목은 DB와 같다"는 강제하지만 "DB에 있는 모든 enum이
표에 있다"는 강제하지 않는다. 후자를 강제하면 오늘 `workspaces.kind`에서 깨진다.

## Flagged Assumptions (이 플랜이 닫지 못한 것)

플랜의 `## Flagged Planner Assumptions`가 ING-05를 `unclassified`로 표시했다. 실행이 그 가정을
바꾸지 않았으므로 그대로 열려 있다:

- **`cl100k_base`는 bge-m3의 실제 토크나이저가 아니다** (XLM-R SentencePiece). 한국어를 더 많이 세는
  방향의 근사라 512 목표가 8192 예산을 넘길 위험은 구조적으로 없지만, "512 토큰"이 모델이 보는 512는
  아니다. `CHUNKER_VERSION`의 `cl100k` 조각이 나중에 진짜 토크나이저로 바꿀 때 재청킹 범위를 좁힌다.
- **512 / 64에는 문헌 근거가 없다.** 읽을 만한 인용 단위와 배치 비용 사이의 경험적 출발점이며,
  Phase 4 골든 질의 세트(RTV-06)가 반증할 대상이다. 값은 상수로 노출되어 있다.

두 사실 모두 `chunking.py` 모듈 docstring에 `⚠️`로 남아 있다 — 코드를 읽는 사람이 SUMMARY를 찾아
가지 않아도 보이는 자리다.

## Known Stubs

없음. 두 모듈 모두 완전한 구현이며 계약 테스트로 행동이 고정되어 있다.

`JobType`의 `parse`/`compile`/`link_sync`/`embed`는 아직 핸들러가 없지만 스텁이 아니라 **소비자가 뒤
플랜에 있는 상수**다(`worker.handlers.HANDLERS` 등록은 03-04 이후). `EmbeddingScope`도 마찬가지로
COMP-06이 소비한다.

## Threat Flags

새로 발견된 보안 표면은 없다. 플랜의 `<threat_model>` 5건 처분 결과:

| Threat | 처분 | 실제로 한 것 |
|---|---|---|
| T-03-SC (PyPI 설치) | mitigate | 설치 **이전** 차단형 사람 체크포인트 통과. `pypdf` BSD-3 · `tiktoken` MIT 확인, 이름은 정확히 `pypdf`/`tiktoken` |
| T-03-15 (런타임 BPE 다운로드) | mitigate | 빌드 시점 캐시 + `--network none` 실행으로 관측 확인 |
| T-03-16 (분리자 없는 초장문) | mitigate | `_force_split` 반분할 + `char_start` 엄격 증가 불변식. 6000자 무공백 입력 테스트가 고정 |
| T-03-17 (초대형 원문) | transfer | 순수 함수에 상한을 두지 않았다 — API 경계(03-05)의 몫 |
| T-03-18 (청크 내용 로그 노출) | mitigate | `chunking.py`에 로거가 없다 (`get_logger` import 자체가 없음) |

## Self-Check: PASSED

- `packages/core/src/nexuswiki_core/domain.py` FOUND
- `packages/core/src/nexuswiki_core/chunking.py` FOUND
- `packages/core/tests/test_domain.py` FOUND
- `packages/core/tests/test_chunking.py` FOUND
- 커밋 `653edac` · `953a809` · `abf0bc9` FOUND
- `packages/core/pyproject.toml`에 `pypdf==6.15.0`와 `tiktoken==0.13.0`이 각각 정확히 한 줄
- `Dockerfile`의 builder·runtime 양쪽에 `TIKTOKEN_CACHE_DIR`, `COPY --from=builder /app/.tiktoken` 존재
- `uv run pytest -rs` 173 passed · `pre-commit run --all-files` 통과
