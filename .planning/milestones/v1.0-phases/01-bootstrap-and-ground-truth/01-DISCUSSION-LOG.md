# Phase 1: Bootstrap and Ground Truth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-02
**Phase:** 1-bootstrap-and-ground-truth
**Areas discussed:** Dockerfile 구조와 서비스 분기, `0005` 정책의 3세그먼트 검사 구현

---

## 영역 선택

제시된 후보 7개 중 사용자가 2개를 선택했다.

| 후보 영역 | 선택 |
|-----------|------|
| Dockerfile 구조와 서비스 분기 | ✓ |
| monorepo 레이아웃과 Next.js 위치 | |
| `/health/ready`의 DB 접근 경로 | |
| Railway 설정 방식과 환경변수 스코프 | |
| `0005` 정책의 3세그먼트 검사 구현 | ✓ |
| structlog 프로세서 체인과 redaction | |
| RTT 측정 도구와 문서 위치 | |

---

## Dockerfile 구조와 서비스 분기

### 단일 이미지에서 api와 worker를 어떻게 가릅니까?

| Option | Description | Selected |
|--------|-------------|----------|
| start command만 다르게 | Dockerfile 하나, CMD 기본값은 api. worker 서비스에만 Custom Start Command. 이미지가 문자 그대로 하나라 R8 1차 판정(다이제스트 일치)이 자연히 통과 | ✓ |
| entrypoint.sh + SERVICE_ROLE env | 분기 로직을 저장소 안에 두고 역할을 로그에 찍기 쉽다. 대신 shell이 PID 1이 되어 SIGTERM 전달을 직접 챙겨야 함 | |
| 멀티스테이지 타깃 2개 | `--target api` / `--target worker`. 깔끔해 보이지만 두 이미지가 반드시 다른 다이제스트라 R8 1차 판정이 구조적으로 불가능 | |

**User's choice:** start command만 다르게
**Notes:** 선택 근거는 취향이 아니라 SPEC R8 판정 조건. 멀티스테이지는 1차 판정을 원천 봉쇄한다는 점이 결정적이었다.

### 이미지 안에서 uv를 어떻게 씁니까?

| Option | Description | Selected |
|--------|-------------|----------|
| 멀티스테이지 + venv 복사 | builder에서 `uv sync --frozen --no-dev` → 런타임엔 `/app/.venv`만 COPY. 런타임에 uv 불필요, R4의 `--frozen`과 동일한 lockfile 경로 | ✓ |
| 단일 스테이지 + uv sync | 런타임 이미지에 uv를 남긴다. 단순하고 디버깅 편하지만 이미지가 커짐 | |
| uv export → pip install | requirements.txt로 반출 후 pip. uv 없는 환경과 호환되지만 워크스페이스 로컬 패키지(`packages/core`) 처리가 까다로움 | |

**User's choice:** 멀티스테이지 + venv 복사

### Railway PORT 주입 vs exec form CMD의 `$PORT` 미확장 — 시그널 전달과 함께 어떻게?

| Option | Description | Selected |
|--------|-------------|----------|
| 파이썬이 PORT를 읽게 | exec form CMD 유지, uvicorn을 파이썬 엔트리에서 구동하며 `os.environ["PORT"]` 사용. PID 1이 파이썬이라 SIGTERM 직접 도달 | ✓ |
| `sh -c` 안에서 exec | `CMD ["sh","-c","exec uvicorn ... --port $PORT"]`. `exec`가 shell을 치환해 PID 1이 uvicorn이 됨. 또다른 정답이지만 `exec` 키워드를 빠뜨리면 조용히 깨짐 | |
| PORT 고정 + Railway 포트 설정 | 8000으로 고정하고 Railway에 명시. 가장 단순하지만 플랫폼 관습을 거스름 | |

**User's choice:** 파이썬이 PORT를 읽게
**Notes:** worker의 graceful shutdown(SPEC R6 범위)이 이 결정에 직접 걸려 있다. `sh -c` + `exec`도 기술적으로 정답이나, 실패 시 증상이 "재배포 때 잡 유실"로만 나타나 진단이 어렵다는 점을 고려.

### Python 버전을 어떻게 고정합니까? (호스트는 3.11.5)

| Option | Description | Selected |
|--------|-------------|----------|
| 3.12 + .python-version | `requires-python = ">=3.12"`, `.python-version` 커밋, 이미지 `python:3.12-slim`. uv가 로컬에 3.12 자동 설치 | ✓ |
| 3.13 최신 | 가장 새 기능. 후속 페이즈 의존성(pypdf·asyncpg)의 휠 호환성이 덜 검증됨 | |
| 3.11 (호스트와 일치) | 로컬과 정확히 같다. 대신 3.12의 개선을 포기하고 지원 종료가 더 빨리 옴 | |

**User's choice:** 3.12 + .python-version

**후속 질문:** "더 물을까요, 다음 영역으로?" → **다음 영역으로** (`.dockerignore` 범위 · 레이어 캐싱 · 비루트 유저는 Claude 재량으로 위임)

---

## `0005` 정책의 3세그먼트 검사 구현

논의 전 확인한 코드 근거: 경로 규약은 `0001_core_schema.sql:108` 주석에만 존재 · 멤버십 헬퍼는 `0004_rls_policies.sql:44-95`에 `security definer` + `grant … to authenticated`로 존재 · `raw_sources`는 UPDATE 정책 부재로 불변

