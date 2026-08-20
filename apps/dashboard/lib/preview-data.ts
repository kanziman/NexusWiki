export type PreviewWikiPage = {
  id: string;
  slug: string;
  title: string;
  category: "concepts" | "entities" | "guides" | "maps";
  verificationStatus: "verified" | "partial";
  updatedAt: string;
  sourceCount: number;
  content: string[];
};

export const previewUser = {
  name: "민서 김",
  email: "minseo@nexuswiki.local",
};

export const previewWorkspace = {
  id: "preview-workspace",
  name: "NexusWiki 제품 탐색",
  kind: "team" as const,
};

export const previewSources = [
  {
    id: "source-research",
    title: "2026 Q3 제품 리서치.pdf",
    type: "PDF",
    status: "완료",
    updatedAt: "오늘",
  },
  {
    id: "source-interviews",
    title: "고객 인터뷰 메모",
    type: "텍스트",
    status: "완료",
    updatedAt: "어제",
  },
  {
    id: "source-brief",
    title: "NexusWiki 포지셔닝 브리프",
    type: "URL",
    status: "처리 중",
    updatedAt: "2일 전",
  },
] as const;

export const previewWikiPages: PreviewWikiPage[] = [
  {
    id: "wiki-double-citation",
    slug: "double-citation",
    title: "이중 인용",
    category: "concepts",
    verificationStatus: "verified",
    updatedAt: "오늘",
    sourceCount: 3,
    content: [
      "NexusWiki의 답변은 컴파일된 위키 페이지와 원문 청크를 함께 가리킨다.",
      "이 구조는 요약의 이해 가능성과 근거의 추적 가능성을 동시에 유지한다.",
    ],
  },
  {
    id: "wiki-workspace",
    slug: "workspace-boundary",
    title: "워크스페이스 경계",
    category: "guides",
    verificationStatus: "verified",
    updatedAt: "어제",
    sourceCount: 2,
    content: [
      "워크스페이스는 지식·소스·멤버십을 묶는 기본 단위다.",
      "모든 조회는 요청자의 권한 범위 안에서만 결과를 반환한다.",
    ],
  },
  {
    id: "wiki-source-pipeline",
    slug: "source-pipeline",
    title: "소스 컴파일 파이프라인",
    category: "maps",
    verificationStatus: "partial",
    updatedAt: "3일 전",
    sourceCount: 4,
    content: [
      "원문을 수집한 뒤 청킹, 임베딩, 위키 컴파일 과정을 거친다.",
      "처리 상태는 소스 목록에서 확인할 수 있다.",
    ],
  },
  {
    id: "wiki-retrieval",
    slug: "hybrid-retrieval",
    title: "하이브리드 검색",
    category: "entities",
    verificationStatus: "partial",
    updatedAt: "4일 전",
    sourceCount: 3,
    content: [
      "검색은 위키와 원문을 여러 채널에서 함께 탐색한다.",
      "최종 답변에는 채널별 근거가 인용으로 남는다.",
    ],
  },
];

export const previewBacklog = [
  {
    slug: "evaluation-loop",
    title: "평가 루프",
    references: 4,
    firstDetected: "오늘",
  },
  {
    slug: "source-freshness",
    title: "소스 최신성",
    references: 2,
    firstDetected: "어제",
  },
] as const;

export const previewMembers = [
  { name: "민서 김", email: "minseo@nexuswiki.local", role: "소유자" },
  { name: "도윤 이", email: "doyun@nexuswiki.local", role: "편집자" },
  { name: "서윤 박", email: "seoyun@nexuswiki.local", role: "뷰어" },
] as const;

export const previewAskAnswer = {
  question: "NexusWiki가 일반적인 RAG 챗봇과 다른 점은 무엇인가요?",
  answer:
    "NexusWiki는 답변의 요약뿐 아니라 그 근거가 된 위키 문서와 원문 청크를 함께 보여줍니다. 그래서 사용자는 결론을 읽은 뒤 바로 지식의 맥락과 원문까지 되짚어 볼 수 있습니다.",
  wikiSlug: "double-citation",
  sourceId: "source-research",
};
