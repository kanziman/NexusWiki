# NexusWiki 디자인 시스템

## 의도

NexusWiki의 인증, 워크스페이스, 소스 관리, 문서 리더 화면을 같은 제품처럼 연결하는 최소 디자인 시스템이다. 순백색 작업 캔버스 위에 신뢰 가능한 엔지니어링 정보를 조밀하게 배치하고, 청록색은 현재 맥락과 단일 핵심 동작에만 사용한다.

## 토큰

```css
:root {
  --bg: oklch(1 0 0);
  --surface: oklch(.982 .004 247);
  --fg: oklch(.208 .033 264);
  --muted: oklch(.554 .033 258);
  --border: oklch(.928 .012 255);
  --accent: oklch(.58 .11 190);
  --soft: oklch(.965 .025 190);
  --good: oklch(.63 .14 155);
  --danger: oklch(.57 .205 20);
  --shadow: 0 18px 46px oklch(.208 .033 264 / .10);
}
```

| 역할 | 사용 규칙 |
| --- | --- |
| `--bg` | 문서·폼·모달의 기본 배경 |
| `--surface` | LNB, 테이블 헤더, 비활성 보조 영역 |
| `--fg` / `--muted` | 본문·제목 / 보조 정보·메타데이터 |
| `--accent` | 활성 내비게이션, 선택, 화면당 핵심 CTA 1개 |
| `--good` / `--danger` | 검증 완료·정상 / 삭제·실패 상태에만 사용 |

## 타이포그래피

- Display: `Plus Jakarta Sans`, `Pretendard`, system-ui, sans-serif
- Body: `Pretendard`, `Apple SD Gothic Neo`, system-ui, sans-serif
- Mono: `JetBrains Mono`, ui-monospace, monospace

| 역할 | 기준 |
| --- | --- |
| 페이지 제목 | 28–40px, 800, 약한 자간 축소 |
| 섹션 제목 | 14–20px, 800 |
| 본문 | 14–15px, 1.65–1.8 줄간격 |
| 메타·캡션 | 10–12px, `--muted` |
| 수치·상태·식별자 | 10–12px, Mono |

## 레이아웃

- 데스크톱 앱 화면: 264px LNB + 유동형 콘텐츠 캔버스.
- 문서 리더: 콘텐츠 폭 780–840px를 우선하고, 오른쪽 목차는 닫을 수 있어야 한다.
- 상단바: 높이 64–66px, 흰색 배경, 하단 1px `--border`.
- 콘텐츠: 데스크톱 좌우 42px, 모바일 14–20px 패딩.
- 모서리: 6px, 8px, 10px, 14px만 사용한다. 그림자는 플로팅 메뉴·모달·강조 카드에 한정한다.

## 컴포넌트

### 버튼

- 기본 버튼: 흰 배경, `--border` 테두리, 8px 모서리, 12px·800.
- Primary 버튼: `--accent` 배경과 흰 전경색. 같은 화면에 한 개만 둔다.
- 모바일의 모든 주요 조작 버튼은 최소 44px 높이를 보장한다.
- 호버는 배경 또는 테두리만 바꾸며 텍스트 대비를 낮추지 않는다.

### 폼

- 입력 필드: 흰 배경, 1px 테두리, 8px 모서리, 최소 39–42px 높이.
- 포커스: `--accent` 테두리와 명확한 포커스 링.
- URL 슬러그, 상태 코드, 금액처럼 구조가 중요한 입력은 Mono 메타데이터로 보조한다.

### 상태와 배지

- 검증 완료: 연한 녹색 배경과 `--good` 전경색.
- 역할: `owner`만 `--soft` + `--accent`, 나머지는 절제된 중립색.
- 위험 동작은 `--danger`를 텍스트 또는 테두리에만 사용하고, 기본 CTA와 경쟁시키지 않는다.
- 공개·재발행·비동기 작업 상태는 문장형 배너로 이유와 다음 행동을 함께 제시한다.

### 내비게이션

- 활성 LNB: `--soft` 배경과 `--accent` 전경색.
- 접힌 LNB는 아이콘만 남기고, 호버 시 레이블을 제공한다.
- 문서 목차는 활성 섹션에만 청록색 2px 표시를 쓴다.

### 표와 목록

