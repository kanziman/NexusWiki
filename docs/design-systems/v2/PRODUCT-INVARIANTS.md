# 넥서스위키(NexusWiki) 제품 핵심 불변식 (Product Invariants)

> 이 문서는 넥서스위키의 모든 화면 설계(PRD), 데이터베이스 DDL, 비동기 파이프라인 및 UI 프로토타입 작성 시 **절대 위반할 수 없는 단일 진실 공급원(Single Source of Truth)**입니다.

---

## 1. 컴파일 & 재컴파일 불변식 (Compiler & Jobs)

### ❌ [금지] "사용자 수동 재컴파일 트리거" 버튼은 존재하지 않음
* **원칙**: 위키 생성과 갱신은 **"원본 소스가 변경/추가/삭제될 때 시스템 백그라운드 워커가 자동으로 실행하는 비동기 파이프라인"**입니다.
* 사용자가 누르는 "위키 수동 재컴파일" 버튼은 UI 어디에도 존재하지 않습니다.
* **유일한 사용자 액션**:
  1. `[+ 소스 추가]` / 소스 파일 업로드 또는 삭제 (➔ 백그라운드 파이프라인 자동 실행)
  2. 비동기 잡이 실패했을 때 `JobStepper`에서 누르는 `[재시도 (Retry)]` 버튼

---

## 2. 공개 위키 URL 네임스페이스 및 충돌 방지 불변식 (Public Routing)

### ❌ [금지] 전역 플랫 URL `/p/[page_slug]` 사용 금지
* **원칙**: 넥서스위키의 위키 슬러그는 워크스페이스 내부에서만 고유합니다(`UNIQUE (workspace_id, slug)`).
* 서로 다른 워크스페이스(A사, B사)가 동일한 `tenant-isolation-rls` 슬러그를 공개할 수 있으므로, 전역 플랫 URL(`/p/[slug]`)은 심각한 라우팅 충돌을 일으킵니다.
* **공개 URL 표준 규격**:
  $$\text{https://nexuswiki.io/p/}\mathbf{[workspace\_slug]}\text{/}\mathbf{[page\_slug]}$$
* **동작 계약**:
  1. `workspace_public_settings`에 `workspace_slug` (전역 고유 식별자)가 존재합니다.
  2. 라우터는 `/p/[workspace_slug]/[page_slug]` 경로를 파싱하여 해당 워크스페이스의 마스터 스위치가 `ON`이고 발행본(`wiki_page_publications`)이 존재하는 경우에만 정확히 렌더링합니다.

---

## 3. 인간 검증(`verification_status`) 보존 불변식

* `wiki_pages.verification_status` (`'unverified'`, `'verified'`, `'stale'`)는 **사람(엔지니어)이 직접 검토하여 세우는 신뢰 뱃지**입니다.
* 백그라운드 AI 컴파일러(`_upsert_page`)는 이 필드를 절대 오버라이트하지 않습니다.
* **공개 및 재발행 수명주기**:
  1. `verification_status == 'verified'`인 문서만 공개(`[웹에 공개]`) 신청 가능.
  2. 공개 이후 재컴파일로 내용이 바뀌었는지는 `wiki_pages.updated_at > wiki_page_publications.published_at` 타임스탬프 비교로만 판정.

---

## 4. 1:1 사이드카 테넌트 격리 & 물리적 킬스위치 불변식

1. **테넌트 격리 복합 FK**:
   * 모든 자식 테이블과 사이드카 테이블은 `FOREIGN KEY (parent_id, workspace_id) REFERENCES parent_table(id, workspace_id)`를 강제하여 RLS 우회 시에도 테넌트 교차 오염을 원천 차단.
2. **사이드카 테이블 분리**:
   * `workspace_public_settings`: 워크스페이스 마스터 스위치 및 공개 메타데이터 (핵심 `workspaces` 테이블 오염 0%).
   * `wiki_page_publications`: 사람이 검토 승인한 단 1건의 공개 불변 발행본 (본문 전문 + 승인된 인용 스니펫 JSONB).
3. **물리적 킬스위치 (Engine-level Kill Switch)**:
   * `workspace_public_settings.allow_public_sharing`이 `false`면 PostgreSQL RLS 엔진 레벨에서 모든 공개 엔드포인트 조회가 0건(404)으로 즉시 일괄 차단.

---

## 5. 디자인 시스템 룩앤필 불변식

1. **100% Pure Crisp White Mode**: 순백색(`#FFFFFF`), 쿨 슬레이트(`#F8FAFC`), `#E2E8F0` 헤어라인 보더.
2. **Zero Emojis**: 일체의 이모지 배제, 2.0~2.2px 단색 Monochrome SVG 라인 아이콘만 사용.