### 3세그먼트 + 멤버십 검사를 어떻게 쓰겠습니까?

| Option | Description | Selected |
|--------|-------------|----------|
| 전용 헬퍼 함수 | `public.storage_path_workspace(text) returns uuid`를 0005에 신설. 정규식으로 형태 검사, 불일치 시 null. 정책 4개가 짧아지고 로직이 한 곳에 모임 | ✓ |
| 정규식을 정책마다 인라인 | 각 정책에 정규식 + 캐스팅을 직접. 함수 추가 없지만 같은 정규식이 4번 복사됨 | |
| foldername 길이만 검사 | `array_length(storage.foldername(name),1) = 2` + 캐스팅. 가장 짧지만 첫 세그먼트가 UUID가 아니면 22P02 예외 → 거부가 아니라 에러 | |

**User's choice:** 전용 헬퍼 함수
**Notes:** 22P02 예외 회피가 실질적 결정 요인. 정책에서 캐스팅이 예외를 던지면 "조용한 거부"가 아니라 500 에러가 된다.

### 역할 등급을 기존 RLS 베이스라인과 맞춥니까?

| Option | Description | Selected |
|--------|-------------|----------|
| 기존 베이스라인 대칭 | SELECT=`is_workspace_member`, INSERT=`has_workspace_role(ws,'editor')`, DELETE=`has_workspace_role(ws,'owner')`. 0004와 같은 모양 | ✓ |
| 멤버면 전부 허용 | `is_workspace_member` 하나로 네 정책 처리. 단순하지만 viewer가 업로드·삭제 가능해져 DB 측과 어긋남 | |
| 쓰기를 owner로 좁힘 | INSERT도 owner만. 가장 보수적이지만 editor가 소스를 못 넣어 Phase 3 수집이 막힐 수 있음 | |

**User's choice:** 기존 베이스라인 대칭

### Storage에 UPDATE 정책을 만듭니까?

| Option | Description | Selected |
|--------|-------------|----------|
| 만들지 않는다 | `raw_sources`가 UPDATE 정책 부재로 불변인 것과 대칭. "불변 원본 보존" 약속이 정책 부재로 강제됨 | ✓ |
| editor에게 허용 | 재업로드로 덮어쓰기 가능. 편하지만 `content_hash` 멱등성과 어긋나고 원본 추적성이 깨짐 | |

**User's choice:** 만들지 않는다

### 버킷 생성과 제약을 어떻게 둡니까?

| Option | Description | Selected |
|--------|-------------|----------|
| 멱등 insert + 크기 상한만 | `on conflict (id) do nothing`, `public=false`, 50MiB. MIME 검증은 Phase 3 애플리케이션에 | ✓ |
| 멱등 insert + MIME allowlist까지 | `allowed_mime_types`를 버킷에 명시. 방어가 DB로 내려가지만 타입 추가마다 새 마이그레이션 필요 | |
| 단순 insert | `on conflict` 없이. `supabase db reset` 반복 환경에서 깨질 수 있음 | |

**User's choice:** 멱등 insert + 크기 상한만

**후속 질문:** "`0005` 영역을 더 파야 할까요?" → **충분하다**

---

## 마무리

"아직 불투명한 영역이 있을까요?" → **컨텍스트 쓸 준비 됐다**
(제시된 대안: "`/health/ready` DB 경로 한 영역 더" / "다른 영역도 더")

---

## Claude's Discretion

사용자가 명시적으로 위임한 영역 — CONTEXT.md의 D-09 ~ D-14에 결정값과 근거를 기록했다.

- monorepo 레이아웃과 Next.js 앱 위치 (`apps/dashboard`, `src/` 레이아웃, pnpm workspace 미도입)
- `/health/ready`의 DB 접근 경로 (httpx → Supabase REST, 2초 타임아웃, 얇은 어댑터 뒤에 배치) — **researcher 검증 요청 표시함**
- Railway 설정 방식과 환경변수 스코프 (`railway.json` 커밋, 시크릿은 서비스별 스코프, `RAILWAY_GIT_COMMIT_SHA` 사용)
- structlog 프로세서 체인과 redaction (`merge_contextvars`, 환경별 렌더러, 키 denylist)
- RTT 측정 도구와 문서 위치 (worker 기동 시 1회 측정 → `docs/ops/rtt-baseline.md`)
- `.dockerignore` 범위 · 레이어 캐싱 순서 · 비루트 유저
- `0005`의 정책 이름 규칙 · 헬퍼 시그니처 세부 · 버킷 id/name 값

## Deferred Ideas

- **GitHub Actions CI** — SEC-03이 Phase 2 요구사항이므로 CI 파이프라인은 그때. Phase 1에서 만들면 Phase 2가 다시 손댐
- **`LLM_MODEL` 기본값 불일치** — `.env.sample`(`anthropic/claude-3.5-sonnet`) vs PROJECT.md(`claude-sonnet-4-6`). OpenRouter 실제 슬러그도 미검증. Phase 3(COMP-01) 이전 정리
- **`jobs` 하트비트 컬럼 유무 확인** — Phase 2 블로커. Phase 1 worker는 루프가 없어 지금은 무관
- **`CLAUDE.md`·`checklists.json`의 `apps/fastapi-backend` 경로 표기** — SPEC의 `apps/api`+`apps/worker`와 불일치. 이 페이즈에서 갱신 대상으로 CONTEXT.md에 기록
