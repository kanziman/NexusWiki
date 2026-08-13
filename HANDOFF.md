# 🤝 Handoff Document

- **작성 일시**: 2026-08-13 09:35 KST
- **작업 브랜치**: `main`

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: `/gsd-execute-phase 6` — Phase 6(Dashboard) 8개 플랜 전체 실행, 코드 리뷰·회귀·페이즈 검증·보안·UI 감사 게이트 통과, `/gsd-verify-work 6`로 UAT 마무리.
- **진행률**: **코드·품질 게이트는 100% 완료.** 페이즈 완료 체크박스(ROADMAP.md `[ ]`)만 미완 — UAT 5개 중 2개(라이브 LLM 필요)가 사용자 선택으로 `skipped` 상태라 자동 전환 게이트(`gsd_run phase uat-passed`)가 막혀 있다. 나머지는 전부 그린.

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

- **8개 플랜 전부 실행**: 06-01(트레이서: middleware.ts 유일 쿠키 기록자·로그인·RLS 워크스페이스 셸·디자인 토큰), 06-02(스위처+내비), 06-03(멤버 로스터+이메일 초대, 마이그레이션 `0014` 신규 RPC 2종), 06-04(api-client/sse), 06-05(드롭존+잡 스테퍼), 06-06(Ask UI 이중 인용), 06-07(위키 뷰어), 06-08(그래프 캔버스). 06-08은 의존성 DAG상 06-02/03/04와 함께 Wave 2로 재배치됨(선언된 Wave 3는 planner 오류).
- **06-03 체크포인트 결정**: 이메일 초대가 `auth.users`를 해석할 방법이 전무해(PostgREST 미노출) planner가 제시한 3안 중 "마이그레이션 0014 신규(`add_owner_as_member()` 관례 재사용)"를 사용자 사전 승인으로 채택. 로컬 `db reset` 검증 완료, 클라우드 미푸시.
- **코드 리뷰 → 6건 전부 수정**: CR-01(레드링크 CTA prefillTitle이 소스 페이지에 안 이어짐), WR-01~05(그래프 캡 off-by-one, Ask SSE 에러 미분기, RLS 차단 삭제를 성공으로 오판, JobStepper 폴링이 안 멈춤, `NEXT_PUBLIC_*` non-null assertion).
- **라이브 UAT 중 신규 버그 2건 추가 발견·수정**(정적 검사로는 못 잡음):
  1. `lib/env.ts`가 `process.env[name]` 동적 인덱싱을 써서 웹팩이 클라이언트 번들에 인라인 못 함 → **로그인 자체가 깨짐**. WR-05 수정의 회귀. `switch` 기반으로 재작성(모듈 스코프 캐싱은 vitest mock 14건을 깼다가 되돌림).
  2. `GraphCanvas.tsx`가 엣지 쿼리에 `from_wiki_id IN (...)`로 최대 1000개 UUID를 URL에 나열 → 1000노드 근처에서 요청 자체가 실패(브라우저엔 CORS 오류로 보임, 실제 원인은 URL 길이). `workspace_id` 스코프만 남기고 기존 클라이언트 필터에 위임.
