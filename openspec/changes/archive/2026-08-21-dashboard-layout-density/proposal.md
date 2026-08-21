## Why

디자인 리뷰에서 나온 지적은 "화려함이 부족하다"가 아니라 **"모든 화면이 같은 작은 캔버스 위에 놓인 균일한 템플릿처럼 보인다"** 였다. 코드를 확인하니 인상이 아니라 구조적 원인이 셋 있다.

1. **본문 폭이 좁고 제각각이다.** `.content`는 `width: min(1120px, 100%); margin: 0 auto`라 1920px 화면에서 좌우로 각 268px씩 비운다. 게다가 값이 화면마다 다르다 — 홈·위키 `1120`, 설정·백로그 `1180`, 소스 `1320`. 기존 CSS 주석은 *"각 프로토타입에서 옮겨온 값이라 통일할 근거가 없어 그대로 둔다"* 고 적혀 있다. 이번 리뷰가 그 근거다.
2. **메타 텍스트가 읽기에 너무 작다.** `.badge`가 `600 10px var(--font-mono)`다. 정보 밀도가 낮아 제품이 미완성처럼 보이는 원인이며, 리뷰의 "작은 회색 배지가 많이 겹쳐 있다"는 지적과 뿌리가 같다.
3. **같은 상태를 화면마다 다른 말로 부른다.** `verification_status = 'verified'` 하나를 `KnowledgeGrid`는 "검증 완료", `WikiLibrary`는 "검증됨"으로 표시한다. 이중 Citation이 제품의 존재 이유인데 신뢰 상태 어휘가 화면마다 갈리면 그 신뢰 표시 자체가 흔들린다.

⚠️ 리뷰 지적 중 둘은 코드와 어긋나 이 change에서 재정의했다.
- "상태 배지의 색만으로 의미를 전달하지 말라" → 이미 `dashboard-design-consistency`의 `Shared state and control language`가 *"using text in addition to color"* 를 요구하고 있고 구현도 준수한다. 남은 공백은 색이 아니라 **어휘 일관성과 가독 크기**다.
- "상단 전역 행동을 소스 추가와 질문 시작으로 제한하라" → `WorkspaceShell`의 topbar는 이미 그 둘뿐이다. 새로 제한할 것이 없으므로 **회귀 방지 요구사항으로만 명문화**한다.

## What Changes

- **본문 폭을 1280px 단일값으로 통일한다.** 홈·위키 `1120`, 설정·백로그 `1180`, 소스 `1320`의 3중 체계를 없앤다. 모든 목적지가 같은 좌우 경계선을 공유한다.
- **본문·메타 타이포 스케일을 한 단계 올린다.** 배지를 포함한 상태 텍스트에 가독 최소 크기를 보장한다.
- **상태 어휘를 목적지 간에 단일화한다.** 같은 `verification_status` 값은 어느 화면에서든 같은 라벨로 표시된다.
- **반복되는 영문 대문자 모노스페이스 eyebrow를 감축한다.** 현재 6개 워크스페이스 화면이 각각 하나씩 갖고 있어 매 화면 반복된다. 중복되지 않는 맥락을 실제로 전달하는 자리만 남긴다.
- **반복되던 도입부를 깨뜨린다.** eyebrow 감축만으로도 여섯 화면이 "제목 → 짧은 설명 → 작은 표"로 똑같이 시작하던 리듬이 무너진다. ⚠️ 그 이상(각 목적지가 주 작업 대상에 시각적 비중을 갖도록 구조를 재배치하는 일)은 **이 change의 스펙 요구사항이 아니다** — 데이터·기능 변경을 수반하므로 화면별 후속 change의 몫이다(design.md Decision 5).
- **topbar 전역 행동 2개 제한을 스펙에 고정한다.** 현 동작을 유지하되 회귀를 막는다.

**이 change에서 하지 않는 것** (후속 change로 분리)
- 최신성·원문연결·검증상태·인용수를 제품 고유의 신뢰 시각 언어로 정의하는 일 → `knowledge-trust-vocabulary`
- 각 화면의 기능·데이터 변경(위키 필터, 홈 상태 카드, 근거 패널 표준 포맷 등) → 화면별 후속 change
- 색 팔레트 변경. 청록을 현재 선택·핵심 CTA·성공 상태에만 쓰고 나머지를 흑백 중심으로 두는 현재 판단이 이미 맞다
- 담당자·백로그 우선순위·초대 상태처럼 새 스키마가 필요한 항목. 제품 결정이 선행돼야 한다

## Capabilities

### New Capabilities

없음. 이 change는 기존 목적지들의 표현 계약만 조인다.

### Modified Capabilities

- `dashboard-design-consistency`: `Consistent workspace page structure`의 "readable content width"를 **공유 콘텐츠 캔버스를 쓰는 목적지 간의 단일 본문 폭**으로 구체화하고, 자체 레이아웃을 소유한 목적지(Ask · 리더)를 사유와 함께 예외로 명시한다. 맥락 라벨이 제목이 이미 전달하는 정보를 반복하지 않을 것을 요구한다. `Shared state and control language`에 **상태 어휘의 목적지 간 일관성**과 **상태 텍스트 가독 최소 크기**를 추가한다. 전역 행동 집합 제한 요구사항을 추가한다.

## Impact

- **주 변경**: `docs/design-systems/v2/nexuswiki-design-system.css` — `.content` 및 화면별 폭 오버라이드(`.content.settings` `.content.sources` `.content.backlog` `.content.library`), `.badge`·메타 타이포 스케일
- **라벨 정리**: `KnowledgeGrid.tsx` · `WikiLibrary.tsx` 등 상태 라벨을 직접 문자열로 갖고 있는 컴포넌트. 어휘를 한곳에서 파생시킨다
- **eyebrow 감축**: `AskConversation` · `BacklogList` · `SourcesList` · `WikiLibrary` · `WikiPageContent` · `settings/page` 각 1곳
- **회귀 위험 범위가 넓다.** `.content` 폭은 모든 워크스페이스 목적지가 공유하므로 한 줄 변경이 6개 화면에 동시에 걸린다
- **검증 경로**: `/preview` 라우트가 로그인 없이 렌더되고 `PreviewWorkspace`가 앱과 같은 CSS 클래스를 쓰므로 이 change의 CSS 변경은 육안 확인이 가능하다. ⚠️ 단 `PreviewWorkspace`는 실제 컴포넌트가 아니라 **별도 JSX 복제본**이라 구조 변경은 자동 반영되지 않는다(UX-05에서 실제로 갈라져 3열 그리드가 깨진 전례가 있다)
- 마이그레이션 없음. RLS·테넌트 경계·워커 경로 변경 없음
