# Product Marketing Context

**Document version:** v3
**Last updated:** 2026-08-29

## Product Overview
**One-liner:** 원시 소스를 상호 연결된 위키로 자동 컴파일하고, 원문과 위키 양쪽을 인용한 검증 가능한 답변을 제공하는 팀 & 전문가 지식 워크스페이스
**What it does:** 팀 문서·회의록뿐만 아니라 특정 분야 전문가/인플루언서의 방대한 발언(유튜브 스크립트, 강연, 인터뷰, 저서) 등 원시 자료를 업로드하면, 백그라운드 AI가 그 사람의 사고체계와 개념을 상호 링크된 '살아있는 위키'로 자동 구조화합니다. 4채널 하이브리드 검색(위키/원문 듀얼 벡터 + 키워드 검색)을 통해 질문에 대해 실제 발언 원문과 위키 문서를 동시에 인용하여 "그 전문가라면 이 상황에서 어떻게 사고하고 조언할지" 완벽한 근거와 함께 답을 제공합니다.
**Product category:** AI 지식 베이스 / 살아있는 위키 (Living Wiki) / 전문가 사고모델 복제 및 지식 QA 도구
**Product type:** B2B / Prosumer SaaS (Knowledge Workspace)
**Business model:** 프리미엄(Freemium) 기반 구독 모델 (워크스페이스 수, 멤버 시트, 소스 저장 용량 및 토큰 기준 티어제)

## Target Audience
**Target companies & Individuals:** 
- **B2B 팀:** 애자일 스타트업, IT 제품 조직, 문서와 정책 변경이 잦은 테크 팀
- **Prosumer / 1인 창업가 / 마케터 / 크리에이터:** 특정 전문가·롤모델의 방대한 콘텐츠(유튜브, 뉴스레터, 팟캐스트)를 수집해 나만의 사고 자산(Second Brain)으로 구축하려는 지식 탐구자
- **리서처 / 기획자:** 방대한 인터뷰, 영상 스크립트, 리서치 자료를 체계적으로 색인화하고 검증 가능한 인사이트를 도출하려는 실무자
**Decision-makers & Power Users:** 
- Tech Lead, CTO, PM (팀 단위 도입 결정권자)
- 솔로프리너, 1인 마케터, 콘텐츠 전략가, 헤비 리서처 (개인/프로슈머 파워 유저)
**Primary use cases:** 
1. **[전문가 사고모델 복제 (Brain Clone)]** 롤모델/인플루언서의 유튜브·강연 스크립트를 워크스페이스에 축적해 "xx 전문가라면 어떻게 사고할까?"를 실제 발언 근거와 함께 질문하고 의사결정에 차용
2. **[팀 지식]** 흩어진 업무 문서에서 필요한 최신 정책·기술 결정 히스토리를 1초 만에 찾고, 원문 근거로 즉각 검증
**Jobs to be done:**
1. "내가 좋아하는 롤모델의 수십 시간짜리 유튜브/강연을 다 외우지 않아도, 그 사람의 사고 프레임워크를 통째로 복제한 나만의 AI 위키를 갖고 싶다."
2. "문서 정리하느라 시간 쓰지 않아도 소스만 넣으면 항상 최신으로 유지되는 지식 베이스를 만들고 싶다."
3. "AI가 답변할 때 지어낸 말이 아니라 '그 사람이 몇 번째 영상, 어느 문맥에서 그렇게 말했는지' 원본 출처를 확실하게 확인하고 싶다."
**Use cases:**
- **전문가 멘탈 모델 복제:** 탑티어 마케터(예: Alex Hormozi, Seth Godin)의 유튜브 전편 스크립트를 넣어 "내 서비스 랜딩페이지 오퍼를 짤 때 Hormozi라면 어떻게 피드백할까?" 질의응답
- **팀 온보딩 & 정책 QA:** 신규 입사자 온보딩 및 결제/환불 예외 조건 등 크리티컬 비즈니스 규정 확인
- **리서치 & 인터뷰 집약:** 수십 명의 고객 인터뷰 녹취록을 위키화하여 고객의 공통 불만 및 보이스 즉시 추출

## Personas
| Persona | Cares about | Challenge | Value we promise |
|---|---|---|---|
| **Knowledge Curator / Marketer** (1인 창업가, 마케터) | 거장의 인사이트를 내 업무에 즉시 적용하기 | 유튜브/책을 봐도 금방 잊어버리고 체계화가 안 됨 | 스크립트만 넣으면 거장의 사고체계가 위키로 자동 정리되고 질문 시 실제 발언 인용 제공 |
| **User** (실무 개발자 / 기획자) | 원하는 사내 답을 빠르고 정확하게 찾기 | 노션/슬랙을 뒤져도 최신 문서가 안 나옴 | 질문 1개로 원문 줄 번호와 위키 근거가 달린 답변 즉시 획득 |
| **Champion** (Tech Lead / PM) | 팀의 지식 파편화 및 지식 부채 해소 | 위키 정리할 시간이 없어 문서가 금방 낡아짐 | 소스만 업로드하면 알아서 링크가 엮이는 살아있는 위키 유지 |
| **Decision Maker** (CTO / 대표) | 온보딩 시간 단축, 중복 질문 감소, 보안 | 사내 기밀 유출 불안 및 도구 도입 비용 | Postgres RLS 기반 완전한 데이터 격리와 팀 지식 자산화 |

