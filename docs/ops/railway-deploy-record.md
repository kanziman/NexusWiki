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

## 동일 빌드 및 배포 검증

- 판정 차수: 2차. 두 서비스의 비결정적 개별 빌드로 이미지 다이제스트가 달라 런타임 3항 일치를 적용했다.
- api 이미지 다이제스트: `sha256:09eed3d47daffbe01402b7314cb11a7c3089f3502dcfa979d8fa82699d30ffb6`
- worker 이미지 다이제스트: `sha256:bddd486be597b43985a3e75fa95162fd7cad2bb06431ea9804be618a5c5b2112`
- 배포 커밋 SHA: 두 서비스 모두 `5ca73afb4d48f83b202ec80f2bb78f01ae9c73bc`
- Dockerfile 경로: 두 서비스 모두 `Dockerfile` (`DOCKERFILE` builder)
- 런타임 `GIT_SHA`: api `/health`와 worker `worker.started` 모두
  `5ca73afb4d48f83b202ec80f2bb78f01ae9c73bc`
- api deployment id: `9950852a-4d5d-4e36-aac0-85edc286290f`
- worker deployment id: `a1164100-ba01-4733-b7ba-06121a898cc8`
- 배포 상태: 두 deployment 모두 `SUCCESS`, `asia-southeast1`
- api `/health`: HTTP 200
- api `/health/ready`: HTTP 503 관측. 클라우드 마이그레이션 push 전 상태이므로 이 계획의 합격 조건에서 제외한다.
- 권한 경계 재확인: api 변수 이름 목록에 `SUPABASE_SECRET_KEY`가 없고 worker에만 존재한다.

모든 로그와 헬스 응답은 위 deployment id의 배포에서 읽었다. 이전 배포의 관측값은 판정에 사용하지 않았다.
