# 워크스페이스 설정 PRD

> **문서 상태**: 리뷰 반영판 (2026-08-17). 이전 "확정(Validated)" 판이 적은 RLS 정책 수·파이프라인 단계 수·초대 계약·역할 변경 UI·운영 지표 단위를 실제 구현과 대조해 정정했다.
> **기능 영역**: 워크스페이스 멤버 로스터·초대, 운영 현황(예산·파이프라인) 조회
> **라우트**: `/w/[workspace_id]/settings`
> **연계 프로토타입**: [`nexuswiki-workspace-settings.html`](nexuswiki-workspace-settings.html)
> **상위 불변 규칙**: [`PRODUCT-INVARIANTS.md`](PRODUCT-INVARIANTS.md)
> **디자인 토큰**: [`nexuswiki-design-system.css`](nexuswiki-design-system.css)

이 문서의 SQL·식별자는 `supabase/migrations/0001`~`0014` 와 `apps/` 에 실재하는 것만 쓴다. 미구현은 **[미구현]**, 새 마이그레이션이 필요하면 **[마이그레이션 필요]**, 스키마는 있으나 화면이 없으면 **[UI 미구현]** 으로 표시한다.

**이 화면은 다른 3개 PRD 와 달리 이미 구현되어 있다.** [`SettingsMembersPanel.tsx`](../../../apps/dashboard/components/SettingsMembersPanel.tsx) · [`MembersList.tsx`](../../../apps/dashboard/components/MembersList.tsx) · [`InviteForm.tsx`](../../../apps/dashboard/components/InviteForm.tsx) · [`OperationsPanel.tsx`](../../../apps/dashboard/components/OperationsPanel.tsx) 가 이 문서의 정본이다. 문서와 코드가 어긋나면 **코드가 이긴다.**

---

## 0. 이전 판에서 정정한 것

| # | 이전 판 주장 | 실제 | 근거 |
| --- | --- | --- | --- |
| 1 | "RLS **38개** 보안 정책 무결성 확인" | **27개**. 그리고 **RLS 상태 위젯은 화면에 존재하지 않는다** | `grep -c "create policy" supabase/migrations/*.sql` = 27 (`0004` 23 + `0005` 3 + `0009` 1) |
| 2 | "**3대** 비동기 파이프라인 큐" | **5단계** — `parse` · `compile` · `link_sync` · `embed` · `conflict_check` | [`jobs.py:29`](../../../apps/api/src/api/routers/jobs.py) `CHAIN_ORDER` |
| 3 | "멤버 초대장 발송", "가입 승인 파이프라인" | **이메일을 보내지 않는다.** 이미 가입한 사용자만 즉시 멤버로 추가하고, 미가입 이메일은 `NW404` 로 거부한다 | [`0014`](../../../supabase/migrations/0014_workspace_roster_and_invite.sql) `invite_workspace_member` |
| 4 | "관리자(**Owner/Editor**)는 팀원을 초대" | **owner 전용**. `has_workspace_role(p_workspace_id, 'owner')` 실패 시 `42501` | `0014:78` |
| 5 | "초기 역할 드롭다운 (`editor`/`viewer`)" | **3종**(`owner`·`editor`·`viewer`), 기본값 `viewer` | `InviteForm.tsx` `ROLE_OPTIONS` · `DEFAULT_ROLE` |
| 6 | "액션 드롭다운: 역할 변경, 퇴장 처리" | **역할 변경 UI 는 없다.** 제거만 있고, `···` 드롭다운이 아니라 아이콘 버튼 + 확인 다이얼로그다 | `MembersList.tsx` |
| 7 | "컬럼: 이름, 이메일, 역할 뱃지, 가입 일시, You 인디케이터" | 로스터 RPC 는 `user_id`·`email`·`role`·`created_at` 만 준다. **이름 컬럼이 스키마에 없고**, 화면은 이메일 + 역할 뱃지만 그린다 | `0014` `workspace_members_list` |
| 8 | 운영 현황 라우트 `/operations` | 설정 페이지 **안의 탭**이다. 별도 라우트가 없다 | `apps/dashboard/app/w/[workspaceId]/settings/page.tsx` |
| 9 | 예산 "한도 $100.00 / 사용 $34.20" | 단위는 **micro-dollar 정수**(`monthly_budget_micros`, 기본값 `5000000` = $5). 표시 전용이며 `authoritative: false` | `0009:88`, [`jobs.py:224`](../../../apps/api/src/api/routers/jobs.py) |
| 10 | §3.4 외부 공개 킬스위치를 이 화면 요구사항으로 기술 | `workspace_public_settings` 는 **[미구현]**. 계약은 [`public-sharing-prd.md`](public-sharing-prd.md) 가 소유한다 | 실재 테이블 10개에 없음 |
| 11 | 브레드크럼 `엔지니어링 코어 / 워크스페이스 설정` | 3계층 잔재. 실제 화면은 `PageHeader` 제목 "설정" 하나다(불변식 §1) | `settings/page.tsx:42` |
| 12 | 탭 라벨에 이모지 `👥` · `⚡` | 불변식 §7.2 **Zero Emojis** 위반. 실제 라벨은 `멤버` · `운영 현황` | `SettingsMembersPanel.tsx:83,98` |
| 13 | §4.1 에 `#FFFFFF` · `#F8FAFC` · `#E2E8F0` 직접 지정 | 불변식 §7.1 위반. 색은 토큰만 쓴다 | `nexuswiki-design-system.css` |
| 14 | 프로토타입 링크가 v1 경로(`docs/design-systems/workspace-settings-preview.html`) | v2 정본은 `nexuswiki-workspace-settings.html` | `a46795f` |
| 15 | "`editor`: 원문 소스 업로드/**삭제**" | **삭제는 owner 전용**이다(`raw_sources_delete_owner`). editor 는 INSERT 만 | `0004:217-223` |

