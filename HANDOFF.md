# 🤝 Handoff Document

- **작성 일시**: 2026-08-13 16:10 KST
- **작업 브랜치**: `main`

## 🎯 1. 작업 목표 & 현재 상태

- **목표**: v1.0 Phase 7 통합·운영 기준선을 완성하고, 마지막 브라우저 레이아웃 백스톱까지 실제 환경에서 검증한다.
- **진행률**: **완료.** v1.0은 7개 Phase, 55개 계획, 73/73 요구사항을 완료·검증한 뒤 아카이브됐다. 현재 상태는 `Awaiting next milestone`이며 다음 정상 진입점은 `/gsd-new-milestone`이다.

## ✏️ 2. 주요 변경 사항 & 의사결정 (Why)

- **Phase 7 OPS-02~06 완료**: 빈 워크스페이스의 수집→컴파일→임베딩→검색 E2E, 중복/축소 재처리, 9테이블 요청자-JWT 격리, 25k+25k 합성 HNSW 기준선, Settings 내 비용·잡 파이프라인 관측을 구현·검증했다. 원본 Phase 7 문서는 `.planning/milestones/v1.0-phases/07-integration-and-ops-baseline/`로 아카이브됐다.
- **격리 검증 보강**: 최초 검증에서 OPS-04의 쓰기 매트릭스가 불충분하다는 갭을 발견했다. `a1d1143`가 UPDATE/DELETE, own control, A↔B·비멤버·익명 거부, 지원 INSERT 경계 및 42501 읽기 전용 경계를 명시적인 9테이블 매트릭스로 보강했다. RLS의 0행 거부와 SQLSTATE 42501을 구분하는 기존 규칙을 유지했다.
- **OPS-05 정책 불변**: 50k 로컬 코퍼스에서 strict/relaxed 양쪽이 임베딩 HNSW 인덱스를 선택함을 scoped EXPLAIN으로 기록했다. 비교 결과는 근거로만 남기고 retrieval 정책은 변경하지 않았다.
- **OPS-06 보안 경계**: Operations API는 owner/editor 요청자 JWT만 허용하며, budget·고정 5단계 집계·관측 시각만 반환한다. payload, `last_error`, usage metadata, provider/model 정보는 반환하지 않는다. 대시보드는 Settings 탭에서만, 초기 로드와 수동 새로고침만 사용한다.
- **브라우저 백스톱 완료**: 전역 `agent-browser`를 설치해 실제 로컬 owner 세션으로 확인했다. 360×800에서 새로고침 버튼은 뷰포트 안에 남고 페이지 가로 넘침은 없었으며, 표는 `overflow-x:auto` 내부 스크롤을 사용했다. 고정 서버 라벨 때문에 장문 실데이터는 없으므로 렌더된 행에 장문을 주입해 실제 CSS 자르기와 `title` 접근성을 확인했다 (`scrollWidth 716 > clientWidth 298`, ellipsis/hidden/nowrap).
- **마일스톤 아카이브·배포 후속 기록**: 이후 커밋으로 v1.0 계획/요구사항/Phase 디렉터리가 `.planning/milestones/`로 이동했고, Vercel 대시보드 배포와 DOCX 수집 후보(v1.1)가 문서화됐다. 배포는 저장소 루트에서 `vercel --prod`로 해야 모노레포 토큰 CSS 참조가 유지된다.

## 🧪 3. 검증 상태

- **완료된 검증**:
  - Phase 7 focused API suite: E2E, 재수집, 9테이블 격리, Operations API.
  - `packages/core/tests/test_retrieval_golden.py`: 18 passed.
  - strict/relaxed HNSW comparator: `status: ok`, pinned records와 scoped EXPLAIN 증거 확인.
  - Dashboard: 17 files / 82 tests passed, TypeScript typecheck passed.
  - 실제 브라우저 owner 세션: Operations 탭, 좁은 viewport, 내부 표 스크롤, 장문 라벨 ellipsis/title 확인.
  - 최종 브라우저 검증 기록: `9450bd5 docs(07): record browser layout verification`.
- **미검증 항목**:
  - 전체 Python `pytest -rs`는 435개 수집과 일부 출력까지는 확인됐지만 실행 캡처가 종료 footer를 보존하지 않았다. Phase 7 검증 보고서는 이를 전체-suite 통과로 주장하지 않고 focused 증거로 판정한다.

## ⚠️ 4. 주의사항 & 남은 작업 (TODO)

- [ ] **v1.1 스코프 수립**: `/gsd-new-milestone`으로 시작. 후보는 `.planning/PROJECT.md`의 v2 후보(Navigation, Maintain, Quality & History, Platform)와 최신 커밋의 DOCX 수집 후보다.
- [ ] **배포 운영 확인**: Vercel 재배포는 반드시 저장소 루트에서 `vercel --prod` 실행. `apps/dashboard` 안에서 실행하면 `docs/design-systems/design-tokens.css`가 업로드 범위에서 빠진다.
- [ ] **선택적 운영 점검**: Railway worker의 `EMBEDDING_MODEL=baai/bge-m3`, `EMBEDDING_PROVIDER=deepinfra/fp32` 환경 변수가 실제 배포에 유지되는지 확인한다. 이 값이 없으면 임베딩 잡이 provider에 null model을 보내 dead가 될 수 있다.
- **주의사항**:
  - 작업 트리에 세 개의 **사용자/외부 상태로 보이는 미추적 항목**이 있다: `.claude/skills/`, `.vercel/`, `apps/dashboard/.gitignore`. 이번 세션에서 만들거나 수정하지 않았으므로 검토 전 삭제·추가·커밋하지 말 것.
  - v1.0 Phase 문서는 더 이상 `.planning/phases/`에 없다. 아카이브 경로 `.planning/milestones/v1.0-phases/`를 사용한다.
  - API 사용자 경로는 요청자 JWT, worker/migration만 `service_role`이라는 RLS 경계를 유지한다.

## 🚀 5. 다음 세션 재개 안내

다음 세션 시작 시 `/catchup` 스킬을 실행하거나 아래 멘트를 입력하세요:

> "HANDOFF.md와 .planning/PROJECT.md를 확인하고, v1.1 후보를 정리하기 위해 /gsd-new-milestone부터 시작해줘."
