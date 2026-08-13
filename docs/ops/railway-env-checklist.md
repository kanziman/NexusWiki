# Railway 환경변수 체크리스트

- 작성 배경: 2026-08-13, v1.0 첫 프로덕션 배포 직후 실사용 테스트에서 **네 가지 별개의
  누락된 Railway 환경변수**를 순서대로 발견·수정했다(CORS → LLM_MODEL → EMBED_BATCH_SIZE →
  내부 리스너 토큰). 서비스 초기 배포(`docs/ops/railway-deploy-record.md`, 2026-08-03)
  때는 `/health`만 확인했고 실제 기능 왕복(소스 등록 → 컴파일 → 임베딩 → Ask)을 프로덕션에서
  검증한 적이 없어 이 네 가지가 전부 숨어 있었다. 앞으로 서비스를 재생성하거나 새 환경을
  만들 때 이 문서 하나로 전부 확인할 것 — 개별 발견 기록에서 종합 체크리스트로 승격.

## `api` 서비스

| 변수 | 예시 값 | 비고 |
| --- | --- | --- |
| `SUPABASE_URL` | `https://dajhhwbkfdaqnuenulsb.supabase.co` | |
| `SUPABASE_PUBLISHABLE_KEY` | `sb_publishable_...` | |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,https://<vercel-domain>` | **기본값이 localhost 전용** — 코드 주석(`settings.py:37-39`)이 배포 시 덮어쓰라고 명시하는데도 실제 첫 배포에서 누락됐다. 미설정 시 모든 쓰기 요청이 프리플라이트 405/CORS 실패로 "소스 등록에 실패했습니다"만 남긴다. |
| `QUERY_EMBEDDING_INTERNAL_URL` | `http://worker.railway.internal:8081` | worker의 사설 리스너 주소. `<service-name>.railway.internal` 형식. |
| `QUERY_EMBEDDING_INTERNAL_TOKEN` | (32바이트 랜덤 hex) | **worker의 동일 이름 변수와 값이 같아야 한다.** 미설정 시 worker가 리스너 자체를 기동하지 않아(`__main__.py:95-96`) 모든 벡터 검색 채널이 `embedding_unavailable`로 죽는다(어휘 채널은 살아 있어 부분 응답은 나오지만 벡터 채널 전체 무효). |
| `LLM_STREAM_INTERNAL_URL` | `http://worker.railway.internal:8081` | 같은 리스너, 다른 라우트. |
| `LLM_STREAM_INTERNAL_TOKEN` | (32바이트 랜덤 hex) | worker와 값이 같아야 한다. 미설정 시 Ask의 LLM 스트리밍 자체가 안 된다. |

**절대 여기 있으면 안 되는 것**: `SUPABASE_SECRET_KEY`, `OPENROUTER_API_KEY` — 있으면 SEC-01
위반이며 `service_role`이 사용자 요청 경로에 노출된다.

## `worker` 서비스

| 변수 | 예시 값 | 비고 |
| --- | --- | --- |
| `SUPABASE_URL` | api와 동일 | |
| `SUPABASE_PUBLISHABLE_KEY` | api와 동일 | |
| `SUPABASE_SECRET_KEY` | `sb_secret_...` | worker 전용, api에는 절대 없어야 함(SEC-01) |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | worker 전용 |
| `LLM_MODEL` | `anthropic/claude-sonnet-4.6` | **코드 기본값 없음(필수 필드)** — OpenRouter가 구형 모델 슬러그를 제거하면 조용히 404로 죽는다. `curl https://openrouter.ai/api/v1/models`로 주기적으로 유효성 확인할 것. `anthropic/claude-3.5-sonnet`은 2026-08-13 기준 이미 제거됨. |
| `EMBEDDING_MODEL` | `baai/bge-m3` | |
| `EMBEDDING_PROVIDER` | `deepinfra/fp32` | `allow_fallbacks: false`로 고정 — 이 provider가 요청을 못 받으면 폴백 없이 그대로 실패(의도된 설계, `03-CONTEXT.md` D-04/D-05) |
| `EMBED_BATCH_SIZE` | `8` (코드 기본값) | 32였을 때 실측 27~32KB 사이에서 `deepinfra/fp32`가 "No endpoints found"로 404. 한국어 텍스트는 UTF-8에서 문자당 3바이트라 청크 수 기준 상한만으로는 예측 불가 — 바이트 상한 기준으로 재검토 필요 시 `apps/worker/src/worker/settings.py` 주석 참고. |
| `QUERY_EMBEDDING_INTERNAL_TOKEN` | api와 동일 값 | |
| `LLM_STREAM_INTERNAL_TOKEN` | api와 동일 값 | |

## 배포 후 최소 검증 순서

`/health`만으로는 이 네 가지 중 아무것도 드러나지 않는다. 최소한 아래를 실 계정으로 왕복할 것:

1. 소스 등록(파일 업로드) — CORS 확인
2. 컴파일 완료까지 대기 — `LLM_MODEL` 유효성 확인
3. 임베딩 완료까지 대기 — `EMBED_BATCH_SIZE`/provider 확인
4. Ask에 실제 질문 — `QUERY_EMBEDDING_INTERNAL_*`/`LLM_STREAM_INTERNAL_*` 확인, 답변에
   `[[wiki:...]]`/`[[src:...]]` 인용 마커가 실제로 붙는지까지 확인