---

## 1. 목적

워크스페이스는 이 제품의 테넌트 경계이고, 그 경계는 앱이 아니라 **Postgres RLS 가 강제한다**. 이 화면이 하는 일은 두 가지뿐이다.

1. **누가 이 경계 안에 있는가**를 보여주고 바꾼다 — 로스터 조회, owner 의 초대·제거.
2. **경계 안에서 백그라운드가 무엇을 하고 있는가**를 보여준다 — 이번 달 LLM 비용과 5단계 파이프라인 적체.

두 번째는 조회 전용이다. 이 화면에는 잡을 다시 돌리는 버튼이 없다(불변식 §2). 실패한 잡의 재시도는 `JobStepper` 가 소유한다.

---

## 2. 역할 계약 — 실측

역할은 `workspace_members.role` 의 `check (role in ('owner','editor','viewer'))` 3종이다(`0001`). 아래 표는 **실재하는 RLS 정책과 RPC 가드에서 역으로 뽑은 것**이며, "관리 화면이 이렇게 보여야 한다"는 희망이 아니다.

| 능력 | owner | editor | viewer | 강제 지점 |
| --- | :---: | :---: | :---: | --- |
| 워크스페이스 조회 | O | O | O | `workspaces_select_member` |
| 워크스페이스 이름 수정 · 삭제 | O | X | X | `workspaces_update_owner` · `workspaces_delete_owner` — **[UI 미구현]** |
| 멤버 로스터 조회 | O | O | O | `workspace_members_list` (`is_workspace_member`) |
| 멤버 초대 | O | X | X | `invite_workspace_member` → `42501` |
| 멤버 역할 변경 | O | X | X | `workspace_members_update_owner` — **[UI 미구현]** |
| 멤버 제거 | O | X | X | `workspace_members_delete_owner` + `protect_owner_membership` 트리거 |
| 원문 소스 업로드 | O | O | X | `raw_sources_insert_editor` |
| 원문 소스 삭제 | O | X | X | `raw_sources_delete_owner` |
| parse 잡 인큐 | O | O | X | `enqueue_source_job` → `42501` |
| 실패 잡 재시도 · 취소 | O | O | X | `retry_dead_job` · `request_job_cancel` (`0009:427`, `0009:361`) |
| 프롬프트 오버라이드 | O | O | X | `prompt_templates_insert_editor` · `_update_editor` |
| 운영 현황 조회 | O | O | X | `_require_operations_role` → `has_workspace_role(…, 'editor')` |
| 위키 열람 · Ask · 그래프 | O | O | O | `wiki_pages_select_member` 외 `_select_member` 계열 |

