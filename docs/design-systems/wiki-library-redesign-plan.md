# 위키 라이브러리 페이지 리디자인 설계 및 구현 계획서
**문서 위치:** `docs/design-systems/wiki-library-redesign-plan.md`  
**대상 컴포넌트:** `apps/dashboard/app/w/[workspaceId]/wiki/page.tsx` & `components/WikiLibrary.tsx`  
**디자인 기준:** leonxlnx (Anti-Slop Taste-Skill) & Quiet Editorial System  
**최종 업데이트:** 2026-09-01

---

**구현 전 게이트.** 이 문서는 디자인 계획서이며, 아직 OpenSpec change로 승격되지 않았다. `openspec/changes/`에는 archive만 있다. 위키 라이브러리의 사용자 행동을 바꾸는 변경이므로, 구현 전에 `/plan-feature` → `/opsx:propose`를 거쳐야 한다.

---

## 1. 개요 및 현황 진단 (The Anti-Slop Audit)

### 1.1 현 화면의 주요 문제점
제공해주신 스크린샷(`nexuswiki.vercel.app/w/.../wiki`)을 기반으로 진단한 핵심 개선 과제 5가지:

```
[현재 위키 라이브러리 화면의 시각적 결함 요약]
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. 상단 헤더: "위키" 텍스트만 덩그러니 놓여 시각적 위계와 밀도 부족           │
│ 2. 통계 박스: 단순 2분할 텍스트("28 전체 문서 | 28 검증됨")로 생동감 부재    │
│ 3. 필터/검색 바: 칩 크기가 너무 작고(tiny), 검색창과 시각적 밸런스가 어긋남    │
│ 4. 문서 행(Row): 발췌문(Excerpt)이 1400px 가로 전체로 길게 늘어져 가독성 저하│
│ 5. 액션 영역: 체크박스, 배지, 본문, 삭제(휴지통), 화살표가 한 행에 산만하게 분산 │
└─────────────────────────────────────────────────────────────────────────────┘
```

1. **지나친 가로 늘어짐(Unbounded Line Length):**
   * 발췌문이 와이드 스크린 전체 너비(1200px 이상)로 한 줄로 길게 펼쳐져 있어, 가독성 최적 너비인 65~75ch를 크게 초과합니다.
2. **평면적이고 무미건조한 통계:**
   * 단순히 2칸짜리 회색 사각형에 숫자 28만 적혀 있어, "지식이 얼마나 건강하고 최신 상태인지"에 대한 통찰을 주지 못합니다.
3. **카테고리 칩의 정보 가치 부족:**
   * `[전체] [개념] [엔티티] [가이드] [맵]` 버튼에 각 카테고리별 문서 개수 카운트가 없어, 눌러보기 전에는 몇 개의 문서가 있는지 알 수 없습니다.
4. **시각적 위계의 혼선:**
   * 카테고리 배지와 `검증됨` 배지가 제목 바로 위에 너무 작게 붙어 있어, 제목이 먼저 눈에 들어오지 않고 시선이 분산됩니다.
5. **일괄 작업(Bulk Action) 바의 덜컹거림:**
   * 체크박스 선택 시 나타나는 상단 바가 테이블 헤더처럼 끼어들어 레이아웃의 상하 리듬을 해칩니다.

---

## 2. 디자인 원칙 (Taste-Skill Redesign Principles)

1. **Quiet Editorial Craft (정제된 지식 서재):**
   * 위키는 읽고 탐색하는 공간입니다. 형광색이나 요란한 장식 대신, **Pretendard / Plus Jakarta Sans** 기반의 단정한 타이포그래피와 부드러운 중립 톤(Slate/Zinc)을 사용하여 신뢰감을 줍니다.
2. **Optimal Reading Bounds (가독성 폭 제한):**
   * 문서 제목과 발췌문 영역을 `max-w-3xl` 내외로 우아하게 제한하고, 2줄 말줄임(`line-clamp-2`)과 1.6의 행간을 적용하여 편안한 읽기 경험을 제공합니다.
3. **Micro-Card Surface Elevation (입체적 카드 로우):**
   * 단순 구분선 나열 방식에서 벗어나, 각 문서 행을 **서틀한 마이크로 카드 형태(1px 섬세한 보더 + 호버 시 elevation)**로 감싸 클릭 감도를 높입니다.