- **UI 감사에서 타이포그래피 BLOCKER 발견·수정**: UI-SPEC이 checker 리비전으로 확정한 "정확히 2웨이트(400/600)" 계약이 코드에 반영 안 됨 — `--font-caption`/`--font-button-md/sm` 토큰이 500이라 48개 호출부가 500으로 렌더링. 토큰 파일 자체는 안 건드리고(HANDOFF 기존 결정 유지) 48개 호출부에 `fontWeight: 600` 오버라이드 추가, 라이브로 재확인.
- **D-10 접수 오버라이드**: Ask 인용 사이드패널의 "위키 카드+원문 카드 나란히 표시"는 resolved-citation 데이터가 marker당 wiki XOR source만 갖고(페어링 메타데이터 없음) 불가능함을 확인 — Phase 5 API 계약 변경 없이는 불가(Phase 6 스코프 밖). 사용자 승인으로 "마커별 단일 카드, 인접 마커 클릭으로 양쪽 확인" 해석을 채택·문서화.
- **COVERAGE.md 파서 버그 수정**: `api-coverage.verify-pre` 게이트가 이스케이프 파이프(`text\|file\|url`)와 200자 초과 reason 2건 때문에 실패 → 3건 수정.
- **[핸드오프 이후 추가] `apps/api`에 CORS 미들웨어 자체가 없었다**: 사용자가 실제로 `apps/api`+`worker`를 로컬 스택 대상으로 띄우고 대시보드에서 소스 등록을 시도하자 전부 "소스 등록에 실패했습니다"로 실패. 원인 확인: `OPTIONS` 프리플라이트가 405, `main.py`에 `CORSMiddleware` 등록 자체가 없음 — Phase 6 대시보드가 `apps/api`의 **첫 브라우저 호출자**라 지금까지 아무도 이 경로를 안 탔다. `ApiSettings.CORS_ALLOWED_ORIGINS`(콤마 구분 문자열, 로컬 기본값 `http://localhost:3000,http://127.0.0.1:3000`) 신설 + `main.py`에 `CORSMiddleware` 등록(`allow_credentials=True`, origin 명시 — JWT Authorization 헤더 때문에 `allow_origins=["*"]` 불가) + `test_settings.py`의 필드 허용목록 갱신. 커밋 `250f4e8`. `uv run pytest packages/core/tests/test_settings.py apps/api/tests` 158/158 통과 확인. **배포 시 실제 프론트엔드 도메인으로 `CORS_ALLOWED_ORIGINS` 덮어써야 함(Railway env var) — 현재 기본값은 로컬 전용.**

## 🧪 3. 검증 상태

- **완료된 검증**:
  - 코드 리뷰(`06-REVIEW.md`/`06-REVIEW-FIX.md`): 6/6 수정, `tsc`/vitest(77/77) 클린
  - 회귀 게이트: 백엔드 `uv run pytest` 408/408, 대시보드 vitest 77/77
  - 페이즈 목표 검증(`06-VERIFICATION.md`): 5/5 성공 기준 충족(1건은 D-10 오버라이드), status: **passed**
  - 보안 감사(`06-SECURITY.md`): STRIDE 위협 25/25 closed, threats_open: 0, status: **verified**
  - UI 감사(`06-UI-REVIEW.md`): 16/24 → 타이포그래피 BLOCKER 수정 후 라이브 재확인(로그인 화면 `getComputedStyle` weight:600 확인)
  - UAT(`06-UAT.md`): 3/5 라이브 통과(위키 뷰어 6페이지, 그래프 1000행 캡, RLS 차단 삭제 — 전부 실제 시드 데이터+Playwright로 검증, 시드 데이터는 정리 완료 0행 확인), status: **complete**
- **미검증 항목**:
  - UAT 테스트 1(전체 인제스트 흐름)·2(Ask 이중 인용 흐름) — `apps/api`+`worker`가 실 `OPENROUTER_API_KEY`로 떠 있어야 하는데, 이번 세션은 `.env` 읽기가 권한 설정으로 차단되어 있었음(Bash·Read 둘 다 디렉토리 단위 거부). 사용자가 "일단 스킵하고 넘어가자"로 명시적 보류.
  - `WINDOWS.md` #13(App Router에 `error.tsx`/`not-found.tsx` 전무), #14(`GraphCanvas.tsx` hex 리터럴 8개, CSS 커스텀 프로퍼티 미사용) — UI 감사에서 발견했으나 사용자가 "타이포그래피만 지금 고치자"로 범위를 좁혀 후속 과제로 남김.
  - `WINDOWS.md` #12(이전 세션부터 남은 항목, 06-07 관련)는 이번 세션 UAT 테스트 3에서 실제로 라이브 검증되어 **사실상 해소**되었으나 WINDOWS 항목 자체는 아직 `status: open`으로 미정리 — 다음 세션에서 `gsd-tools windows fixed 12` 처리 권장.
  - **[미수정 — 다음 세션 과제, 사용자가 지금은 고치지 말라고 명시] worker의 파싱 단계 실패**: CORS 수정 후 사용자가 실제로 소스 등록까지 진행했으나, worker가 파싱 단계에서 예외로 죽었다. 트레이스백 핵심: `handlers/parse.py:184`의 `run_parse` → `db.index_source_chunk_lexical`(어휘 색인 RPC 호출, `db/service.py:279`) → `db/service.py:755`의 `_rpc()`가 `response.json()`을 호출하는 지점에서 `json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)` — 즉 RPC 응답 바디가 비어 있거나 JSON이 아님. 원인은 조사하지 않았다(사용자가 지금은 고치지 말고 기록만 하라고 명시적으로 요청, 2026-08-13). 전체 트레이스백은 이 대화 세션 로그에 있음 — 다음 세션에서 `worker/db/service.py`의 `_rpc()`가 호출하는 실제 PostgREST RPC 엔드포인트(어휘 색인 관련, 아마 `index_source_chunk_lexical` 또는 그에 대응하는 SQL 함수)가 로컬 스택에서 실제로 무엇을 응답하는지부터 확인할 것 — 빈 응답 자체가 이례적이라 RPC 함수 존재 여부, 권한(GRANT), 또는 API 응답 상태 코드(200인데 바디가 비었는지, 아니면 에러 상태인데 `_rpc()`가 상태 코드를 안 보고 바로 `.json()`을 호출하는지)부터 볼 것.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

