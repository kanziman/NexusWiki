# Design — retrieval-debug-viewer

## Context

동기는 `proposal.md`의 "Why"를 본다. 여기서는 접근을 설명하는 데 필요한 현재 상태만 적는다.

- 백엔드 `POST /workspaces/{id}/retrieval`(`apps/api/src/api/routers/retrieval.py`)은 이미 완성돼 있고 변경하지 않는다. 응답은 `evidence: [{id, kind, document_id, channels, contributions: dict[str, float], metadata}]` + `meta: {policy_version, elapsed_ms, <channel>: {status, returned, elapsed_ms, contribution}}`이다. 채널 키는 정확히 `wiki_vector` · `source_vector` · `wiki_lexical` · `source_lexical` 4종이다(`apps/api/src/api/services/retrieval.py`).
- 이 라우터는 `_user_db(request, credentials)`로 요청자 JWT만 쓴다 — `service_role` 아님. RLS가 이미 테넌트 경계를 강제하므로 화면을 새로 만든다고 노출 범위가 늘지 않는다.
- `apps/dashboard/lib/api-client.ts`의 `apiFetch<T>`가 세션 토큰 부착·에러 파싱을 이미 처리한다. 이 엔드포인트는 SSE가 아니라 평범한 JSON이라 `AskConversation.tsx`처럼 별도 파서를 쓸 필요가 없다.
- `apps/dashboard/app/preview/layout.tsx`가 `process.env.NODE_ENV !== "development"`일 때 `notFound()`를 던지는 패턴을 이미 갖고 있다. `local-product-preview`의 design.md가 이 게이트를 "middleware matcher와 독립적으로 전체 하위 경로를 막아야 한다"고 판단해 놓았고, 같은 판단을 여기서도 그대로 따른다.

## Goals / Non-Goals

범위는 `proposal.md`의 "What Changes"가 정의한다. 설계 수준의 경계만 덧붙인다.

**Goals**
- 백엔드·미들웨어·기존 라우트를 전혀 건드리지 않고 새 페이지 하나만 추가한다.
- `/preview`의 환경 게이트 패턴을 재사용하되 그 트리 자체는 건드리지 않는다.

**Non-Goals**
- 배포 환경에서의 접근 제어(역할 기반 등)는 다루지 않는다 — `proposal.md`가 이미 범위 밖으로 명시했다.
- RRF 정책 파라미터(k=60 등)를 화면에서 조정하는 기능은 다루지 않는다. 이번 화면은 관찰 전용이다.

## Decisions

### 1. `/preview`가 아니라 `/w/[workspaceId]/debug/retrieval/`에 둔다

**대안과 기각 사유**
- *`/preview/retrieval`에 추가*: `local-product-preview` 스펙의 "MUST NOT query a live workspace"와 정면으로 충돌한다. `/preview`는 인증·DB·API 없이 안전하게 보여주는 목업 전용 트리라는 게 존재 이유이고, 그 계약을 한 화면이라도 깨면 "이 화면이 진짜 데이터인지 목업인지"를 프리뷰 트리 전체에서 다시 따져야 한다.
- *완전히 새 최상위 라우트(`/debug/retrieval`)*: 워크스페이스 컨텍스트(`workspaceId`) 없이는 어느 워크스페이스를 조회할지 알 수 없어 결국 같은 파라미터를 다시 받아야 한다. `/w/[workspaceId]/` 트리 밑에 두면 미들웨어의 기존 로그인 요구와 워크스페이스 컨텍스트를 그대로 상속받는다.

**채택**: `/w/[workspaceId]/debug/retrieval/`. 미들웨어 matcher(`/w/:path*`)에 이미 포함되므로 로그인 안 한 사용자는 정상적으로 `/login`으로 리다이렉트된다.

### 2. 환경 게이트는 `/preview/layout.tsx`와 같은 코드를 별도로 복제한다

같은 유틸 함수로 추출하지 않고 **각 라우트의 `layout.tsx`에 각자 직접 둔다**.

**대안**: `lib/dev-only-gate.ts` 같은 공유 헬퍼로 추출 → 기각. 게이트 로직이 세 줄짜리 `if` 하나뿐이라 추출해도 줄어드는 코드가 없고, 두 라우트가 이 함수 하나를 공유한다는 사실 자체가 "둘이 같은 성격의 라우트"라는 암묵적 결합을 만든다 — 실제로는 하나는 목업 전용(`/preview`), 하나는 실제 데이터 조회(`/w/.../debug`)로 성격이 다르다. 이 change의 Decision 1이 정확히 그 둘을 분리하려는 결정이었으므로, 헬퍼 공유로 다시 묶는 것은 그 결정과 어긋난다.