## Problems & Pain Points
**Core problem:** 
- **(개인/마케터)** 훌륭한 영상과 강연을 수없이 소비하지만 정보가 파편화되어 내 의사결정에 실제 활용하지 못함.
- **(팀)** 문서는 날마다 쌓이지만 정작 필요할 때 찾지 못하고 방치되어 낡아감.
- **(공통)** 일반 AI 챗봇은 출처 없이 두루뭉술하게 답하거나 환각이 있어, 진짜 그 사람의 생각인지 사내 규정이 맞는지 신뢰할 수 없음.
**Why alternatives fall short:**
- **Notion / Obsidian:** 사람이 일일이 백링크를 걸고 요약해야 해서 수십 시간 분량의 콘텐츠를 소화하기엔 노동력이 너무 큼.
- **단순 영상 요약 AI 도구:** 3줄 요약만 해줄 뿐, 전체 발언 맥락 사이의 연결고리를 만들지 못하고 심층 질문을 던질 수 없음.
- **일반 ChatGPT:** 특정 인물의 스타일을 흉내 낼 수는 있지만, 실제 그 사람이 했던 구체적 발언 근거(Citation)를 정확히 짚어주지 못함.
**What it costs them:** 
- 배운 지식을 실전에 써먹지 못해 발생하는 수많은 시행착오와 시간 낭비
- 출처가 불분명한 AI 조언을 믿고 실행했다가 발생하는 마케팅/비즈니스 실패
**Emotional tension:** "이거 분명 그 유튜브에서 엄청 좋은 팁으로 들었는데 어디서 말했더라?", "AI가 그럴듯하게 조언해주는데 진짜 원본 발언에 근거한 걸까?"

## Competitive Landscape
**Direct:** 
- **NotebookLM / Mem.ai:** 소스를 넣고 대화할 수 있으나, 개념 간의 상호 링크가 연결된 영구적 '위키 구조'로 자동 컴파일되지 않음.
- **Slite / Notion AI:** 수작업 정리 의존도가 높고, 원문-위키 양방향 인용 구조가 부족함.
**Secondary:** 
- **YouTube 요약 확장 프로그램:** 단순 1회성 요약에 그침. 여러 영상에 걸친 통합 사고체계 구축 불가.
**Indirect:** 
- **영상 북마크 / 개인 메모장:** 쌓이기만 하고 다시 열어보지 않는 정보의 무덤이 됨.

## Differentiation
**Key differentiators:**
- **원문과 위키 양방향 인용 (Dual-Citation Grounding):** 답변 문장마다 실제 영상 스크립트 원문과 위키 개념 문서를 동시에 링크하여 원본 맥락 100% 검증 가능.
- **자동 위키 컴파일 (Living Wiki Pipeline):** 유튜브 스크립트, PDF, 문서를 넣으면 LLM 백그라운드 워커가 핵심 개념, 법칙, 프레임워크를 상호 링크 위키로 자동 빌드.
- **4채널 하이브리드 검색 (4-Channel Retrieval):** 위키 벡터 + 원문 벡터(HNSW pgvector) + 위키 키워드 + 원문 키워드(GIN bigram) 융합 RRF 랭킹으로 누락 없는 검색.
- **인간 검증 워크플로우 (Human Verification Status):** 자동 정리된 위키에 내가 직접 검증 뱃지(`verified`)를 부여하며 나만의 공인 지식 베이스로 완성.
- **원클릭 공개 위키 발행 (`/p/[workspace]/[page]`):** 내가 구축한 "OO 전문가 사고 위키"를 외부 사람들에게 즉시 멋진 공개 지식 페이지로 공유/자랑 가능.

## Objections
| Objection | Response |
|---|---|
| "AI가 그 사람의 생각을 지어내서 답하면 어쩌죠?" | NexusWiki는 실제 입력된 스크립트 원문에 없는 내용은 임의로 꾸며내지 않으며, 모든 문장마다 원본 발언 타임스탬프/텍스트 청크를 칩 형태로 명시합니다. |
| "영상 100개 분량의 방대한 스크립트도 소화할 수 있나요?" | 4채널 하이브리드 검색(위키/원문 벡터 & 키워드)을 통해 방대한 양의 소스도 누락 없이 정확한 맥락을 짚어냅니다. |
| "내 개인적인 지식 워크스페이스가 남에게 노출되진 않나요?" | Postgres RLS로 완벽히 격리되어 있으며, 사용자가 명시적으로 '공개 발행'을 누른 문서만 `/p/` 경로로 노출됩니다. |

