# Tenant isolation review — R1

## 판정

`pass`

차단 또는 수정 필수 finding은 없다. 이 change는 운영 업로드·Storage·RLS·큐 구현을 변경하지 않고, 로컬 설정 예시와 테스트/벤치마크 준비 데이터만 현재 계약에 맞춘다. 검토 대상 diff에서 요청자 JWT 경로가 service role로 승격되거나 워크스페이스 조건이 제거되는 변화는 발견되지 않았다.

## 검토 결과

- **요청자 JWT와 service role 경계:** API 공유 fixture의 워크스페이스 INSERT는 publishable key와 해당 사용자의 access token을 사용한다. worker 큐 fixture도 사용자 토큰으로 워크스페이스를 만든 뒤에만 service-role `ServiceDb`로 잡을 다룬다. `PipelineHarness`에 추가된 `SUPABASE_PUBLISHABLE_KEY`는 필수 `WorkerSettings` 구성을 완성할 뿐이며, `service_client()`는 계속 `SUPABASE_SECRET_KEY`만 `apikey`와 Bearer에 사용한다.
- **RLS와 403:** 추가된 `slug`는 `owner_id = auth.uid()`를 요구하는 기존 `workspaces_insert_self_owned` 정책 아래 삽입된다. `test_sources_router.py`와 전체 경계 스위트는 교차 테넌트 소스 생성의 고정 403 계약을 유지한다. 이번 diff에는 정책, grant, API 오류 매핑 변경이 없다.
- **테넌트 격리:** API/worker fixture slug는 기존의 실행별 무작위 워크스페이스 이름에서 파생되고, 벤치마크 slug는 해당 벤치마크 전용 결정적 workspace UUID에서 파생된다. 벤치마크 생성·정리 SQL의 모든 자식 행과 삭제 조건은 동일한 `workspace_id`로 제한되어 있다.
- **fixture secret 경계:** 대시보드 예시는 publishable key만 요구하고 service key를 공개 변수로 이동시키지 않는다. 로컬 통합 fixture의 admin/service key는 루프백 전용 가드 안에 머물며, 클라우드 환경변수를 읽지 않는다. 운영 API 설정에 secret 필드가 추가된 변화도 없다.
- **멱등성:** 소스 잡의 기존 dedup/RPC 경로는 불변이다. 벤치마크의 결정적 workspace ID와 slug는 재실행 시 같은 행을 가리키며, `on conflict do nothing` 및 workspace 한정 cleanup의 기존 멱등 동작을 훼손하지 않는다.
- **조용한 실패:** 필수 slug 누락으로 준비 단계가 실패하던 경로를 명시적 slug 제공으로 복구한다. API fixture는 INSERT 실패를 `_expect`로 즉시 드러내고 worker fixture는 `raise_for_status()`로 드러낸다. UTF-8 명시는 Windows에서 검증이 본 테스트 전에 조용히 이탈하는 플랫폼 차이도 제거한다.

## 독립 검증

- `git diff --check -- . ':(exclude)docs/ref/ref0.png' ':(exclude)docs/ref/ref2.png'`: 통과
- `uv run pytest -q apps/api/tests/test_workspaces_isolation.py apps/api/tests/test_tenant_isolation_full_path.py apps/worker/tests/test_queue.py -rs`: `17 passed, 52 skipped`
- skip 52건은 검토 시점에 로컬 Supabase가 중단되어 있었기 때문이며 통과 증거로 계산하지 않았다. 아카이브 task에는 로컬 Supabase에서 소스/큐 왕복과 Markdown 업로드 `202`·원문 행·parse 잡 생성을 확인한 결과가 기록되어 있다.

## 비차단 잔여 위험

- `queue-it-<8 hex>` slug는 병렬·장기 반복에서 극히 낮은 확률의 전역 unique 충돌 가능성이 있다. 충돌은 `raise_for_status()`로 명시적으로 실패하므로 테넌트 혼합이나 조용한 성공으로 이어지지 않으며, 이번 보안 게이트의 차단 사유는 아니다.