### 3. RRF 총점은 프론트에서 `contributions` 값을 합산해 파생한다

응답에 `rrf_score` 같은 사전 계산된 합산 필드가 없다(design Context 참고). 화면은 `Object.values(evidence.contributions).reduce((a, b) => a + b, 0)`로 합산해 "융합 랭킹" 정렬·표시 키로 쓴다.

**대안**: 백엔드에 합산 필드를 추가해 달라고 요청 → 기각. 이 change는 "백엔드 변경 없음"이 전제이고(proposal.md Impact), 합산은 순수 함수라 프론트에서 하는 것과 정확도 차이가 없다.

### 4. 채널 실패·0건은 감추지 않고 상태를 그대로 보여준다

델타 스펙의 "A channel returns no results or fails" 시나리오가 요구하는 대로, `meta.<channel>.status !== "ok"`이거나 `returned === 0`이면 그 채널 칸에 원인을 그대로 표시한다(카드를 통째로 숨기지 않는다). 디버그 화면의 존재 이유가 "왜 이 채널이 기여하지 않았는가"를 보여주는 것이므로, 조용히 생략하면 화면의 목적 자체가 무너진다.

### 5. 원시 결과 항목에 실제 청크·페이지 내용을 지연 조회로 보여준다

id·metadata만으로는 채널별 랭킹을 실제로 비교하기 어렵다는 구현 중 피드백에 따라, 각 원시 결과 항목에 "내용 보기" 토글을 추가한다. 클릭 시에만 Supabase 클라이언트로 조회한다(`CitationSidePanel.tsx`와 동일한 `createClient()` user-JWT 패턴, RLS 그대로 적용). 조회 대상 테이블은 evidence의 kind·channels로 결정한다 — `apps/api/src/api/services/retrieval.py`의 `_wiki_vector_hit`(evidence.id = `wiki_embeddings.id`, 청크 단위) · `_wiki_lexical_hit`(evidence.id = `wiki_pages.id`, 페이지 단위, embedding_chunk_id 없음) · `_source_hit`(evidence.id = `source_chunks.id`, 벡터·어휘 공통)와 정확히 일치시킨다.

**대안**: 검색 응답 자체에 내용을 포함해 달라고 백엔드를 바꾼다 → 기각. `RetrievalResponse`는 "evidence plus safe retrieval observability only"로 의도적으로 얇게 유지되고 있고(retrieval.py 주석), 이 change의 "백엔드 변경 없음" 전제와도 맞지 않는다. 이미 존재하는 테이블을 프론트에서 직접 조회하는 쪽이 기존 인용 패널과 같은 패턴이라 일관적이다.

**Non-goal 갱신**: 처음 계획 시점에는 id·metadata 표시로 충분하다고 판단했으나, 실사용 검증(4.2) 중 실제 비교에는 내용이 필요하다는 게 드러나 범위에 포함했다. RRF 융합 랭킹 표(3.3)에는 포함하지 않는다 — "채널별 원시 결과" 비교가 목적이라는 요청 범위를 그대로 따른다.

## Risks / Trade-offs

- **배포 번들에 코드가 포함된다** → `layout.tsx`의 환경 게이트가 요청 자체를 막는다(Context 참고). 번들 크기에는 영향이 있지만(무시할 수준 — 페이지 1개), 실행 경로는 프로덕션에서 절대 열리지 않는다.
- **로컬 개발 서버에서는 워크스페이스 멤버라면 누구나 볼 수 있다** — 별도 역할 게이트가 없다. 다만 이미 그 멤버는 같은 API를 직접 호출해 같은 데이터를 볼 수 있으므로(요청자 JWT만 쓰는 엔드포인트), 새로운 노출이 아니라 기존에 API로 가능하던 걸 화면으로 옮기는 것뿐이다.
- **`contributions` 딕셔너리의 채널 키가 백엔드에서 바뀌면 화면이 조용히 깨질 수 있다** → 4개 채널 키를 상수로 고정하고, 응답에 없는 키가 오면(정책 변경 등) "알 수 없는 채널"로 표시하는 방어적 렌더링을 태스크에 포함한다(구현 시 결정).

## Migration Plan

마이그레이션 없음. 백엔드·스키마·RLS 변경이 없고, 새 페이지 하나 추가·삭제는 되돌리기가 파일 삭제 수준으로 간단하다.

## Open Questions

없음. 위치·게이트 방식·총점 파생 방식 모두 사용자와 확정했다(대화 맥락, proposal.md 참고).
