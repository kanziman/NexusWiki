"use client";

import { useRouter } from "next/navigation";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ArrowUpRight, Search } from "lucide-react";

import { workspacePath } from "@/lib/workspace-path";

export type AskHeroProps = {
  workspaceId: string;
  initialScope?: string;
  defaultChips?: string[];
};

const SCOPE_OPTIONS = [
  { id: "all", label: "워크스페이스 전체", desc: "모든 팀 지식에서 검색" },
  {
    id: "category",
    label: "카테고리 한정",
    desc: "선택한 카테고리 문서로 한정",
  },
  {
    id: "context",
    label: "현재 문서 주변",
    desc: "이 문서와 링크로 이어진 문서만",
  },
];

export function AskHero({
  workspaceId,
  initialScope = "워크스페이스 전체",
  // 칩은 홈 서버 페이지가 워크스페이스 위키 제목으로 주입한다. 기본값을
  // 엔지니어링 질문으로 두면 다른 도메인 워크스페이스에도 그 칩이 나타난다.
  defaultChips = [],
}: AskHeroProps) {
  const router = useRouter();
  const [question, setQuestion] = useState("");
  const [selectedScope, setSelectedScope] = useState(initialScope);
  const [scopeMenuOpen, setScopeMenuOpen] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const scopeWrapRef = useRef<HTMLDivElement | null>(null);

  const base = workspacePath(workspaceId);

  useEffect(() => {
    if (!scopeMenuOpen) return;
    function handleClickOutside(event: MouseEvent) {
      if (
        scopeWrapRef.current &&
        !scopeWrapRef.current.contains(event.target as Node)
      ) {
        setScopeMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [scopeMenuOpen]);

  function handleChipClick(chipText: string) {
    setQuestion(chipText);
    if (textareaRef.current) {
      textareaRef.current.focus();
      textareaRef.current.setSelectionRange(chipText.length, chipText.length);
    }
  }

  function handleSubmit() {
    const trimmed = question.trim();
    if (!trimmed) {
      textareaRef.current?.focus();
      return;
    }
    const params = new URLSearchParams();
    params.set("q", trimmed);
    if (selectedScope !== "워크스페이스 전체") {
      params.set("scope", selectedScope);
    }
    router.push(`${base}/ask?${params.toString()}`);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  }

  return (
    <div className="w-full">
      <div className="group/ask relative">
        {/* 포커스 시 앰비언트 글로우. opacity 만 올린다 — 단축키 힌트 뱃지를
          붙이면 이미 있는 ⌘+Enter 제출과 카피가 중복된다. */}
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -inset-0.5 rounded-[18px] bg-[var(--accent)]/20 blur-[14px] opacity-60 transition-opacity duration-300 group-focus-within/ask:opacity-100"
        />
        <section className="ask relative z-[1]" data-od-id="workspace-question">
          <div className="ask-main">
            <Search className="ask-icon" aria-hidden="true" />
            <textarea
              ref={textareaRef}
              id="question"
              aria-label="질문 입력"
              placeholder="이 워크스페이스에 질문하세요."
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={handleKeyDown}
              className="w-full resize-none border-0 bg-transparent p-0 text-base leading-relaxed text-[var(--fg)] focus:border-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 shadow-none outline-none ring-0"
            />
          </div>

          <div className="ask-bottom">
            <div ref={scopeWrapRef} className="scope-wrap relative z-20">
              <button
                type="button"
                className="scope cursor-pointer select-none"
                id="scopeTrigger"
                data-od-id="search-scope-control"
                aria-haspopup="true"
                aria-expanded={scopeMenuOpen}
                onClick={() => setScopeMenuOpen((prev) => !prev)}
              >
                <i className="scope-dot" aria-hidden="true" />
                <span id="scopeText">{selectedScope}</span>
                <span className="text-[10px] opacity-70">⌄</span>
              </button>

              {scopeMenuOpen && (
                <div className="scope-menu open" role="menu">
                  {SCOPE_OPTIONS.map((opt) => (
                    <button
                      key={opt.id}
                      type="button"
                      role="menuitem"
                      className="scope-option cursor-pointer"
                      data-scope={opt.label}
                      onClick={() => {
                        setSelectedScope(opt.label);
                        setScopeMenuOpen(false);
                      }}
                    >
                      <b>{opt.label}</b>
                      <span>{opt.desc}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button
              type="button"
              className="button primary"
              id="submitQuestion"
              data-od-id="submit-question-button"
              onClick={handleSubmit}
            >
              <span>질문하기</span>
              <ArrowUpRight size={15} aria-hidden="true" />
            </button>
          </div>
        </section>
      </div>

      <div className="chips" data-od-id="suggested-questions">
        {defaultChips.map((chip) => (
          <button
            key={chip}
            type="button"
            className="chip"
            onClick={() => handleChipClick(chip)}
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
