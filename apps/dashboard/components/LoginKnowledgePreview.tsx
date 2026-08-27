"use client";

import { useEffect, useState } from "react";

type KnowledgeScenario = {
  question: string;
  answer: string;
  source: string;
  wiki: string;
};

const scenarios: KnowledgeScenario[] = [
  {
    question: "지난 분기 고객 이탈 원인은 무엇이었나요?",
    answer:
      "요금제 변경보다 온보딩 지연의 영향이 컸습니다. 인터뷰 원문과 리텐션 위키 모두 첫 가치 도달 시간의 증가를 공통 원인으로 지목합니다.",
    source: "원문 청크 3개",
    wiki: "위키 문서 2개",
  },
  {
    question: "새 결제 정책에서 반드시 지켜야 할 조건은?",
    answer:
      "기존 연간 계약은 갱신일까지 가격을 유지해야 합니다. 정책 회의록과 결제 운영 가이드에서 같은 예외 조건을 확인할 수 있습니다.",
    source: "원문 청크 4개",
    wiki: "위키 문서 2개",
  },
  {
    question: "검색 품질 저하가 시작된 시점은 언제인가요?",
    answer:
      "한국어 토크나이저 교체 직후부터입니다. 색인 버전 기록과 검색 품질 회고가 질의 시점 토큰 불일치를 함께 가리킵니다.",
    source: "원문 청크 2개",
    wiki: "위키 문서 3개",
  },
];

export function LoginKnowledgePreview() {
  const [scenarioIndex, setScenarioIndex] = useState(0);

  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

    if (reducedMotion.matches) return;

    const interval = window.setInterval(() => {
      setScenarioIndex((current) => (current + 1) % scenarios.length);
    }, 9000);

    return () => window.clearInterval(interval);
  }, []);

  const scenario = scenarios[scenarioIndex];

  return (
    <section
      className="login-knowledge-preview"
      aria-label="NexusWiki 답변 미리보기"
    >
      <header className="login-preview-header">
        <span className="login-preview-status">근거 연결 완료</span>
      </header>
      <div className="login-preview-body" aria-hidden="true">
        <div className="login-preview-question">
          <span className="login-preview-label">QUESTION</span>
          <p
            className="login-preview-question-text"
            key={`question-${scenarioIndex}`}
          >
            {scenario.question}
            <span className="login-preview-cursor" />
          </p>
        </div>
        <div className="login-preview-answer">
          <span className="login-preview-label">NEXUSWIKI ANSWER</span>
          <p
            className="login-preview-answer-text"
            key={`answer-${scenarioIndex}`}
          >
            {scenario.answer}
          </p>
          <div className="login-preview-evidence">
            <span className="login-evidence-chip">{scenario.source}</span>
            <span className="login-evidence-chip">{scenario.wiki}</span>
          </div>
        </div>
      </div>
    </section>
  );
}
