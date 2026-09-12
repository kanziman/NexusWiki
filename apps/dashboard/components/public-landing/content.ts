export type PublicWikiPageLink = {
  title: string;
  slug: string;
};

export type PublicWikiShowcase = {
  workspace: string;
  workspaceSlug: string;
  docCount: number;
  blurb: string;
  featured: PublicWikiPageLink & { excerpt: string };
  related: PublicWikiPageLink[];
};

export function publicWikiHref(
  workspaceSlug: string,
  pageSlug: string,
): string {
  return `/p/${encodeURIComponent(workspaceSlug)}/${encodeURIComponent(pageSlug)}`;
}

export const landingPublicWikis: PublicWikiShowcase[] = [
  {
    workspace: "스타트업 올스타",
    workspaceSlug: "스타트업-올스타",
    docCount: 20,
    blurb:
      "초기 고객 확보부터 PMF까지, 스타트업 실전 지식을 위키로 엮었습니다.",
    featured: {
      title: "B2B SaaS 기업이 초기 100개 고객사를 확보한 6대 경로",
      slug: "b2b-saas-기업이-초기-100개-고객사를-확보한-6대-경로",
      excerpt:
        "B2C 서비스는 재미나 호기심만으로도 가입하지만, B2B 고객은 자신의 시간, 돈, 직장에서의 평판을 걸고 소프트웨어를 도입한다.",
    },
    related: [
      {
        title: "창업자 주도 영업",
        slug: "창업자-주도-영업-founder-led-sales",
      },
      {
        title: "제품-시장 적합성",
        slug: "제품-시장-적합성product-market-fit",
      },
      {
        title: "Superhuman PMF 엔진",
        slug: "superhuman-pmf-엔진-4단계-프로세스",
      },
    ],
  },
  {
    workspace: "마케팅 올스타",
    workspaceSlug: "마케팅-올스타",
    docCount: 28,
    blurb:
      "가치 방정식, 포지셔닝, 리드 생성. 마케팅 원문을 상호 링크된 문서로 정리했습니다.",
    featured: {
      title: "100의 법칙 (The Rule of 100)",
      slug: "100의-법칙-the-rule-of-100",
      excerpt:
        "일주일 하고 포기하는 것이 아니라, 최소 100일 동안 매일 실행해야 합니다. 성공과 실패의 차이는 전략이 아니라 실행 볼륨에 있습니다.",
    },
    related: [
      {
        title: "가치 방정식",
        slug: "가치-방정식-the-value-equation",
      },
      {
        title: "리드 생성의 Core Four",
        slug: "리드-생성의-core-four-the-core-four",
      },
      {
        title: "포지셔닝의 5가지 핵심 구성 요소",
        slug: "포지셔닝의-5가지-핵심-구성-요소",
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
