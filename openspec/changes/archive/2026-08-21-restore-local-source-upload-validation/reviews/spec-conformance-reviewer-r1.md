# Spec Conformance Review R1

## 검토 범위

- OpenSpec 산출물: `proposal.md`, `design.md`, `tasks.md`
- 구현 diff: 로컬 환경 예시·README, API/worker fixture, 검색 벤치마크 fixture·UTF-8 처리
- 범위 제외: 기존 사용자 변경인 `docs/ref/ref0.png`, `docs/ref/ref2.png` 삭제

## 계획 대비 구현

| 계획 AC | 구현 및 확인 결과 | 판정 |
| --- | --- | --- |
| 대시보드가 `NEXT_PUBLIC_API_URL`을 사용하고 Supabase 54421과 FastAPI 8000을 분리한다 | `.env.sample`의 이전 키를 현재 소비 키로 교체했고, `apps/dashboard/.env.example`의 API 주소를 `127.0.0.1:8000`으로 수정했다. README는 루트 서버 환경과 `apps/dashboard/.env.local`을 분리해 준비하도록 안내한다. `apps/dashboard/lib/env.ts` 및 API client의 실제 소비 계약과 일치한다. | 일치 |
| 프런트 환경변수·API client·Dropzone 회귀가 통과한다 | apply 단계의 전체 Dashboard 242건 통과 증거가 있으며, 리뷰 재실행에서도 관련 2개 파일 21건, typecheck, ESLint가 통과했다. | 충족 |
| 최신 `workspaces.slug` 제약을 모든 직접 INSERT 경로가 만족한다 | API fixture는 기존 고유 `test-<hex>`, worker fixture는 `queue-it-<hex>`, 벤치마크는 결정적 UUID 기반 `benchmark-<uuid>`를 slug로 제공한다. 모두 migration 0015의 소문자·숫자·하이픈, 길이 1~80, unique 계약을 만족한다. | 충족 |
| worker fixture가 현재 설정 계약을 만족한다 | `PipelineHarness`의 `WorkerSettings`에 필수 publishable key를 추가해 `BaseAppSettings` 상속 계약과 일치시켰다. 운영 설정이나 권한 경계 변경은 없다. | 충족 |
| Windows에서도 벤치마크 JSON을 안정적으로 처리한다 | 관련 loader, benchmark 결과, golden 테스트 임시 파일의 `read_text`/`write_text`에 UTF-8을 명시했다. 한국어 corpus를 플랫폼 기본 인코딩에 의존하지 않게 한다는 design 결정과 일치한다. | 충족 |
| 실제 업로드가 202, 원문 행, parse queued 잡을 만든다 | apply 단계에서 로컬 Supabase 기반 Markdown 업로드가 HTTP 202를 반환하고 `raw_sources` 및 `jobs(type=parse, status=queued)` 생성을 확인한 증거가 있다. 업로드 API·RLS·Storage·잡 구현 자체는 변경하지 않았다. | 충족 |

## 누락 및 범위 이탈

- 계획된 파일과 실제 diff가 대응하며 사용자 동작, API 응답, DB schema를 변경한 범위 이탈은 없다.
- `apps/api/tests/fixtures/pipeline.py`의 worker 설정 보완과 벤치마크 UTF-8 변경은 proposal의 테스트 준비 데이터·운영체제 독립 처리 범위에 포함된다.
- delta spec이 없는 유지보수 change라는 proposal의 분류와 실제 변경이 일치한다.
- 차단 또는 수정이 필요한 누락을 발견하지 못했다.

## 검증 증거

- apply 단계: Python 454건 통과, Dashboard 242건 통과, Ruff·typecheck·ESLint 통과, 실제 Markdown 업로드 HTTP 202 및 원문/parse 잡 생성 확인.
- 리뷰 재실행: 관련 Python 테스트 `77 passed, 35 skipped`. skip은 리뷰 시점에 로컬 Supabase 스택이 종료된 상태여서 발생했으며, 해당 통합 경로는 위 apply 단계 증거로 보완된다.
- 리뷰 재실행: Dashboard 관련 테스트 `21 passed`, typecheck 통과, ESLint 통과.
- 리뷰 재실행: 저장소 표준 범위 `uv run ruff check apps packages` 통과.
- 리뷰 재실행: `openspec.cmd validate --specs --strict` 결과 `32 passed, 0 failed`.
- 리뷰 재실행: 범위 밖 이미지 삭제를 제외한 `git diff --check` 통과.

## 최종 판정

**pass**

계획 AC와 구현이 일치하고, 필요한 회귀 및 실제 업로드 증거가 있으며, PR 전에 수정해야 할 spec 불일치나 범위 이탈은 없다.