**Anti-persona:** 
- 단순히 1회성으로 영상 3줄 요약만 보고 넘어가는 라이트 유저
- 지식을 구조화하거나 활용할 의지 없이 단순 즐겨찾기만 모으는 사용자

## Switching Dynamics
**Push:** 아무리 유익한 영상을 봐도 머릿속에서 흩어지는 답답함, 단순 요약 AI의 얕은 인사이트, 출처 없는 AI 조언의 불안감.
**Pull:** 영상 텍스트만 넣으면 거장의 뇌가 그대로 위키가 되는 마법, "그 사람이라면 이 문제를 어떻게 풀까?"를 물어볼 수 있는 나만의 멘토 위키.
**Habit:** 노션에 메모해 두고 다시는 열어보지 않던 습관.
**Anxiety:** "스크립트 추출해서 넣는 게 번거롭지 않을까?" (→ 텍스트/파일 드롭만으로 백그라운드에서 자동 위키화).

## Customer Language
**How they describe the problem:**
- "유튜브에서 진짜 좋은 마케팅 인사이트를 봤는데, 막상 내 사업에 적용하려니 어디서 봤는지 기억이 안 나요."
- "그 전문가의 사고방식을 통째로 내 뇌에 다운로드하고 싶어요."
- "ChatGPT한테 'Alex Hormozi 스타일로 말해줘' 하면 그냥 말투만 흉내 내고 뜬구름 잡는 소리만 해요."
**How they describe us:**
- "이 워크스페이스 하나만 있으면 그 전문가를 24시간 내 개인 마케팅 자문단으로 둔 것 같아요."
- "질문하니까 그 사람이 유튜브 몇 번째 영상에서 했던 말을 정확히 인용해 주네요."
- "자료만 모아뒀는데 알아서 위키로 엮여서 내가 만든 지식 백과사전이 됐어요."
**Words to use:** 거장의 사고방식 복제, 멘탈 모델 위키, 살아있는 지식 베이스, 원문 검증 답변, 나만의 전문가 AI 자문단
**Words to avoid:** 단순 영상 요약기, 말투 흉내 챗봇

## Brand Voice
**Tone:** 조용하고 정돈되며 지적인 신뢰감을 주는 (Quiet, Orderly, Authoritative yet Clear)
**Style:** 명료한 한국어, 과장 없는 실질적 유용성 강조, 엔지니어링의 정밀함
**Personality:** 지식을 꿰뚫어 보는 통찰력 있는 사서, 든든한 지식 파트너

## Proof Points
**Metrics:**
- 4채널 융합 검색(위키 벡터 + 원문 벡터 + 위키 키워드 + 원문 키워드) 및 RRF 랭킹
- 수십 개 영상 스크립트의 상호 링크 및 개념 카테고리 자동 컴파일
- 1초 미만 원문 발언 청크(Citation) 연결
**Value themes:**
| Theme | Proof |
|---|---|
| **정밀한 근거 (True Grounding)** | 단순 페르소나 흉내가 아닌, 실제 발언 원문 청크 기반 인용 |
| **자동 구조화 (Self-Organizing)** | 파편화된 스크립트가 개념(Concepts), 가이드(Guides)로 자동 체계화 |
| **안전한 공유 (Public Showcase)** | 구축한 전문가 지식 위키를 원클릭으로 웹에 공개 발행 |

## Goals
**Business goal:** 팀 협업 고객뿐만 아니라, 거장의 지식을 복제하려는 크리에이터/마케터/프로슈머에게 압도적 유용성을 체감시켜 바이럴 및 가입 유도
**Conversion action:** 공개 위키(쇼케이스) 탐색 후 "나만의 전문가 지식 위키 만들기" 시작 및 첫 스크립트 업로드
**Current metrics:** 초기 런칭 준비 단계

## Changelog
*Newest first. One line per revision: what changed and why.*
- v3 (2026-08-29) — Corrected search architecture to 4-channel hybrid retrieval (wiki_vector, source_vector, wiki_lexical, source_lexical) with knowledge graph disabled per retrieval policy (`graph_enabled: false`).
- v2 (2026-08-29) — Added Expert Mental Model / Brain Clone use case (YouTube/Influencer transcripts) and expanded ICP to Solo Creators, Marketers, and Knowledge Curators.
- v1 (2026-08-29) — Initial context auto-drafted from codebase (PRODUCT.md, README.md, PRDs, and architecture specs).