⚠️ **owner 자신은 스스로를 제거하거나 강등할 수 없다.** `protect_owner_membership` 트리거(`0004:146`)가 UPDATE/DELETE 를 DB 레벨에서 막는다. 화면은 owner 자신의 행에 제거 버튼을 아예 그리지 않아, 눌러야만 실패를 알게 되는 죽은 버튼을 만들지 않는다(`MembersList.tsx:151`).

---

## 3. 화면 요구사항

### 3.1 헤더와 탭

* **헤더**: 제목 `설정`, 설명 `워크스페이스 멤버와 운영 상태를 관리합니다.` — `PageHeader` 프리미티브.
  * 브레드크럼은 없다. 이전 판의 `엔지니어링 코어 / 워크스페이스 설정` 은 3계층 정보구조의 잔재이므로 폐기한다(불변식 §1).
* **탭 2종**: `멤버` · `운영 현황`. **이모지를 붙이지 않는다**(불변식 §7.2).
  * `운영 현황` 탭은 `currentRole` 이 `owner`·`editor` 일 때만 렌더링한다.
  * ⚠️ 탭 숨김은 **UX 방어선일 뿐**이다. 실제 차단은 API 의 `_require_operations_role` 이 한다 — 대시보드 판정에 맡기면 직접 API 를 호출해 비용·잡 집계를 빼가는 경로가 생긴다(`settings/page.tsx:31` 주석).
  * 멤버십 조회가 실패하거나 행이 없으면 **보수적으로 `viewer` 로 처리**한다(`membership?.role ?? "viewer"`).
* **키보드**: `role="tablist"` + `ArrowLeft`/`ArrowRight`/`Home`/`End` 로 탭 이동, `tabIndex` 로 로빙 포커스.

### 3.2 [탭 1] 멤버

#### 3.2.1 로스터

* 데이터 원천은 **[구현됨]** `workspace_members_list(p_workspace_id)` RPC 다. `auth.users` 는 PostgREST 에 노출되지 않으므로(`config.toml` 의 `schemas = ["public","graphql_public"]`) `SECURITY DEFINER` 로만 이메일을 얻을 수 있다.
* 멤버가 아닌 호출자에게는 **에러가 아니라 0행**을 돌려준다. 화면은 이를 "빈 목록"으로 그대로 렌더한다.
* 행 구성: **이메일** + **역할 뱃지**(`소유자`·`편집자`·`뷰어`), owner 에게만 제거 버튼.
  * ⚠️ **표시 이름 컬럼은 없다.** `workspace_members` 에도 `auth.users` 조회 결과에도 이름이 없다. 이름을 쓰려면 프로필 테이블이 필요하다 — **[마이그레이션 필요]**, §6 미해결 참조.
  * ⚠️ **가입 일시는 RPC 가 `created_at` 으로 주지만 화면이 렌더하지 않는다.** 프로토타입은 3열 표(멤버/역할/가입 일시)를 그린다. 둘 중 하나로 맞춰야 한다 — §6 참조.
* 초기 조회 중에는 행 3개짜리 스켈레톤(`aria-busy="true"`)을 보여준다. 불확정 스피너를 쓰지 않는다.
* 조회 실패 시 `role="alert"` 로 `멤버 목록을 불러오지 못했습니다.`

#### 3.2.2 멤버 제거

* 아이콘 전용 버튼(44×44px + `aria-label="제거: {email}"`) → 확인 다이얼로그.
* 확인 문구는 계약이다. **한 글자도 바꾸지 않는다**:
  > `제거: {email}님을 이 워크스페이스에서 제거하시겠습니까? 소유한 콘텐츠는 유지되지만 접근 권한이 즉시 사라집니다.`
* ⚠️ **삭제 결과 판정은 `error` 가 아니라 반환 행 수로 한다.** RLS `USING` 에 막힌 DELETE 는 예외 없이 0행으로 돌아오므로(`CLAUDE.md` > Error Handling), `.select()` 로 삭제된 행을 되받아 `data.length === 0` 을 실패로 처리해야 한다. `error` 만 보면 차단과 성공이 똑같이 성공으로 보인다.

