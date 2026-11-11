## Context

- 공개 랜딩(`PublicLandingPage`)은 클라이언트 컴포넌트이고, 평가 소개는 제목·문단·`/showcase/evaluation` 링크 하나다.
- 실험 기록은 `apps/dashboard/content/experiments.json`(`eval-experiments.v1`, `synthetic: true`)으로 커밋되고, `lib/experiments.ts`가 정적 import로 읽어 `experimentFor`로 기준 세트·정책·결정을 붙인다. 참조가 끊긴 도입 실험은 `undefined`가 된다.
- 쇼케이스 화면들은 `/` 링크와 서로 간 링크에 `prefetch={false}`를 쓴다. 켜 두면 세션이 있는 방문자에게서 대상 경로의 미들웨어·서버 렌더링이 돌아 인증·DB 요청이 생긴다.
- 공개 위키 뷰어(`/p/[slug]/[page]`) 헤더의 브랜드 마크는 링크가 아닌 `div`다.

## Goals / Non-Goals

**Goals:**

- 대표 실험의 판정을 스냅샷 값만으로 그린다. 스냅샷이 바뀌면 랜딩도 코드 수정 없이 따라 바뀐다.
- 대표 실험을 고르는 규칙과 끊긴 참조 처리를 화면이 아닌 순수 함수에 두어 가짜 스냅샷으로 시험한다.

**Non-Goals:**

- 스냅샷 형식(`eval-experiments.v1`)·등록·내보내기 스크립트·DB·API 변경.
- 통제 전후 비교·평가 설계·회귀 작업대 카드에 수치를 싣는 것. 카드는 소개 문구와 링크만 갖는다. 수치를 실으려면 각 화면의 스냅샷 계약을 다시 확인해야 해서 이번 범위가 아니다.
- 사람 검토 작업대(`/showcase/review`) 연결, 회귀 작업대·검토 화면에 홈 링크 추가.
- 랜딩의 다른 섹션(히어로, 쇼케이스, 활용 사례, FAQ) 문구 변경.

## Decisions

### D1. 구조적 선택지 없음: 기존 스냅샷 헬퍼 위에 선택 함수 하나와 표시 컴포넌트 하나

데이터는 이미 커밋된 정적 JSON이고 읽는 헬퍼가 있다. 데이터 구조·API·상태 관리를 바꾸는 대안이 실질적으로 없으므로 세 안 비교 대신 결정 근거만 남긴다.

- `lib/experiments.ts`에 `featuredAdoption(data = experimentSnapshot)`을 추가한다. 결정 기록이 있는 첫 `adoption` 실험을 찾아 `experimentFor`로 기준·정책·결정을 붙이고, 셋 중 하나라도 없으면 `undefined`를 돌려준다. 판정을 지어내지 않는 규칙이 화면이 아니라 여기서 한 번만 정해진다.
- 스냅샷 타입에 `synthetic`을 노출한다. 합성 표기는 이 값이 `true`일 때만 붙는다.
- 랜딩 평가 섹션을 `components/public-landing/PublicLandingEvaluation.tsx`로 분리한다. 기존 `PublicLandingShowcase`·`PublicLandingFaq`와 같은 배치이고, 가짜 스냅샷을 prop으로 넣어 대체 표시를 시험할 수 있다.
- 실행 출처별 상세 페이지는 고정 매핑(`research` → `/showcase/evidence-research`)으로 두고, 매핑이 없으면 `/showcase/evaluation`으로 연결한다.

기각한 안:

- 랜딩 문구에 수치를 직접 적기: 스냅샷이 갱신되면 랜딩만 낡고, `public-marketing-landing`의 확인되지 않은 수치 금지를 테스트로 지킬 수 없다.
- 서버 컴포넌트(`app/page.tsx`)에서 요약을 계산해 prop으로 넘기기: 스냅샷이 4KB대 정적 JSON이라 번들 절감이 작고, 인증 분기가 있는 홈 라우트에 랜딩 전용 데이터 흐름을 하나 더 만든다.

### D2. 표시 내용

- 대표 실험 블록: 「대표 실험 · 합성 시나리오 기준」 표기(합성일 때만 뒤 절), 실험 제목, 실험 질문, 결정 라벨(`decisionLabels`), 「원래 기준 N개 중 M개 충족」, 미충족 조건 목록(조건 이름 · 실제값 · 허용값), 상세 링크.
- 카드 3개: 평가 설계(`/showcase/evaluation`), 통제 전후 비교(`/showcase/controlled-ai`), 회귀 작업대(`/showcase/regression`). 문구는 각 페이지 메타 설명에서 줄여 쓴다.
- 대체 표시: 대표 실험이 없으면 블록 자리에 기존 소개 문단과 `/showcase/evaluation` 링크만 남긴다. 카드는 스냅샷과 무관하므로 그대로 보인다.
- 모든 링크 `prefetch={false}`, `nw-focus-ring`. 카드는 `md` 이상에서 3열, 그 아래에서 1열.

### D3. 공개 위키 홈 링크

뷰어 헤더의 브랜드 마크 `div`를 같은 클래스의 `Link href="/" prefetch={false} aria-label="NexusWiki 홈"`으로 바꾼다. `.public-brand-logo`가 이미 `display: flex`라 3열 정렬과 크기가 변하지 않는다.

## Risks / Trade-offs

- [스냅샷 조건 문자열(`actual`, `limit`)이 사람이 읽는 문구라 형식이 바뀔 수 있다] → 랜딩은 문자열을 해석하지 않고 그대로 보인다. 테스트는 스냅샷 값과의 일치만 본다.
- [합성 데이터를 실제 성과처럼 읽을 수 있다] → 합성 표기를 같은 블록 첫 줄에 두고, 미채택 결정을 숨기지 않는다.
- [클라이언트 번들에 스냅샷이 들어간다] → 약 4KB이며 쇼케이스 화면이 이미 같은 파일을 번들한다.

## Migration Plan

배포만 하면 된다. DB·환경 변수 변경이 없고, 되돌리기는 커밋 revert다.