4. **Floating Floating Action Bar (우아한 플로팅 일괄 액션):**
   * 문서 선택 시 화면 중앙 하단 또는 리스트 상단에 부드러운 블러(Backdrop Blur) 효과를 가진 플로팅 툴바가 슬라이드업되어 전문적인 툴(Raycast/Linear) 감성을 부여합니다.

---

## 3. 새로운 위키 라이브러리 UI 레이아웃 설계

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ 📚 마케팅 올스타  /  위키 라이브러리                                         │
│ ─────────────────────────────────────────────────────────────────────────── │
│                                                                             │
│  [헤더 & 스마트 지식 상태]                                                  │
│  위키 라이브러리                               [+ 원문 수집] [새 문서 작성] │
│  원문 소스에서 검증 및 컴파일된 28편의 상호 연결된 지식 문서입니다.           │
│                                                                             │
│  ┌─ [지식 완성도 & 카테고리 현황 (Bento Header)] ────────────────────────┐  │
│  │ 🟢 100% (28/28)   │ 💡 개념 14  │ 👤 엔티티 4 │ 🧭 가이드 8 │ 🗺 맵 2  │  │
│  │    전 문서 신뢰   │   핵심 이론 │   인물·개체 │   실전 적용 │  지식 맵│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ [툴바: 카테고리 세그먼트 & 스마트 검색] ─────────────────────────────┐  │
│  │ [전체 28] [💡 개념 14] [👤 엔티티 4] [🧭 가이드 8] [🗺 맵 2]  [🔍 검색]│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ [문서 리스트 (Card-Row)] ────────────────────────────────────────────┐  │
│  │ [ ] 💡 개념  •  🟢 검증됨  •  🔗 인용 2개                                │  │
│  │     100의 법칙 (The Rule of 100)                               [🗑️] [>] │  │
│  │     Alex Hormozi가 제시한 리드 생성 실행 철학으로, core-four의 각     │  │
│  │     채널을 압도적인 볼륨으로 최소 100일간 매일 연속 실행하는 원칙...  │  │
│  │ ────────────────────────────────────────────────────────────────────  │
│  │ [ ] 👤 엔티티  •  🟢 검증됨  •  🔗 인용 3개                               │  │
│  │     April Dunford (에이프릴 던포드)                             [🗑️] [>] │  │
│  │     B2B 제품 포지셔닝의 세계적 권위자이자 'Obviously Awesome'의 저자. │  │
│  │     경쟁 대안, 고유 속성, 가치, 타깃 고객의 5단계 피치 공식을 정립...  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─ [플로팅 일괄 작업 바 (체크 시 표시)] ────────────────────────────────┐  │
│  │   ✓ 3개 문서 선택됨       [선택 해제]     [선택 일괄 검증] [선택 일괄 발행]│  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│                [ < 이전 ]  1  [2]  3  4  [ 다음 > ]                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. 섹션별 상세 인터랙션 및 컴포넌트 명세

### 4.1 상단 헤더 & 지식 현황 벤토 (Bento Header)
* **헤더 텍스트:**
  * `위키 라이브러리` 대형 타이틀 + `28` 총 문서 수 카운트 뱃지.
  * 서브타이틀: 워크스페이스의 목적을 명시하는 에디토리얼 카피.
* **지식 건강 상태 벤토 카드:**
  * **전체 검증률:** `100% (28/28) 검증됨` (초록색 링 프로그레스 또는 바).
  * **카테고리 퀵 탭:** 각 카테고리(`개념`, `엔티티`, `가이드`, `맵`)별 보유 문서 수를 표시하여 클릭 시 해당 카테고리로 즉시 필터링. 라벨은 `KnowledgeGrid.tsx`의 `CATEGORY_LABELS`와 같다 (`concepts:개념, entities:엔티티, guides:가이드, maps:맵`).

---

### 4.2 카테고리 필터 & 검색 툴바
* **카테고리 세그먼트 버튼:**
  * `[전체 28]`, `[개념 14]`, `[엔티티 4]`, `[가이드 8]`, `[맵 2]`
  * 활성화된 칩: `bg-[var(--accent)] text-white shadow-xs`
  * 비활성 칩: `bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--fg)] border border-[var(--border)]`
  * 카운트 숫자는 `font-mono text-[11px] opacity-80`로 단정하게 표기.
