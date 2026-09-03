# 미완성 백로그 페이지 (`/w/[workspaceId]/backlog`) 리디자인 계획서

본 문서는 `taste-skill` 및 `NexusWiki v2 디자인 시스템` 원칙을 기반으로, 미완성 백로그(레드링크 관리) 페이지의 정보 구조·시각적 위계·사용자 인터랙션을 고도화하기 위한 상세 리디자인 설계 계획서입니다.

* **인터랙티브 프리뷰:** [`apps/dashboard/public/backlog-preview.html`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/public/backlog-preview.html)  
  👉 로컬 실행 주소: [`http://localhost:3000/backlog-preview.html`](http://localhost:3000/backlog-preview.html)
* **대상 컴포넌트:**  
  - [`apps/dashboard/app/w/[workspaceId]/backlog/page.tsx`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/app/w/[workspaceId]/backlog/page.tsx) (서버 컴포넌트)
  - [`apps/dashboard/components/BacklogList.tsx`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/components/BacklogList.tsx) (클라이언트 목록 컴포넌트)
  - [`apps/dashboard/components/BacklogDetailModal.tsx`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/components/BacklogDetailModal.tsx) (상세 발췌문 모달)

---

## 1. 배경 및 문제 진단 (Audit & Critique)

현재의 미완성 백로그 화면은 기능적으로 완성되어 있으나, 최근 리디자인된 **홈 대시보드(Bento & Card-Row)** 및 **원문 소스 관리**에 비해 시각적 레지스터와 사용 편의성 측면에서 다음과 같은 한계를 지니고 있습니다.

1. **지루한 2단 텍스트 통계 바 (Bland Flat Stats):**
   * 현재 `section.stats`는 `9 / 미해결 백로그`, `8 / 영향받는 위키` 2개의 숫자가 단순 나열되어 있어, 지식 공백의 심각도(집중 인용되는 핵심 공백, 자동 해결 파이프라인 상태)가 시각적으로 전달되지 않습니다.
2. **테이블의 반응형 한계 및 행 높이 불균일 (Broken Table Flow):**
   * 전형적인 5열 테이블 구조(`<table>`)로 되어 있어, 인용 중인 위키 문서가 2~3편 이상인 경우 특정 행만 세로로 길어져 표 전체의 균형이 깨집니다.
3. **툴바 높이 불일치 및 필터 옵션 부족:**
   * 단순 텍스트 밑줄 탭(`전체 9`) 하나만 존재하여, 실무에서 시급하게 먼저 메꿔야 하는 '다중 인용(🔥 Multi-citation)' 백로그를 빠르게 추려볼 수 없습니다.
4. **라인 정렬 및 비주얼 위계 부재:**
   * 레드링크(미작성 지식)라는 특성이 단순 텍스트로만 표시되어, 해결해야 할 지식 공백이라는 시각적 긴장감(Affordance)이 부족합니다.

---

## 2. 핵심 리디자인 원칙 (Taste-Skill Anti-Slop Rules)

* **단일 테마 및 v2 토큰 철저 준수 (Strict v2 Tokens):**
  * `docs/design-systems/v2/nexuswiki-design-system.css`의 `:root` 토큰만 사용하며, 임의의 hex 코드나 새로운 비표준 색상을 추가하지 않습니다.
  * 과도한 보더레디우스(16px 이상)를 배제하고, **카드 외곽 10~12px, 내부 아이템 8px, 칩/버튼 6px**의 단정하고 절제된 곡률을 유지합니다.
* **4열 미니 벤토 메트릭 스트립:**
  * `미해결 레드링크` (9개 주제 · 앰버 경고 톤)
  * `영향받는 위키` (8개 문서 · 링크 결손 알림)
  * `최다 인용 핵심 공백` (포지셔닝-5가지-구성요소 · 2회 인용 집중)
  * `자동 해결 준비도` (소스 추가 시 즉시 컴파일 안내)
* **38px 높이 완전 통일 툴바 및 스마트 세그먼트:**
  * 좌측 세그먼트 바(`.segment-bar`)와 우측 검색창(`.search-box input`)의 높이를 모두 **`height: 38px`로 완전 통일**.
  * 실무 중심의 세그먼트 필터: `[전체 백로그 9]`, `[🔥 다중 인용 2]`, `[단일 인용 7]`.
  * 검색창: `360px` 가로폭 및 `/` 키 단축키 힌트.
* **5열 CSS Grid 카드-로우 및 완벽한 수직 라인 동기화:**
  * 상단 헤더와 개별 카드가 동일한 5열 CSS Grid 규격을 공유하여 완벽하게 정렬:
    ```css
    grid-template-columns: minmax(0, 1.4fr) minmax(0, 1.25fr) 95px 100px 105px;
    gap: 20px;
    padding: 0 20px;
    ```
  * 모든 백로그 카드의 높이를 **`height: 68px`로 엄격히 고정**.
  * **1열 (백로그 주제):** 레드링크 경고 뱃지(`🔗`) + 주제명(클릭 시 발췌 모달) + 슬러그(11px Mono).
  * **2열 (인용 중인 위키):** 단일 행 정렬(`flex-wrap: nowrap`, 최대 2개 칩 + `+N개 더` 배지 줄바꿈 원천 방지).
  * **3열 (인용 빈도):** `2 회` (13.5px Bold Mono, 우측 정렬).
  * **4열 (최초 감지):** `2일 전` (11.5px 서브틀, 좌측 정렬).
  * **5열 (해결 액션):** `+ 소스 추가` 버튼 (우측 정렬, 호버 시 틸 톤 반전).

---

## 3. 화면별 상세 UI 스펙

### 3.1 4열 벤토 메트릭 스트립 (`.metrics-grid`)
```html
<div class="metrics-grid">
  <!-- 1. 미해결 레드링크 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">미해결 레드링크</span><i data-lucide="alert-triangle"></i></div>
    <div class="metric-main"><span class="metric-value">9</span><span class="metric-unit">개 주제</span></div>
    <div class="metric-footer"><span class="status-pill warning">우선 해결 필요</span></div>
  </div>
  <!-- 2. 영향받는 위키 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">영향받는 위키</span><i data-lucide="book-open"></i></div>
    <div class="metric-main"><span class="metric-value">8</span><span class="metric-unit">개 문서</span></div>
    <div class="metric-footer"><span class="status-pill accent">링크 결손 발생</span></div>
  </div>
  <!-- 3. 최다 인용 핵심 공백 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">최다 인용 핵심 공백</span><i data-lucide="trending-up"></i></div>
    <div class="metric-main"><span class="metric-value">포지셔닝-5가지...</span></div>
    <div class="metric-footer"><span class="status-pill good">인용 2회 집중</span></div>
  </div>
  <!-- 4. 자동 해결 준비도 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">자동 해결 준비도</span><i data-lucide="sparkles"></i></div>
    <div class="metric-main"><span class="metric-value">대기 중</span></div>
    <div class="metric-footer"><span>소스 추가 시 즉시 컴파일</span></div>
  </div>
</div>
```

### 3.2 일체형 백로그 테이블 컨테이너 (`BacklogTableContainer`) 및 동기화된 5열 CSS Grid
헤더가 공중에 붕 떠 있고 개별 카드가 따로 흩어져 있던 어색함을 해결하기 위해, **단일 일체형 테이블 래퍼 컨테이너 (`.backlog-table-container`)** 내부에 상단 헤더와 로우 아이템들을 결합했습니다.

* **외곽 컨테이너:** `border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--surface); box-shadow: var(--shadow-2xs);`
* **헤더 바 (`.list-header-row`):** 컨테이너 상단에 단정하게 안착되며, 은은한 서브틀 배경(`var(--bg-subtle)`)과 하단 구분선(`border-bottom: 1px solid var(--border)`) 적용.
* **데이터 로우 (`.backlog-row-item`):** 개별 카드가 아니라 행 구분선(`border-bottom: 1px solid var(--border)`)으로 연결된 매끄러운 엔터프라이즈 로우. 호버 시 부드러운 하이라이트.

```html
<!-- 단일 일체형 테이블 컨테이너 -->
<section class="backlog-table-container" data-od-id="backlog-table-section">
  <!-- 상단 리스트 컬럼 헤더 -->
  <div class="list-header-row">
    <div class="header-col-primary">백로그 주제 (레드링크)</div>
    <div class="header-col-wiki">인용 중인 위키 문서</div>
    <div class="header-col-frequency">인용 빈도</div>
    <div class="header-col-detected">최초 감지</div>
    <div class="header-col-actions">해결 액션</div>
  </div>

  <!-- 데이터 행 목록 -->
  <div class="backlog-list" id="backlogList">
    <article class="backlog-row-item">
      <!-- 1. 백로그 주제 -->
      <div class="topic-primary-col">
        <div class="redlink-icon-box"><i data-lucide="link-2-off" size="16"></i></div>
        <div class="topic-title-meta">
          <button type="button" class="topic-title-btn">포지셔닝-5가지-구성요소</button>
          <span class="topic-slug">포지셔닝-5가지-구성요소</span>
        </div>
      </div>

      <!-- 2. 인용 중인 위키 문서 (단일 행 정렬, 북 아이콘 일관성, 줄바꿈 완전 방지) -->
      <div class="wiki-chips-col">
        <div class="wiki-chips-box">
          <a href="/wiki/feature-vs-value" class="wiki-chip"><i data-lucide="book-open" size="12"></i><span>기능 vs 가치 구분</span></a>
          <a href="/wiki/april-dunford" class="wiki-chip"><i data-lucide="book-open" size="12"></i><span>April Dunford</span></a>
          <span class="wiki-chip-more">+3개 더</span>
        </div>
      </div>

      <!-- 3. 인용 빈도 (우측 정렬) -->
      <div class="frequency-col">
        <span class="freq-count">2</span><span class="freq-unit">회</span>
      </div>

      <!-- 4. 최초 감지 (좌측 정렬) -->
      <div class="detected-col">
        <span>2일 전</span>
      </div>

      <!-- 5. 해결 액션 (우측 정렬) -->
      <div class="action-col">
        <a href="/sources?prefillTitle=...&tab=text" class="add-source-btn">
          <i data-lucide="plus" size="12"></i>
          <span>소스 추가</span>
        </a>
      </div>
    </article>
  </div>
</section>
```

---

## 4. 보존되어야 할 핵심 시스템 계약 (Preserved Contracts)

1. **테스트 셀렉터 계약 유지:**
   * `data-od-id="backlog-header"` (헤더 섹션)
   * `data-od-id="backlog-table-section"` (테이블/목록 래퍼 섹션)
   * `role="tablist"` (세그먼트 탭 네비게이션)
   * `aria-label="백로그 필터"`, `aria-label="백로그 검색"`
   * `EMPTY_HEADING`, `EMPTY_BODY` (빈 상태 텍스트)
   * `.topic` (상세 발췌 모달 트리거)
   * `button.compact` (`+ 소스 추가` 버튼 링크)
2. **컴포넌트 및 동작 계약:**
   * `BacklogDetailModal`: 주제 클릭 시 인용 위키별 발췌문(`excerpt`)을 보여주는 모달 연동 유지.
   * `RedLinkCta`: `+ 소스 추가` 클릭 시 쿼리 파라미터(`prefillTitle`, `tab=text`)를 담아 `/sources`로 이동하는 워크플로우 유지.
   * `Pagination`: 페이지당 8개 아이템 페이지네이션 유지.

---

## 5. 구현 단계 (Phases)

* **Phase 1 (프리뷰 검증):**
  * `apps/dashboard/public/backlog-preview.html`을 통해 시각적 위계, 반응형 그리드, 폰트 가독성 검토.
* **Phase 2 (BacklogList 컴포넌트 리팩토링):**
  * `apps/dashboard/components/BacklogList.tsx`의 마크업을 4열 벤토 메트릭 및 5열 CSS Grid Card-Row 구조로 교체.
* **Phase 3 (테스트 검증):**
  * `tests/BacklogList.test.tsx`, `tests/backlog-page-route.test.tsx` 실행 및 전건 통과 확인.
