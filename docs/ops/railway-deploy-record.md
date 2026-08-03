# Railway 배포 기록

- 측정 일시: 2026-08-03
- 방법: Railway CLI 로그인 세션과 공개 헬스 엔드포인트로 구성·배포 상태 확인
- 결과: NexusWiki 프로젝트의 `api`·`worker` 서비스를 싱가포르 리전에 구성

## 서비스 구성

| 항목 | api | worker |
| --- | --- | --- |
| 프로젝트 | NexusWiki | NexusWiki |
| 리전 | `asia-southeast1` | `asia-southeast1` |
| Root Directory | `/` | `/` |
| 이미지 | 루트 `Dockerfile` | 루트 `Dockerfile` |
| Start Command | 이미지 기본값 `python -m api` | Custom Start Command `python -m worker` |
| Health Check | `/health`, timeout 60초 | 없음 |
| Restart Policy | `ON_FAILURE`, 최대 5회 | `ALWAYS` |
| 공개 도메인 | 있음 | 없음 |

`railway.json`은 두 서비스가 공유하므로 빌드 설정만 담는다. 서비스별 Start Command와 Health Check는
Railway 서비스 설정에 둔다. 두 서비스 모두 저장소 루트를 빌드 컨텍스트로 사용해야 루트 `uv.lock`과
`packages/core`를 함께 볼 수 있다.

## 환경변수 스코프

- `api`: `ENVIRONMENT`, `LOG_LEVEL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`
- `worker`: `ENVIRONMENT`, `LOG_LEVEL`, `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, `SUPABASE_SECRET_KEY`

공유 변수 그룹은 사용하지 않는다. 두 서비스가 같은 이미지를 실행하므로 service key를 공유 스코프에
두면 `api`도 BYPASSRLS 자격을 얻게 된다. `SUPABASE_SECRET_KEY`는 오직 `worker` 서비스에만 설정했다.
`PORT`와 `RAILWAY_GIT_COMMIT_SHA`는 Railway 내장 변수를 사용한다.

## 기계 판독 키

api_public_domain: api-production-44b4.up.railway.app