* **스마트 검색 인풋:**
  * `Search` 아이콘. `/` 키 검색 포커스 단축키는 신설하지 않는다.
  * 텍스트 입력 시 실시간 디바운스 필터링 및 우측 `X(지우기)` 버튼 노출.

### 4.3 리스트 컨트롤 및 일괄 선택 바 (List Control & Select All Bar)
* **배치:** 툴바(카테고리/검색)와 카드 리스트 사이에 조용하고 단정한 서브 컨트롤 바로 배치.
* **구성:**
  * **전체 선택 체크박스:** `[ ] 현재 페이지 전체 선택 (N개)`
    * 선택되지 않았을 때: `현재 페이지 전체 선택 (8개)` 은은한 라벨.
    * 1개 이상 선택되었을 때: `[✓] N개 문서 선택됨` 볼드 강조 및 `[선택 해제]` 텍스트 액션 노출.
  * **우측 메타 힌트:** `정렬: 최근 업데이트순` 안내 아이콘.
* **인터랙션 연동:**
  * 전체 선택 체크 시 현재 페이지의 모든 카드가 일괄 선택되고, 화면 하단에 플로팅 일괄 작업 바(Bulk Bar)가 부드럽게 솟아오릅니다.

---

### 4.4 마이크로 카드형 문서 행 (`WikiCardRow`)

단순 텍스트 나열을 탈피하여, 각 행을 **클릭 가능한 인터랙티브 카드**로 구성합니다.

```tsx
// 디자인 콘셉트 코드
// elevation은 실재 토큰 두 개로 만든다 — base는 `--bg`(순백), 호버는 `--surface`(살짝 틴트).
// 같은 토큰을 양쪽에 쓰면 hover가 죽는다.
// (참고: Tailwind v4는 `bg-[var(--x)]/30` 같은 불투명도 수식어를 color-mix 로 컴파일하므로
//  var() 값에도 쓸 수 있다. 이 저장소에도 이미 여러 곳에서 쓰인다.)
<div className="group relative flex items-start gap-4 p-4 rounded-xl border border-[var(--border)] bg-[var(--bg)] hover:bg-[var(--surface)] hover:border-[var(--border-strong)] hover:shadow-xs transition-all">
  {/* 1. 체크박스 (왼쪽 고정 정렬) */}
  <div className="pt-1 flex-none">
    <input type="checkbox" className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)]" />
  </div>

  {/* 2. 메인 콘텐츠 영역 (가독성 폭 제약) */}
  <Link href={`/w/.../wiki/${page.slug}`} className="flex-1 min-w-0 pr-3 block">
    {/* 상단 메타 아이브로우 (제목보다 작고 조용한 10px 마이크로 라인) */}
    <div className="flex items-center gap-1.5 mb-1 leading-none">
      <span className="text-[10.5px] font-bold tracking-wider uppercase text-[var(--accent)]">
        {page.category}
      </span>
      <span className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"></span>
      <span className="inline-flex items-center gap-1 text-[10.5px] font-semibold text-emerald-600">
        <CheckCircle2 size={10} />
        <span>{verificationLabel}</span>
      </span>
      <span className="w-1 h-1 rounded-full bg-[var(--muted)] opacity-40"></span>
      <span className="inline-flex items-center gap-1 text-[10.5px] font-mono text-[var(--muted)]">
        <Link2 size={9} />
        <span>인용 {citationCount}</span>
      </span>
    </div>

    {/* 문서 제목 (시각적 영웅: 17px 볼드 타이틀) */}
    <h3 className="text-[17px] font-bold tracking-tight text-[var(--fg)] group-hover:text-[var(--accent)] transition-colors mb-1">
      {page.title}
    </h3>

    {/* 발췌문 (2줄 제한, 편안한 행간) */}
    <p className="text-xs text-[var(--muted)] leading-relaxed line-clamp-2 max-w-3xl">
      {cleanExcerpt}
    </p>
  </Link>

  {/* 3. 우측 호버 액션 그룹 */}
  <div className="flex items-center gap-2 pt-1 flex-none">
    <button
      title="문서 영구 삭제"
      className="opacity-0 group-hover:opacity-100 p-1.5 rounded-lg text-[var(--muted)] hover:text-red-500 hover:bg-red-50 transition-all"
    >
      <Trash2 size={15} />
    </button>
    <ChevronRight size={16} className="text-[var(--muted)] group-hover:translate-x-0.5 group-hover:text-[var(--accent)] transition-all" />
  </div>
</div>
```

