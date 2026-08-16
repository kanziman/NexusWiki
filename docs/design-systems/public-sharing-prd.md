# 넥서스위키(NexusWiki) - 공개 위키 공유 & 1:1 사이드카 아키텍처 PRD

---

## 1. 개요 및 목적 (Overview)
* **기능 명칭**: 위키 문서 외부 웹 공개 (Public Web Sharing)
* **목적**:
  * 내부 엔지니어링 위키 중 기술 가이드, API 명세, 아키텍처 문서를 외부에 **안전하게 선별 공개** (`/p/[workspace_slug]/[page_slug]`).
  * 넥서스위키의 핵심 정체성인 **"원문 인용(Citation) 양방향 추적성"**을 외부 열람자에게도 100% 온전하게 제공하면서, **비공개 원문 소스 유출은 0%로 완벽 차단**.
  * 컴파일러 재작성으로 인한 공개 버전 오염 방지 및 엄격한 인간 육안 검토 게이트(Human-in-the-loop Guardrail) 보장.

---

## 2. 데이터베이스 & 보안 RLS 아키텍처 (1:1 Sidecar Model)

### 2.1 워크스페이스 공개 설정 (`workspace_public_settings`)
* **역할**: 워크스페이스 레벨의 마스터 킬스위치(Kill Switch), 공개 URL 네임스페이스(`public_workspace_slug`), 공개 메타데이터 보관.
* **보안 불변식**: 핵심 `workspaces` 테이블은 `anon`에게 여전히 완전 차단(`fully denied`) 상태를 유지.
```sql
CREATE TABLE workspace_public_settings (
    workspace_id UUID PRIMARY KEY REFERENCES workspaces(id) ON DELETE CASCADE,
    public_workspace_slug TEXT UNIQUE,         -- [충돌 방지] 전역 고유 URL 네임스페이스 (예: nexusdb-core)
    allow_public_sharing BOOLEAN NOT NULL DEFAULT false,
    public_display_name TEXT,                  -- 공개 Docs 사이트 표기명
    public_description TEXT,                   -- 공개 Docs 사이트 소개
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE workspace_public_settings ENABLE ROW LEVEL SECURITY;

-- anon + 모든 사용자: 공개 활성화(true)된 행만 열람 (민감정보 전무)
CREATE POLICY workspace_public_settings_select_public ON workspace_public_settings
FOR SELECT TO anon, authenticated
USING (allow_public_sharing = true);

-- 워크스페이스 멤버: OFF 상태도 확인 가능 (토글 UI 렌더링용)
CREATE POLICY workspace_public_settings_select_member ON workspace_public_settings
FOR SELECT TO authenticated
USING (is_workspace_member(workspace_id));

-- Owner 전용: 마스터 스위치 및 공개 메타데이터 변경
CREATE POLICY workspace_public_settings_update_owner ON workspace_public_settings
FOR UPDATE TO authenticated
USING (has_workspace_role(workspace_id, 'owner'))
WITH CHECK (has_workspace_role(workspace_id, 'owner'));
```

### 2.2 위키 승인 발행본 사이드카 (`wiki_page_publications`)
* **역할**: 사람이 승인한 단 1건의 공개 불변 스냅샷(본문 전문 + 승인된 인용 스니펫) 보관.
* **복합 외래키 불변식**: `FOREIGN KEY (wiki_page_id, workspace_id)`로 테넌트 교차 오염 물리적 차단.
```sql
CREATE TABLE wiki_page_publications (
    wiki_page_id UUID PRIMARY KEY,
    workspace_id UUID NOT NULL,
    published_title TEXT NOT NULL,
    published_content TEXT NOT NULL,          -- 사람이 승인한 마크다운 전문
    published_citations JSONB NOT NULL,        -- 사람이 승인한 인용 스니펫 JSONB 배열
    published_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_by UUID NOT NULL REFERENCES auth.users(id),

    -- [핵심 불변식] 테넌트 오염 원천 방지 복합 FK
    CONSTRAINT fk_wiki_page_publication_tenant
        FOREIGN KEY (wiki_page_id, workspace_id)
        REFERENCES wiki_pages(id, workspace_id)
        ON DELETE CASCADE
);

ALTER TABLE wiki_page_publications ENABLE ROW LEVEL SECURITY;

-- anon + 모든 사용자: 워크스페이스 마스터 스위치가 ON인 발행본만 열람 (진짜 킬스위치)
CREATE POLICY wiki_page_publications_select_public ON wiki_page_publications
FOR SELECT TO anon, authenticated
USING (
    EXISTS (
        SELECT 1 FROM workspace_public_settings s
        WHERE s.workspace_id = wiki_page_publications.workspace_id
          AND s.allow_public_sharing = true
    )
);

-- Editor / Owner: 발행본 등록 및 갱신
CREATE POLICY wiki_page_publications_write_editor ON wiki_page_publications
FOR ALL TO authenticated
USING (has_workspace_role(workspace_id, 'editor'))
WITH CHECK (has_workspace_role(workspace_id, 'editor'));
```