#### 3.2.3 초대 폼

* 필드: 이메일(`type="email"`, 정규식 검증) + 역할 `Select`(3종, 기본 `viewer` — 최소 권한).
* 제출 버튼은 **이메일 형식이 틀렸을 때만** 비활성이다. 역할 선택은 비활성 사유가 아니다.
* RPC 는 `invite_workspace_member(p_workspace_id, p_email, p_role)`. SQLSTATE 별 문구도 계약이다:

| SQLSTATE | 의미 | 문구 |
| --- | --- | --- |
| `NW409` | 이미 멤버 | `이미 워크스페이스 멤버입니다.` |
| `NW404` | 미가입 이메일 | `가입된 사용자를 찾을 수 없습니다 — 초대 대상이 먼저 NexusWiki 계정을 만들어야 합니다.` |
| `42501` | 비-owner 호출 | `권한이 없습니다.` |
| 그 외 | — | `초대를 보내지 못했습니다.` |

* **실패 시 폼을 비우지 않는다.** 성공 시에만 이메일을 비우고 역할을 `viewer` 로 되돌린 뒤 `onInvited()` 로 로스터를 리마운트(key 증가)한다.
* ⚠️ **"초대장 발송"이 아니다.** 이메일이 나가지 않고, 미가입자는 스스로 계정을 만들어야 한다. `NW404` 는 owner 전용 표면에서 이메일 등록 여부를 노출하는 트레이드오프를 **의도적으로 수용한 것**이다(`0014:56-58`). CTA 문구를 "초대장 발송"으로 적으면 사용자가 받은편지함을 기다린다.
* ⚠️ **[불일치] 초대 폼이 owner 가 아닌 사용자에게도 보인다.** `SettingsMembersPanel.tsx:120-128` 이 `currentRole` 을 갖고 있으면서도 초대 섹션을 무조건 렌더한다. `InviteForm.tsx` 주석은 "정상 흐름에서는 owner 가 아닌 사용자에게 이 폼 자체를 숨기는 것이 우선"이라고 전제하고 `42501` 분기를 마지막 방어선으로만 뒀는데, 그 전제가 성립하지 않는다. **`canInvite = currentRole === "owner"` 로 게이트해야 한다** — §6 참조.

### 3.3 [탭 2] 운영 현황 — owner/editor 전용

단일 엔드포인트 `GET /workspaces/{workspace_id}/operations` 하나로 그린다. 탭 진입 시 **한 번만** 요청하고 **자동 폴링은 의도적으로 없다**. 갱신은 `운영 현황 새로고침` 버튼이다.

#### 3.3.1 이번 달 사용량

* 응답의 `budget` 은 전부 **micro-dollar 정수**다. 화면에서 `1_000_000` 으로 나눠 USD 로 표시한다.
* `cap_micros` 는 `workspaces.monthly_budget_micros`(기본 `5000000` = $5, `>= 0` CHECK).
* ⚠️ **`authoritative: false` 는 계약의 일부다.** 권위 있는 상한 판정은 `enqueue_source_job` SQL 이 하고, 초과 시 `NW402` 로 거부한다(`0010`). 이 화면 수치는 표시용이며 **집행 지점이 아니다.**
* `truncated` 는 `usage_events` 를 1,000행에서 끊었다는 뜻이다. true 면 경고 문구를 함께 띄운다.
* 상태별 문구:

| 조건 | 표시 |
| --- | --- |
| `cap_micros == 0` | `예산이 설정되지 않았습니다.` (프로그레스 바 미표시) |
| `spent_micros == 0` | `이번 달 사용 기록이 없습니다.` |
| `spent > cap` | `이번 달 예산을 초과했습니다. 새 작업 등록이 제한될 수 있습니다.` |
| `cap * 0.8 <= spent <= cap` | `이번 달 예산에 가깝습니다.` |
| `truncated` | `표시할 수 있는 사용 기록이 많아 합계가 일부만 반영되었을 수 있습니다. 정확한 한도 판단은 작업 등록 시 적용됩니다.` |

