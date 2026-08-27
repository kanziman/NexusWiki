"use client";

import { useEffect, useState } from "react";

type KnowledgeScenario = {
  question: string;
  answer: string;
  source: string;
  wiki: string;
};

type PreviewPhase = "question" | "answer" | "evidence" | "complete";

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

function statusFor(phase: PreviewPhase) {
  if (phase === "question") return "질문 입력 중";
  if (phase === "answer") return "답변 생성 중";
  return "근거 연결 완료";
}

export function LoginKnowledgePreview() {
  const [scenarioIndex, setScenarioIndex] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [documentVisible, setDocumentVisible] = useState(true);
  const [phase, setPhase] = useState<PreviewPhase>("complete");
  const [questionText, setQuestionText] = useState(scenarios[0].question);
  const [answerText, setAnswerText] = useState(scenarios[0].answer);
  const [evidenceVisible, setEvidenceVisible] = useState(true);
  const scenario = scenarios[scenarioIndex];

  useEffect(() => {
    const syncVisibility = () => setDocumentVisible(!document.hidden);
    syncVisibility();
    document.addEventListener("visibilitychange", syncVisibility);

    if (typeof window.matchMedia !== "function") {
      return () =>
        document.removeEventListener("visibilitychange", syncVisibility);
    }

    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const syncReducedMotion = () => setReducedMotion(media.matches);
    syncReducedMotion();
    media.addEventListener("change", syncReducedMotion);

    return () => {
      document.removeEventListener("visibilitychange", syncVisibility);
      media.removeEventListener("change", syncReducedMotion);
    };
  }, []);

  useEffect(() => {
    if (reducedMotion || !documentVisible) {
      setPhase("complete");
      setQuestionText(scenario.question);
      setAnswerText(scenario.answer);
      setEvidenceVisible(true);
      return;
    }

    let active = true;
    const timeoutIds = new Set<number>();

    function wait(milliseconds: number) {
      return new Promise<void>((resolve) => {
        const timeoutId = window.setTimeout(() => {
          timeoutIds.delete(timeoutId);
          resolve();
        }, milliseconds);
        timeoutIds.add(timeoutId);
      });
    }

    async function typeText(
      text: string,
      delay: number,
      setText: (value: string | ((previous: string) => string)) => void,
    ) {
      setText("");

      for (const character of Array.from(text)) {
        await wait(delay);
        if (!active) return false;
        setText((previous) => previous + character);
      }

      return true;
    }

    async function playScenario() {
      // 첫 페인트는 완성된 내용을 보여 준다. 그렇지 않으면 느린 연결에서 카드가
      // 빈 상태로 보이고 로그인 화면의 신뢰감을 해친다.
      await wait(700);
      if (!active) return;

      setPhase("question");
      setAnswerText("");
      setEvidenceVisible(false);
      const questionDone = await typeText(
        scenario.question,
        68,
        setQuestionText,
      );
      if (!questionDone || !active) return;

      await wait(320);
      if (!active) return;

      setPhase("answer");
      const answerDone = await typeText(scenario.answer, 22, setAnswerText);
      if (!answerDone || !active) return;

      setPhase("evidence");
      setEvidenceVisible(true);
      await wait(2600);
      if (!active) return;

      setScenarioIndex((current) => (current + 1) % scenarios.length);
    }

    void playScenario();

    return () => {
      active = false;
      timeoutIds.forEach((timeoutId) => window.clearTimeout(timeoutId));
    };
  }, [documentVisible, reducedMotion, scenario]);

  return (
    <section
      className="login-knowledge-preview"
      aria-label="NexusWiki 답변 미리보기"
    >
      <header className="login-preview-header">
        <span className="login-preview-status">{statusFor(phase)}</span>
      </header>
      <div className="login-preview-body" aria-hidden="true">
        <div className="login-preview-question">
          <span className="login-preview-label">QUESTION</span>
          <p className="login-preview-question-text">
            {questionText}
            {phase === "question" ? (
              <span className="login-preview-cursor" />
            ) : null}
          </p>
        </div>
        <div className="login-preview-answer">
          <span className="login-preview-label">NEXUSWIKI ANSWER</span>
          <p className="login-preview-answer-text">{answerText}</p>
          <div className="login-preview-evidence">
            <span
              className={`login-evidence-chip${evidenceVisible ? " is-visible" : ""}`}
            >
              {scenario.source}
            </span>
            <span
              className={`login-evidence-chip${evidenceVisible ? " is-visible" : ""}`}
            >
              {scenario.wiki}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
