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
위반이며 `service_role`이 사용자 요청 경로에 노출된다. `LANGFUSE_SECRET_KEY`도 넣지 않는다. 같은
키로 전 테넌트의 trace를 읽고 지울 수 있어서 worker만 갖는다. api는 턴 보고서를 worker에 넘긴다.

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
| `LANGFUSE_PUBLIC_KEY` | `pk-lf-...` | 선택. 두 키가 모두 있어야 외부 관측이 켜진다. |
| `LANGFUSE_SECRET_KEY` | `sk-lf-...` | 선택. **빈 문자열로 두지 않는다.** 빈 값은 설정 검증에서 거부되어 서비스가 기동하지 못하므로, 쓰지 않으면 변수를 만들지 않는다. |
| `LANGFUSE_BASE_URL` | `https://jp.cloud.langfuse.com` (코드 기본값) | 프로젝트를 만든 리전과 같아야 한다. |

Langfuse를 켰다면 배포 뒤 Langfuse 화면에서 첫 trace 수신을 확인한다. SDK의 전송 실패는 stderr의
평문 한 줄로만 남아, 리전이나 키가 틀려도 `observability.enabled` 로그는 그대로 찍힌다. 키를
회전할 때는 worker 변수를 바꾸고 재배포한 뒤 이전 키를 Langfuse에서 폐기한다.

## main 머지 전 DB 확인

main 머지는 Railway 운영 배포를 바로 시작한다. 계약 정본은 `openspec/specs/pull-request-workflow/spec.md`의 「자동 운영 배포 전 마이그레이션 게이트」다. 마이그레이션이 있는 PR에서는 다음을 운영자가 확인하고 결과를 PR에 남긴다.

1. `supabase migration list --linked`로 원격 원장과 로컬 파일을 대조한다. 최신 번호와 미적용 대상을 실제 응답으로 확인하고, 원장 불일치를 임의의 repair로 덮지 않는다.
2. `supabase db push --linked --dry-run`으로 대상과 순서를 확인하고, 이 변경을 먼저 적용해도 현재 운영 중인 API·워커가 동작하는지 검토한다. 권한·트리거·함수 변경도 확인한다.
3. 호환되는 변경은 승인된 운영 권한으로 `supabase db push --linked`를 실행한다. 이 문서만으로 에이전트에게 운영 DB 쓰기 권한이 생기지는 않는다.
4. 명령 성공 응답과 `supabase migration list --linked`, 재실행한 dry-run으로 필요한 버전의 적용과 해당 PR에 필요한 대기 대상이 없음을 확인한다. 적용 또는 확인이 실패하면 머지하지 않고 운영자 조치를 요청한다.
5. 확인 결과를 PR에 기록한 뒤 main에 머지하고 워커·API·대시보드의 배포 완료와 아래 실제 흐름을 확인한다.

현재 코드와 호환되지 않는 변경은 먼저 호환 단계로 분리하거나, 자동 배포를 통제하는 별도 승인된 전환 계획을 마련한다. 그 계획의 선행 조건이 충족되기 전에는 머지하지 않는다. 마이그레이션이 없는 문서·합성 증거 PR에는 DB 적용이 해당하지 않음을 기록한다.

## 배포 후 최소 검증 순서

`/health`만으로는 이 네 가지 중 아무것도 드러나지 않는다. 최소한 아래를 실 계정으로 왕복할 것:

1. 소스 등록(파일 업로드) — CORS 확인
2. 컴파일 완료까지 대기 — `LLM_MODEL` 유효성 확인
3. 임베딩 완료까지 대기 — `EMBED_BATCH_SIZE`/provider 확인
4. Ask에 실제 질문 — `QUERY_EMBEDDING_INTERNAL_*`/`LLM_STREAM_INTERNAL_*` 확인, 답변에
   `[[wiki:...]]`/`[[src:...]]` 인용 마커가 실제로 붙는지까지 확인