* ⚠️ **일 평균 사용액·다음 초기화일·"예산 상태: 여유" 뱃지는 응답에 없다.** 프로토타입이 그린 것이며 계산 근거가 없다. 넣으려면 `month_start` 로부터 파생 규칙을 먼저 정의해야 한다 — §6 참조.

#### 3.3.2 파이프라인 상태

* **5행 고정**, 순서는 서버가 소유한다:

| `type` | `step_label` |
| --- | --- |
| `parse` | 원문 파싱 |
| `compile` | 위키 컴파일 |
| `link_sync` | 링크 동기화 |
| `embed` | 임베딩 |
| `conflict_check` | 지식 충돌 검사 |

* ⚠️ **라벨을 클라이언트가 만들지 않는다.** 응답이 `type` 과 `step_label` 을 함께 주는 이유가 이것이다 — 클라이언트가 `type` 문자열을 매칭하면 새 단계가 추가될 때 조용히 빈 라벨이 된다(`jobs.py:31` 주석). 이전 판의 `원문 소스 수집 & 청킹` · `위키 자동 컴파일러` · `벡터 임베딩 생성` 은 **어디에도 없는 라벨**이다.
* 열은 `대기`(`queued`) · `실행 중`(`running`) · `실패`(`dead`) 3종. `null` 이면 `집계 불가`, `dead > 0` 이면 `실패한 작업 N건`.
* 5행 전부 0 이면 `처리 중이거나 대기 중인 작업이 없습니다.`
* 표는 `overflow-x: auto` 컨테이너 안에서만 가로 스크롤한다(`min-w-[560px]`). 페이지 자체는 640px 이하에서 가로로 스크롤되지 않는다(불변식 §7.3).
* 하단에 `마지막 갱신: {observed_at}`.

#### 3.3.3 삭제된 항목 — RLS 상태 위젯

⚠️ **`● 38개 정책 · 100% 격리 정상` 은 요구사항에서 제거한다.** 세 가지가 전부 틀렸다.

1. **수치가 틀렸다** — 정책은 27개다.
2. **엔드포인트가 없다** — `/operations` 응답에 정책 관련 필드가 없고, `pg_policies` 를 사용자 경로에서 읽을 방법도 없다.
3. **의미가 없다** — 정책 개수는 격리가 **작동한다**는 증거가 아니다. 개수가 맞아도 `USING` 절이 틀리면 격리는 깨진다. "100% 격리 정상"이라는 초록 뱃지는 검증하지 않은 안전 신호이고, 이런 뱃지는 실제 사고 때 사람의 판단을 늦춘다.

격리 검증은 화면이 아니라 마이그레이션 테스트가 할 일이다.

### 3.4 이 화면이 소유하지 않는 것

* **외부 웹 공개 킬스위치 · 공개 식별자 · 공개 사이트 이름/소개** → [`public-sharing-prd.md`](public-sharing-prd.md) 가 소유한다. `workspace_public_settings` · `wiki_page_publications` 는 둘 다 **[미구현]** 이다(불변식 §5).
  * 설정 화면에 진입점을 두는 것 자체는 자연스럽지만, **계약을 여기 복제하지 않는다.** 같은 규칙을 두 곳에 적으면 한쪽만 고쳐질 때 어긋난다.
  * 공개 URL 이 의존하는 슬러그는 **[마이그레이션 필요]** 다 — `workspaces.slug` 정본 + 사이드카 복제로 확정됐다(§6-6).
* **실패 잡 재시도** → `JobStepper` 가 소유한다. 운영 현황은 조회 전용이다.
* **워크스페이스 이름 변경 · 삭제** → RLS 정책은 있으나 **[UI 미구현]**. 이번 마일스톤 범위인지 §6 에서 결정한다.

---

## 4. 데이터베이스 계약

### 4.1 멤버 로스터

```sql
select * from public.workspace_members_list(:workspace_id);
-- returns (user_id uuid, email text, role text, created_at timestamptz)
```

`SECURITY DEFINER`. 함수 본문의 `is_workspace_member(p_workspace_id)` 가 접근을 판정하며, 멤버가 아니면 **예외가 아니라 0행**이다. `authenticated` 전용 — `anon` 은 EXECUTE 가 회수되어 있다.

