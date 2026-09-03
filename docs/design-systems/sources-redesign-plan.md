# 원문 소스 관리 페이지 (`/w/[workspaceId]/sources`) 리디자인 계획서

본 문서는 `taste-skill` 및 `NexusWiki v2 디자인 시스템` 원칙을 기반으로, 원문 소스 관리 페이지의 정보 구조·시각적 위계·사용자 인터랙션을 고도화하기 위한 상세 리디자인 설계 계획서입니다.

* **인터랙티브 프리뷰:** [`apps/dashboard/public/sources-preview.html`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/public/sources-preview.html)  
  👉 로컬 실행 주소: [`http://localhost:3000/sources-preview.html`](http://localhost:3000/sources-preview.html)
* **대상 컴포넌트:**  
  - [`apps/dashboard/app/w/[workspaceId]/sources/page.tsx`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/app/w/[workspaceId]/sources/page.tsx) (서버 컴포넌트)
  - [`apps/dashboard/components/SourcesList.tsx`](file:///Users/zorba/projects/NexusWiki/apps/dashboard/components/SourcesList.tsx) (클라이언트 목록 컴포넌트)

---

## 1. 배경 및 문제 진단 (Audit & Critique)

현재의 원문 소스 관리 화면은 기능적으로 완성되어 있으나, 최근 리디자인된 **홈 대시보드(Bento & Card-Row)** 및 **위키 라이브러리**에 비해 시각적 레지스터와 사용 편의성 측면에서 다음과 같은 한계를 지니고 있습니다.

1. **지루한 상단 통계 바 (Bland Flat Stats):**
   * 현재 `section.stats`는 3개의 숫자와 라벨이 단순 수직 보더(`border-right`)로 나열되어 있어, 홈 대시보드의 세련된 벤토 메트릭 카드에 비해 데이터의 의미(청킹 진행률, 위키 연결률)가 시각적으로 전달되지 않습니다.
2. **테이블의 반응형 한계 및 행 높이 불균일 (Broken Table Flow):**
   * 전형적인 6열 테이블 구조(`<table>`)로 되어 있어, 연결된 위키 문서가 3~5편 이상인 경우 특정 행만 세로로 길어져 표 전체의 균형이 깨집니다.
   * 작은 화면이나 모바일에서는 가로 스크롤(`overflow-x-auto`)이 강제되어 한눈에 메타데이터를 파악하기 어렵습니다.
3. **업로드 동선의 분리감 (Disjointed Ingestion):**
   * 상단 우측의 `+ 소스 업로드` 버튼 클릭 시 인라인 Dropzone이 목록을 덜컥 밀어내며 나타나 시각적 연속성이 부족합니다.
4. **검색 및 필터 툴바의 단조로움:**
   * 단순 텍스트 밑줄 탭과 검색 인풋이 분리되어 있어, 위키 라이브러리의 모던한 **세그먼트 칩 탭**과 디자인 언어가 갈라집니다.

---

## 2. 핵심 리디자인 원칙 (Taste-Skill Anti-Slop Rules)

* **단일 테마 및 v2 토큰 철저 준수 (Strict v2 Tokens):**
  * `docs/design-systems/v2/nexuswiki-design-system.css`의 `:root` 토큰만 사용하며, 임의의 hex 코드나 새로운 비표준 색상을 추가하지 않습니다.
  * 과도한 보더레디우스(16px 이상)를 배제하고, **카드 외곽 10~12px, 내부 아이템 8px, 칩/버튼 6px**의 단정하고 절제된 곡률을 유지합니다.
* **카드-로우(Card-Row) 하이브리드 아키텍처 및 높이 통일 (Strict 72px Height):**
  * 획일적인 격자 테이블을 탈피하고, 각 원문 소스를 **독립적인 정보 카드 행(Card-Row)**으로 구성합니다.
  * 모든 소스 카드의 높이를 **`height: 72px`로 엄격히 고정**하여, 리스트가 정갈한 리듬감을 갖도록 합니다.
  * **좌측 (주연):** 포맷 배지(MD/PDF 11px 볼드) + 소스 제목(14.5px 볼드) + 파일 크기/타입/일시(11.5px 서브틀)를 수직 중앙 정렬(`align-items: center`).
  * **중앙 (지식 네트워크):** 인용한 위키 문서를 단일 행(`flex-wrap: nowrap`, 최대 2개 칩 + `+N개 더` 배지)으로 고정하여 칩 개수에 따라 카드가 세로로 늘어나는 현상을 원천 방지.
  * **우측 (엔지니어링 메트릭 & 액션):** 청크 개수/좌표 + 파이프라인 상태(펄스 인디케이터 `🟢 5/5단계 완료`) + `[상세 보기]` 링크 및 삭제 버튼.
* **4열 미니 벤토 메트릭 스트립:**
  * `총 등록 원문` (포맷별 비율 칩 포함)
  * `생성된 청크 & 인덱싱` (100% 인덱싱 상태 배지)
  * `위키 인용 연결률` (고아 소스 유무 확인)
  * `파이프라인 건강도` (모든 소스의 정상 처리 여부)
* **확장된 검색바 및 세그먼트 툴바 높이 완전 통일 (Strict 38px Height):**
  * 좌측 세그먼트 탭 바(`.segment-bar`)와 우측 검색창(`.search-box input`)의 높이를 모두 **`height: 38px; box-sizing: border-box;`로 엄격히 고정**하여 수평 수평선이 완벽하게 일치하도록 구현.
  * 검색바 가로 폭을 **`360px`로 넉넉하게 확장**하고 내부 여백을 넓혀 시원한 입력 경험 제공 (`/` 키 단축키 힌트 포함).
  * `[전체 12]`, `[텍스트/마크다운 12]`, `[PDF 0]` 카운트 세그먼트 칩과 시각적 균형 유지.

---

## 3. 화면별 상세 UI 스펙

### 3.1 4열 벤토 메트릭 스트립 (`.metrics-grid`)
```html
<div class="metrics-grid">
  <!-- 1. 총 등록 원문 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">총 등록 원문</span><i data-lucide="file-text"></i></div>
    <div class="metric-main"><span class="metric-value">12</span><span class="metric-unit">개 문서</span></div>
    <div class="metric-footer"><span class="status-pill accent">MD 12</span><span class="status-pill neutral">PDF 0</span></div>
  </div>
  <!-- 2. 청크 및 인덱싱 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">생성된 청크</span><i data-lucide="layers"></i></div>
    <div class="metric-main"><span class="metric-value">63</span><span class="metric-unit">청크 완료</span></div>
    <div class="metric-footer"><span class="status-pill good">100% 인덱싱 완료</span></div>
  </div>
  <!-- 3. 위키 인용 연결률 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">위키 인용 연결률</span><i data-lucide="link-2"></i></div>
    <div class="metric-main"><span class="metric-value">12/12</span><span class="metric-unit">연동됨</span></div>
    <div class="metric-footer"><span class="status-pill good">고아 소스 없음 (100%)</span></div>
  </div>
  <!-- 4. 파이프라인 건강도 -->
  <div class="metric-card">
    <div class="metric-top"><span class="metric-label">파이프라인 상태</span><i data-lucide="activity"></i></div>
    <div class="metric-main"><span class="metric-value">정상</span><span class="metric-unit">5/5단계</span></div>
    <div class="metric-footer"><span>최종 처리 완료</span></div>
  </div>
</div>
```

### 3.2 일체형 테이블 컨테이너 (`SourcesTableContainer`) 및 동기화된 5열 CSS Grid
상단에 헤더가 공중에 붕 떠 있고 개별 카드가 따로 흩어져 있던 어색함을 해결하기 위해, **단일 일체형 테이블 래퍼 컨테이너 (`.sources-table-container`)** 내부에 상단 헤더와 로우 아이템들을 결합했습니다.

* **외곽 컨테이너:** `border: 1px solid var(--border); border-radius: 12px; overflow: hidden; background: var(--surface); box-shadow: var(--shadow-2xs);`
* **헤더 바 (`.list-header-row`):** 컨테이너 상단에 단정하게 안착되며, 은은한 서브틀 배경(`var(--bg-subtle)`)과 하단 구분선(`border-bottom: 1px solid var(--border)`) 적용.
* **데이터 로우 (`.source-row-item`):** 개별 카드가 아니라 행 구분선(`border-bottom: 1px solid var(--border)`)으로 연결된 매끄러운 엔터프라이즈 로우. 호버 시 부드러운 하이라이트.
* **헤더 '작업'과 삭제 아이콘 수직축 일치:** 상단 헤더의 `<span>작업</span>`과 하단 카드의 삭제 버튼(`.delete-icon-btn`)을 모두 **동일한 `width: 30px; text-align: center;` 규격**으로 우측 끝선에 정렬(`justify-content: flex-end`)하여, 텍스트와 휴지통 아이콘의 수직 중심축이 1픽셀의 오차도 없이 일치하도록 구현.

```html
<!-- 단일 일체형 테이블 컨테이너 -->
<section class="sources-table-container" data-od-id="source-table-section">
  <!-- 상단 리스트 컬럼 헤더 (5개 직속 Grid 아이템) -->
  <div class="list-header-row">
    <div class="header-col-primary">소스 파일</div>
    <div class="header-col-wiki">연결된 위키 문서 (인용)</div>
    <div class="header-col-chunks">청크 및 좌표</div>
    <div class="header-col-pipeline">파이프라인</div>
    <div class="header-col-actions"><span>작업</span></div>
  </div>

  <!-- 데이터 행 목록 -->
  <div class="sources-list" id="sourcesList">
    <article class="source-row-item">
      <!-- 1. 소스 파일 -->
      <div class="source-primary-col">
        <div class="format-badge md">MD</div>
        <div class="source-title-meta">
          <a href="/sources/{id}" class="source-title">02_the_dip_and_tribes.md</a>
          <div class="source-meta-row">
            <span>2.9 KB</span> • <span>file</span> • <span>2일 전</span>
          </div>
        </div>
      </div>

      <!-- 2. 연결된 위키 문서 (인용) -->
      <div class="source-wiki-col">
        <div class="wiki-chips-box">
          <a href="/wiki/tribes" class="wiki-chip"><i data-lucide="book-open" size="12"></i> <span>트라이브스 (Tribes)</span></a>
          <a href="/wiki/the-dip" class="wiki-chip"><i data-lucide="book-open" size="12"></i> <span>더 딥 (The Dip)</span></a>
          <span class="wiki-chip-more">+3개 더</span>
        </div>
      </div>

      <!-- 3. 청크 및 좌표 (우측 정렬) -->
      <div class="chunk-stat-box">
        <div class="chunk-count">5 청크</div>
        <div class="chunk-chars">0 ~ 1,444 char</div>
      </div>

      <!-- 4. 파이프라인 (좌측 정렬) -->
      <div class="pipeline-status-box">
        <span class="pulse-dot"></span>
        <span>5/5단계 완료</span>
      </div>

      <!-- 5. 작업 (우측 정렬, white-space: nowrap) -->
      <div class="source-actions-box">
        <a href="/sources/{id}" class="detail-btn">상세 보기</a>
        <button class="delete-icon-btn" title="삭제"><i data-lucide="trash-2" size="14"></i></button>
      </div>
    </article>
  </div>
</section>
```

---

## 4. 보존되어야 할 핵심 시스템 계약 (Preserved Contracts)

1. **테스트 셀렉터 계약 유지:**
   * `data-od-id="source-table-section"` (테이블 래퍼 섹션)
   * `data-testid="empty-sources-dropzone-container"` (빈 상태 컨테이너)
   * `data-testid="delete-source-btn-${source.id}"` (개별 소스 삭제 버튼)
   * `role="tablist"` 및 `aria-selected` (MIME 필터 탭)
2. **컴포넌트 및 동작 계약:**
   * `JobStepper`: 실시간 인덱싱 진행 단계 및 펄스 상태 유지.
   * `Dropzone`: 파일 드롭, 텍스트 입력, URL 크롤링 탭 동작 불변.
   * `Pagination`: 페이지당 8개 아이템 페이지네이션 유지.
   * `delete_raw_source`: 오너 전용 삭제 권한(`isOwner`) 게이트 불변.

---

## 5. 구현 단계 (Phases)

* **Phase 1 (프리뷰 검증):**
  * `apps/dashboard/public/sources-preview.html`을 통해 시각적 위계, 반응형 그리드, 폰트 가독성 검토.
* **Phase 2 (SourcesList 컴포넌트 리팩토링):**
  * `apps/dashboard/components/SourcesList.tsx`의 밋밋한 테이블 마크업을 벤토 메트릭 및 Card-Row 구조로 교체.
* **Phase 3 (테스트 검증):**
  * `tests/SourcesList.test.tsx`, `tests/SourceDeletion.test.tsx`, `tests/source-detail-route.test.tsx` 실행 및 통과 확인.