---

## 3. 공개 URL 네임스페이스 및 전역 슬러그 충돌 방지 (Global Collision Prevention)

### 3.1 라우팅 충돌 원인 및 해결
* **문제**: `wiki_pages`의 `slug`는 워크스페이스 내부에서만 고유합니다(`UNIQUE (workspace_id, slug)`).
* 서로 다른 워크스페이스가 동일한 `tenant-isolation-rls` 슬러그를 공개할 수 있으므로, 플랫 URL(`/p/[slug]`)은 전역 충돌을 유발합니다.
* **해결 규격**:
  $$\text{https://nexuswiki.io/p/}\mathbf{[workspace\_slug]}\text{/}\mathbf{[page\_slug]}$$
* **라우팅 계약**:
  1. 라우터는 `workspace_slug`로 `workspace_public_settings`를 조회하여 `allow_public_sharing == true` 여부를 검증.
  2. 통과 시 해당 `workspace_id` 스코프 내에서 `wiki_page_publications`의 `page_slug` 레코드를 1:1로 정확하게 렌더링.

---

## 4. 핵심 비즈니스 규칙 & 수명주기 (Lifecycle Rules)

1. **사전 검증 게이트 (Prerequisite Gate)**:
   * 오직 `wiki_pages.verification_status == 'verified'` 상태인 기술 검증 완료 위키만 공개 신청 가능 (`unverified`/`stale` 차단).
   * 공개 승인 클릭은 기술 검증 상태를 조작하지 않음 (의미 희석 방지).
2. **인용 스니펫 육안 검토 게이트**:
   * 컴파일러가 자동 생성한 인용 구간에 민감 정보(내부 호스트/IP/주석)가 없는지 사람이 모달에서 각 인용 스니펫(5~10줄)을 `[✅ 승인 / ❌ 제외]` 확인해야만 최종 발행.
3. **재발행 트리거 (`updated_at > published_at`)**:
   * 소스 변경/재컴파일로 `wiki_pages.updated_at`이 갱신되어도 외부 게스트는 기존 승인본(`wiki_page_publications`)을 안전하게 열람.
   * 내부 위키 상단에 `[공개 이후 최신 내용이 갱신되었습니다 ➔ 변경사항 검토 및 재발행]` 배너 표시.
   * 재발행 시에도 최초 발행과 동일한 스니펫 육안 검토 모달을 100% 필수 수행.
4. **마스터 킬스위치 (Master Kill Switch)**:
   * 워크스페이스 마스터 스위치가 `OFF`되면 DB RLS가 모든 공개 엔드포인트 조회를 0건으로 즉시 물리적 차단.

---

## 5. 사용자 권한 매트릭스 (Permission Matrix)

| 기능 영역 | 비로그인 게스트 (`/p/[ws]/[page]`) | 워크스페이스 멤버 (`/wiki/[slug]`) |
| :--- | :---: | :---: |
| **공개 위키 본문 및 목차(TOC) 열람** | ✅ 가능 | ✅ 가능 |
| **승인된 원문 인용 스니펫 열람 (`[1]`)** | ✅ 가능 (승인된 5줄 발췌만) | ✅ 가능 (전체 원본 소스 파일까지) |
| **AI 지식 질문 (`Ask`)** | ❌ **전면 미노출 및 차단** | ✅ 가능 |
| **원본 소스 파일 전문 다운로드** | ❌ **불가 (로그인 유도)** | ✅ 가능 |
| **소스 업로드 / 삭제 (비동기 자동 컴파일)** | ❌ **불가 (로그인 유도)** | ✅ 가능 (Editor/Owner) |
| **실패 잡 재시도 (JobStepper Retry)** | ❌ **불가 (로그인 유도)** | ✅ 가능 (Editor/Owner) |
| **마스터 킬스위치 ON/OFF** | ❌ **불가 (로그인 유도)** | ✅ 가능 (Owner) |