### 4.2 멤버 초대

```sql
select * from public.invite_workspace_member(:workspace_id, :email, :role);
-- 42501: 비-owner / 22023: 알 수 없는 역할 / NW404: 미가입 / NW409: 이미 멤버
```

역할 값은 **서버가 다시 검증한다**. 클라이언트 `Select` 가 3값만 노출하는 것과 무관하게 함수는 입력을 신뢰하지 않는다.

### 4.3 멤버 제거

```sql
delete from public.workspace_members
where workspace_id = :workspace_id
  and user_id = :user_id
returning *;   -- ⚠️ returning 없이는 차단(0행)과 성공을 구분할 수 없다
```

`workspace_members_delete_owner` 정책과 `protect_owner_membership` 트리거를 동시에 통과해야 한다.

### 4.4 운영 스냅샷

```sql
-- ① 예산 상한
select monthly_budget_micros from public.workspaces where id = :workspace_id;

-- ② 이번 달 사용액 (limit 1000 — 초과 시 truncated = true)
select cost_micros, occurred_at
from public.usage_events
where workspace_id = :workspace_id
  and occurred_at >= :month_start
limit 1000;

-- ③ 파이프라인 적체 (서버에서 type × status 로 집계, 원 행은 응답에 없다)
select type, status from public.jobs where workspace_id = :workspace_id;
```

셋 다 **요청자 JWT** 로 실행한다. `service_role` 을 쓰지 않는다 — 이 경로에 `service_role` 을 쓰는 순간 27개 격리 정책이 전부 장식이 된다.

### 4.5 역할 게이트

```sql
select public.has_workspace_role(:workspace_id, 'editor');
```

`false` 면 API 가 403 을 낸다. 응답 본문은 allowlist 로만 조립하며 **원문·공급자 정보·usage metadata·잡 오류를 담지 않는다**(`jobs.py:234-238`).

---

## 5. 프로토타입 정정 목록

`nexuswiki-workspace-settings.html` 에 남은 불일치다. 시안이 정답이 아닌 항목이므로 시안 쪽을 고친다.

| 위치 | 현재 | 고칠 값 | 사유 |
| --- | --- | --- | --- |
| 운영 현황 | `● 38개 정책 · 100% 격리 정상` | **블록 전체 삭제** | §3.3.3 |
| 파이프라인 | 3행(`원문 소스 수집 & 청킹`·`위키 자동 컴파일러`·`벡터 임베딩 생성`) | 5행 + 서버 `STEP_LABELS` | §3.3.2 |
| 초대 폼 | `멤버 초대장 발송`, `초대장을 받은 구성원은…` | 발송 표현 제거 | §3.2.3 |
| 초대 역할 | `editor` · `viewer` 2종 | 3종(기본 `viewer`) | `ROLE_OPTIONS` |
| 권한 모달 | `EDITOR … 위키 재컴파일 … 관리합니다` | 재컴파일 문구 삭제 | **불변식 §2 위반** — 수동 재컴파일은 존재하지 않는다 |
| 권한 모달 | `EDITOR … 소스 업로드` | 삭제 권한이 editor 에 없음을 명시 | §2 표 |
| 브레드크럼 | `넥서스 SaaS 팀 / 워크스페이스 설정` | 유지 가능(2계층) | — |
| LNB 카테고리 | `대상` · `지도` | `엔티티` · `맵` | `GraphLensFilter.tsx` (HANDOFF 기재 항목) |
| LNB | `즐겨찾기` · `최근 본 위키` | 저장소 미정 — §6 | workspace-home PRD 와 동일 항목 |
| 예산 카드 | `일 평균 사용 $1.14` · `다음 초기화 09.01.` · `예산 상태: 여유` | 근거 정의 전까지 제거 | §3.3.1 |
| 외부 웹 공개 | 전체 섹션 | `public-sharing-prd.md` 확정 전까지 `[미구현]` 표기 | §3.4 |

---

## 6. 미해결 결정