- 제목 우선 가로 행을 사용하고, 메타데이터는 제목 아래에 둔다.
- 관련 항목의 비교가 필요한 데스크톱에서만 테이블을 쓴다.
- 900px 이하에서는 테이블 행을 카드로 전환한다. 열을 억지로 숨기거나 페이지 가로 스크롤로 해결하지 않는다.

## 상호작용 규칙

- 메뉴, 모달, 서랍은 `Esc`로 닫히고 명확한 닫기 버튼을 제공한다.
- 공개 발행은 검증 완료 → 인용 스니펫 검토 → 승인 발행의 순서를 유지한다.
- OAuth 신규 사용자는 인증 후 메인 화면 셸에서 워크스페이스 온보딩을 진행한다.
- 완료·저장·복사 동작은 버튼 또는 인접한 피드백 텍스트로 결과를 즉시 알린다.

## 반응형 기준

| 구간 | 행동 |
| --- | --- |
| 1600px 이상 | LNB, 콘텐츠, 인스펙터를 함께 표시 |
| 901–1599px | 콘텐츠 폭을 우선하고 보조 패널은 접을 수 있게 구성 |
| 641–900px | LNB를 숨기고 표를 카드로 전환 |
| 640px 이하 | 페이지 가로 스크롤 금지, 주요 조작 44px 이상, 보조 메타는 상세 화면으로 이동 |

자세한 데이터 목록 규칙은 [responsive-layout-rules.md](responsive-layout-rules.md)를 따른다.

## 적용 대상

이 문서의 실행 가능한 형태는 [nexuswiki-design-system.css](nexuswiki-design-system.css)이며, 아래 6개 화면이 모두 이 파일을 `<link>` 로 불러온다. 각 HTML 의 `<style>` 에는 그 화면 고유 레이아웃만 남긴다.

- `nexuswiki-google-auth.html` — 앱 셸이 없는 유일한 화면(토큰·리셋·버튼·폼만 사용)
- `nexuswiki-workspace-home.html`
- `nexuswiki-workspace-settings.html`
- `nexuswiki-source-management.html`
- `nexuswiki-wiki-document-reader.html`
- `nexuswiki-ask-conversation.html`

## 클래스 이름 규약

셸 컴포넌트는 `apps/dashboard/components/` 의 React 컴포넌트로 그대로 넘어간다. 축약어를 쓰지 않는 이유가 이것이다.

| 역할 | 클래스 | 대응 컴포넌트 |
| --- | --- | --- |
| LNB | `.sidebar` | `NavShell.tsx` |
| 워크스페이스 스위처 | `.switcher` | `WorkspaceSwitcher.tsx` |
| 상단바 | `.topbar` | — |
| 내비 항목 / 하위 트리 | `.nav-item` / `.nav-tree` | — |
| 콘텐츠 캔버스 | `.workspace` | — |

`.brand` 는 제품 로고 락업(google-auth)만 뜻한다. 워크스페이스 스위처와 혼동하지 않는다.

## 정리 TODO

- [x] 각 화면의 중복 CSS를 공통 토큰과 컴포넌트 규칙으로 통합한다. — 인라인 합계 76,591 → 52,732 bytes, 공용 CSS 16,571 bytes
- [x] LNB 아이콘을 모두 단색 SVG로 통일한다. — reader 의 글리프(`☆ ◷ ! ↥ □`)와 `nth-of-type` 매칭 제거
- [x] 375px·768px·1280px·1600px 에서 공통 컴포넌트를 시각 검증한다. — 6화면 × 5구간 `scrollWidth == clientWidth` 확인
- [ ] 상태 색상과 포커스 링의 대비를 컴포넌트별로 점검한다. — 아직 수치 측정 안 함
- [ ] `.section-head` 가 workspace-home 과 workspace-settings 에서 서로 다르게 정의돼 있다. 같은 컴포넌트인지 판단 후 통합하거나 이름을 분리한다.
- [ ] source-management 는 640px 이하에서 "연결된 위키 문서" 열을 `display:none` 으로 숨긴다. §표와 목록의 "열을 억지로 숨기지 않는다"와 어긋나므로 PRD 리뷰에서 결론을 낸다.

## 다음 단계

CSS 정리는 끝났다. 이제 화면별 PRD 를 하나씩 리뷰하며, 위 미해결 TODO 3건(상태 대비 측정, `.section-head` 통합, 모바일 열 숨김)을 해당 화면 차례에 함께 판정한다.