---

### 4.4 플로팅 일괄 작업 바 (Floating Bulk Action Bar)
문서를 1개 이상 선택했을 때, 상단 리스트를 덜컹거리게 밀어내지 않고 **화면 하단 중앙에 떠오르는 우아한 글래스모피즘 바**로 제공합니다:

* **스타일:** `fixed bottom-6 left-1/2 -translate-x-1/2 z-40 bg-[var(--surface)]/90 backdrop-blur-md border border-[var(--border)] shadow-xl rounded-2xl px-5 py-3`
* **구성:**
  * `[✓ N개 문서 선택됨]` 볼드 텍스트
  * `[선택 해제]` 텍스트 버튼
  * 구분선 (`|`)
  * `[✓ 선택 일괄 검증]` 에메랄드 버튼
  * `[🌐 선택 일괄 발행]` 틸/액센트 버튼

---

## 5. 아키텍처 및 하위 호환성 계약

### 5.1 계약 및 데이터 불변식 유지
1. **단일 진실 공급원(Single Source of Truth):**
   * 검증 라벨 및 색상 판정은 기존처럼 `lib/verification-label.ts`의 `isVerified` 및 `verificationLabel` 함수가 100% 통제합니다 (충돌/만료 우선순위 보존).
2. **테스트 셀렉터 유지:**
   * 기존 Vitest 테스트가 검증하는 `data-od-id="wiki-library-header"`, `data-od-id="wiki-library-list"`, `data-testid="select-all-checkbox"`, `data-testid="bulk-verify-btn"`, `data-testid="bulk-publish-btn"`을 그대로 유지하여 회귀를 방지합니다.
3. **RLS 및 권한:**
   * 삭제 권한(`isOwner`), 검증 권한(`canVerify`)에 따른 버튼 노출 조건을 그대로 적용합니다.

---

## 6. 단계별 구현 로드맵 (Phased Roadmap)

| 단계 | 작업 내용 | 검증 기준 |
| :--- | :--- | :--- |
| **Phase 1** | **Bento Header & 메트릭 개편**<br/>- 전체 검증률 및 카테고리별 문서 수 카운트 연산<br/>- 단정한 에디토리얼 헤더 마크업 구축 | 카테고리별 실시간 문서 개수 정확성 확인 |
| **Phase 2** | **필터 및 검색 툴바 리팩토링**<br/>- 카테고리 버튼에 개수 뱃지 추가<br/>- 검색 인풋 디자인 | 검색어 입력 및 칩 클릭 필터링 정상 동작 |
| **Phase 3** | **문서 행 Card-Row 디자인 적용**<br/>- 2줄 말줄임(`line-clamp-2`) 및 가독성 너비 제한<br/>- 카테고리/검증/인용 뱃지 통합 및 호버 모션 | 다양한 화면 해상도에서 줄바꿈 및 호버 확인 |
| **Phase 4** | **플로팅 일괄 액션 바 구축**<br/>- 1개 이상 선택 시 하단 슬라이드업 애니메이션<br/>- 일괄 검증/발행 및 선택 해제 연동 | `WikiBulkActions.test.tsx` 및 선택 테스트 통과 |
| **Phase 5** | **종합 테스트 및 접근성 검증**<br/>- Vitest 실행 (`pnpm test`)<br/>- 타입체크 및 린트 검증 (`pnpm typecheck && pnpm lint`)<br/>- 수정 대상 테스트: `apps/dashboard/tests/AskHero.test.tsx:37`의 하드코딩 칩 문자열 `"PostgreSQL RLS 격리 규칙 요약"`, `apps/dashboard/tests/workspace-home.test.tsx:76`의 `h1` `"홈 대시보드"` 단언. 이 두 단언은 대시보드 홈 계획과 충돌하며, 위키 라이브러리 단독 구현만으로는 깨지지 않는다. | 전체 테스트 PASS 유지 |