1. **초대 폼 owner 게이트** — `SettingsMembersPanel` 이 `currentRole` 을 갖고 있으면서 쓰지 않는다. 코드 한 줄이지만 **PRD 가 아니라 코드 변경**이므로 별도 태스크로 뺀다. *권고: 게이트한다.* 비-owner 에게 폼을 보여주고 제출 후에야 `권한이 없습니다.` 를 띄우는 것은 §3.2.2 의 "죽은 버튼을 만들지 않는다" 원칙과 정면으로 어긋난다.
2. **가입 일시 표시 여부** — RPC 는 `created_at` 을 주고 시안은 열을 그리는데 구현은 렌더하지 않는다. *권고: 표시한다.* 데이터가 이미 오고 있고, 로스터에서 "언제부터 멤버인지"는 제거 판단에 쓰인다.
3. **표시 이름** — 이메일만으로 로스터를 읽는 것이 충분한가. 필요하면 `user_profiles` 신설이 필요하다(**[마이그레이션 필요]**). *권고: 이번 마일스톤 제외.* 이메일이 이미 고유 식별자 역할을 한다.
4. **역할 변경 UI** — `workspace_members_update_owner` 정책이 이미 허용한다. 구현하면 §2 표의 `[UI 미구현]` 이 사라진다. `protect_owner_membership` 이 owner 자기 강등을 막으므로 owner 행은 비활성이어야 한다.
5. **워크스페이스 이름 변경 · 삭제 UI** — 정책은 있고 화면이 없다. 삭제는 `owner_id … on delete restrict` 와 맞물리므로 문구를 신중히 정해야 한다.
6. ~~`workspaces.slug`~~ — **2026-08-17 결정 완료.** `workspaces.slug` 정본 + `workspace_public_settings` 복제. 계약은 [`public-sharing-prd.md`](public-sharing-prd.md) §2.0, 근거는 `checklists.json > decisions.workspace_slug`. 내부 라우트는 당분간 `/w/[workspaceId]`(UUID) 유지.
7. **즐겨찾기 · 최근 본 위키 저장소** — 제외 / `user_wiki_bookmarks` 신설 / `localStorage` 중 택일. (workspace-home · wiki-document-reader PRD 와 동일 항목)
8. **예산 파생 지표** — 일 평균·소진 예상일을 넣을지. 넣는다면 `month_start` 기준 경과일로 계산하고, `truncated: true` 일 때는 표시하지 않아야 한다.

---

## 7. 검증 계획

| # | 항목 | 검증 기준 |
| --- | --- | --- |
| 1 | 역할 게이트 | `viewer` 세션에서 `운영 현황` 탭이 렌더되지 않고, 같은 세션이 `/workspaces/{id}/operations` 를 직접 호출하면 403 |
| 2 | 로스터 격리 | 비멤버 JWT 로 `workspace_members_list` 호출 시 **에러가 아니라 0행** |
| 3 | 초대 오류 분기 | 미가입 이메일 → `NW404`, 기존 멤버 → `NW409`, 비-owner 직접 RPC → `42501`. 각 문구가 §3.2.3 표와 문자 단위로 일치 |
| 4 | 제거 차단 판정 | 비-owner 가 DELETE 시도 시 `error === null` + 0행 → 화면이 실패로 처리하는지 |
| 5 | owner 자기 제거 | owner 자신의 행에 제거 버튼이 렌더되지 않는지. 트리거가 UPDATE/DELETE 를 거부하는지 |
| 6 | 파이프라인 행 수 | 응답 `pipeline` 이 항상 5행이고 순서가 `CHAIN_ORDER` 와 같은지. 라벨을 클라이언트가 만들지 않는지 |
| 7 | 예산 단위 | `cap_micros: 5000000` → `$5.00` 으로 표시되는지. `cap_micros: 0` 에서 프로그레스 바가 사라지는지 |
| 8 | 응답 누출 | `/operations` 응답에 원문·공급자·usage metadata·`last_error` 가 없는지 |
| 9 | 반응형 | 640px 이하에서 페이지 가로 스크롤 0. 파이프라인 표만 자체 컨테이너에서 스크롤 |
| 10 | 토큰 · 이모지 | 렌더링된 화면에 이모지 0개, 팔레트 밖 색 0개 |