- [ ] **worker 파싱 단계 `JSONDecodeError` 진단·수정** (신규, 최우선) — 위 "미검증 항목"의 상세 트레이스백 참조. UAT 테스트 1(인제스트 흐름)이 이 버그 때문에 끝까지 못 감. CORS 수정(커밋 `250f4e8`)으로 소스 등록 API 호출 자체는 성공했지만 그다음 worker 파싱 단계에서 막힘.
- [ ] **UAT 1·2번 라이브 테스트** — 위 파싱 버그부터 고친 뒤, `apps/api`+`worker`를 로컬 스택 대상으로 띄우고(명령어는 이번 대화 마지막 부분에 기록됨: `SUPABASE_URL=http://127.0.0.1:54421` 등으로 override, `.env`의 `OPENROUTER_API_KEY`/`LLM_MODEL`만 사용) 드롭존 인제스트 흐름과 Ask 이중 인용 흐름을 클릭스루. 통과하면 `/gsd-verify-work 6` 재실행 → 자동으로 Phase 6 완료 전환됨.
- [ ] `WINDOWS.md` #12를 `gsd-tools windows fixed 12`로 정리(이번 세션 UAT 테스트 3이 사실상 재현·통과시킴).
- [ ] (선택) `WINDOWS.md` #13(error/not-found 바운더리), #14(GraphCanvas hex 리터럴) — 사용자가 명시적으로 후순위로 미룸. 급하지 않으면 Phase 7에서.
- **주의사항**:
  - **`.env` 읽기가 이 세션 권한 설정에서 완전히 차단됨**(Bash `cat`/`grep`도, Read 툴도) — 디렉토리 단위 deny 규칙으로 보임. 다음 세션도 같은 제약일 수 있으니, 라이브 LLM 테스트가 필요하면 사용자가 직접 서비스를 띄우거나 권한 설정을 사전에 조정해둘 것.
  - **`docs/design-systems/design-tokens.css`는 건드리지 않는다** — Phase 6은 이 토큰 파일의 "사용 계약"만 400/600으로 제한하는 것이지, 파일 자체의 원래 웨이트 값(예: `--font-caption: 500...`)은 그대로 둔다. 이번 세션의 타이포그래피 수정도 컴포넌트별 `fontWeight: 600` 오버라이드로 처리했지 토큰 파일은 안 고쳤다.
  - **`use_worktrees: false`**라 모든 executor는 메인 워킹트리에서 순차 실행됐다 — 병렬 실행 관련 트러블은 없음.
  - 이번 세션 중 두 executor가 세션 한도(session limit)로 중단됐다가 재개됨(06-01, 06-07) — 둘 다 커밋된 작업 유실 없이 정상 재개됨. 재개 패턴은 `SendMessage`로 agentId를 지정해 이어감.
  - 보존할 사용자 변경(기존과 동일): `.planning/config.json`, `checklists.json`은 여전히 세션 시작 전부터 있던 미커밋 상태 — 삭제·revert·무단 커밋하지 않을 것.

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:

> "HANDOFF.md 확인하고, worker 파싱 단계 JSONDecodeError부터 진단해줘. 고친 뒤 apps/api+worker를 로컬 스택으로 띄우고 UAT 1·2번(인제스트/Ask 흐름) 라이브 테스트 이어서 진행해줘. 통과하면 /gsd-verify-work 6으로 Phase 6 완료 전환해줘."
