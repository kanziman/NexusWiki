export type PresetItem = {
  iconType: "flame" | "lightbulb" | "bolt" | "lock" | "shield";
  label: string;
  q: string;
  a: string;
  source: string;
  sourceText: string;
  wiki: string;
  wikiText: string;
};

export type WorkspaceScenario = {
  workspace: string;
  shortLabel: string;
  presets: PresetItem[];
};

export const landingScenarios: WorkspaceScenario[] = [
  {
    workspace: "Alex Hormozi의 $100M 마케팅 & 스케일업 위키",
    shortLabel: "Alex Hormozi 브레인",
    presets: [
      {
        iconType: "flame",
        label: "랜딩페이지 가격 저항 없애는 법",
        q: "랜딩페이지에서 가격 저항을 없애는 $100M 오퍼 공식은?",
        a: "가격을 깎지 말고 '가치 방정식'의 분모를 0으로 만들어야 합니다. 고객이 원하는 결과에 도달하는 시간(Time Delay)과 노력(Effort)을 최소화하고, 보증(Risk Reversal Guarantee)과 보너스 스택으로 성공 확실성을 극대화하면 거절하기 어려운 제안이 완성됩니다.",
        source: "EP.04 / 12:34",
        sourceText:
          '"Never drop your price to compete. If they complain about price, you haven\'t made the dream outcome certain enough, or the delay is too long..."',
        wiki: "concepts/value-equation",
        wikiText:
          "가치 방정식: (Dream Outcome × Likelihood) ÷ (Time Delay × Effort). 분모를 줄이는 전략이 마케팅의 본질이다.",
      },
      {
        iconType: "lightbulb",
        label: "초기 유료 고객 100명 모으기",
        q: "초기 유료 고객 100명을 가장 빠르게 모으려면 어떻게 해야 하나요?",
        a: "유료 광고를 돌리기 전에 'Core Four' 중 따뜻한 아웃리치(Warm Outreach)와 1:1 직접 세일즈부터 시작해야 합니다. Rule of 100에 따라 매일 잠재 고객에게 직접 가치를 제공하며 오퍼를 검증하는 것이 가장 확실합니다.",
        source: "EP.11 / 08:15",
        sourceText:
          '"Do not run ads until you have manually closed 100 clients. Warm outreach and direct outreach teach you the objections you cannot learn from metrics."',
        wiki: "guides/rule-of-100-leads",
        wikiText:
          "Rule of 100: 매일 직접 영업과 가치 전달 액션을 반복해 시장의 저항을 테스트하는 프레임워크.",
      },
      {
        iconType: "bolt",
        label: "절대 외주 주면 안 되는 역량",
        q: "1인 창업가가 절대로 외주를 주면 안 되는 핵심 역량은 무엇인가요?",
        a: "오퍼 설계(Offer Creation)와 세일즈(Sales)입니다. 제품 생산은 외주를 줄 수 있어도, '고객이 무엇을 원하는지 듣고 설득하는 과정'을 창업자가 직접 체득하지 못하면 사업은 스케일업되기 어렵습니다.",
        source: "EP.19 / 24:10",
        sourceText:
          '"You cannot outsource the thing that makes the money until you know how to make the money yourself. Sales is founder-led or it fails."',
        wiki: "concepts/founder-led-sales",
        wikiText:
          "초기 비즈니스의 생존은 창업자가 고객의 거절 이유를 직접 수집하고 오퍼를 수정하는 속도에 비례한다.",
      },
    ],
  },
  {
    workspace: "사내 테크 & 제품 정책 위키",
    shortLabel: "사내 테크 & 정책 위키",
    presets: [
      {
        iconType: "lock",
        label: "연간 결제 고객 환불 예외 규정",
        q: "새 결제 정책에서 연간 계약 고객 환불 처리 규칙은?",
        a: "연간 결제 후 30일 이내 해지 시에는 사용 월수만큼 월간 정가로 일할 계산 후 차액이 환불됩니다. 단, 엔터프라이즈 커스텀 계약은 전액 환불 불가 조항이 우선 적용됩니다.",
        source: "2026_Q3_결제정책_개정안.pdf (p.4)",
        sourceText:
          '"연간 요금제 중도 해지 시 기사용 기간은 프로모션 할인이 취소되며 월 단위 정가 기준으로 환급액을 정산한다."',
        wiki: "policies/billing-refund-exception",
        wikiText:
          "환불 정책 위키: 결제 30일 경과 시점의 크레딧 전환 원칙 및 예외 승인 결재 라인 명시.",
      },
      {
        iconType: "shield",
        label: "DB 테넌트 격리 아키텍처 원칙",
        q: "우리 서비스의 멀티테넌트 데이터 격리는 어떻게 강제되나요?",
        a: "애플리케이션 코드가 아니라 PostgreSQL의 RLS(Row Level Security)가 요청자 JWT와 워크스페이스 멤버십을 확인해 데이터 접근을 제한합니다.",
        source: "ADR-0012-postgres-rls-isolation.md",
        sourceText:
          '"테넌트 격리는 애플리케이션 버그가 발생해도 데이터 누수가 없도록 반드시 RLS 정책으로 강제한다."',
        wiki: "architecture/tenant-isolation",
        wikiText:
          "테넌트 데이터 격리 스펙: 요청자 JWT와 현재 워크스페이스 멤버십을 함께 검사하는 RLS 정책 기준.",
      },
    ],
  },
];

export const landingFaqs = [
  {
    q: "AI가 근거 없는 내용을 답하면 어떻게 되나요?",
    a: "NexusWiki는 검색된 근거가 없을 때 답변 생성을 중단하고 근거를 찾지 못했다고 알립니다. 답변에 발급된 인용은 실제 원문 청크와 위키 문서로 다시 열어 확인할 수 있습니다.",
  },
  {
    q: "내 워크스페이스가 다른 사용자에게 보이나요?",
    a: "워크스페이스 데이터는 요청자 JWT와 현재 멤버십을 확인하는 Postgres RLS 정책으로 제한됩니다. 사용자가 명시적으로 공개 발행한 위키 문서만 공개 경로에 노출됩니다.",
  },
  {
    q: "어떤 자료를 지식 위키로 만들 수 있나요?",
    a: "텍스트, PDF, URL처럼 원문을 추출할 수 있는 자료를 소스로 추가할 수 있습니다. NexusWiki는 원문과 컴파일된 위키를 각각 벡터·키워드로 검색해 함께 근거로 제시합니다.",
  },
] as const;
