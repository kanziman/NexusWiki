# NexusWiki

NexusWiki는 원시 소스를 LLM이 상호 링크된 위키로 컴파일하고, 5채널 하이브리드 검색으로 원문과 위키 양쪽을 인용한 답변을 돌려주는 팀 단위 SaaS입니다. 테넌트 격리는 애플리케이션이 아니라 Postgres RLS가 강제합니다.

## 저장소 구조

- `apps/api` — FastAPI HTTP API와 health/readiness 엔드포인트
- `apps/worker` — 상주 작업 프로세스와 배포 환경 RTT 측정
- `packages/core` — API와 worker가 공유하는 Python 로깅 모듈
- `apps/dashboard` — Next.js 15 dashboard; uv 워크스페이스 멤버가 아닌 독립 pnpm 앱
- `supabase/migrations` — Postgres 스키마, RLS, Storage 정책의 유일한 마이그레이션 원장

## 로컬 개발

```bash
uv sync --frozen
supabase start
bash scripts/smoke_tracer.sh
uv run pytest -q
pnpm --dir apps/dashboard exec vitest run
pre-commit install
```

로컬 Supabase는 같은 머신의 다른 프로젝트가 543xx를 점유하므로 544xx 포트를 사용하며 DB 포트는 `54422`입니다. 호스트에 `psql`이 없으므로 다음 명령으로 접속합니다.

```bash
docker exec -it supabase_db_NexusWiki psql -U postgres -d postgres
```

환경 설정은 `.env.sample`을 기준으로 하며 시크릿이나 접속 문자열을 문서에 기록하지 않습니다.

## 배포

Railway 프로젝트 하나에 `api`와 `worker` 두 서비스를 두고, 둘 다 변경할 수 없는 `asia-southeast1` 리전과 Root Directory `/`를 사용합니다. `api`는 이미지 기본 Start Command `python -m api`, `worker`는 Custom Start Command `python -m worker`로 같은 루트 `Dockerfile`을 실행합니다. 서비스별 config-as-code 경로 설정이 공식 레퍼런스에 없어 이 값은 Railway dashboard에 있으며, 이 절이 리뷰 가능한 설정 기록입니다.

Supabase는 생성 후 변경할 수 없는 `ap-southeast-1` 리전을 사용합니다. Railway와 Supabase 두 리전 모두 생성 후 변경할 수 없습니다.

## 규약

주석·커밋 메시지·문서는 한국어로, 식별자·파일명은 영문으로 씁니다. 커밋 메시지 형식과 인수 조건의 정본은 [`docs/reference/commit.md`](docs/reference/commit.md)입니다.
