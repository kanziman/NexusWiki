"use client";

import { useRouter } from "next/navigation";
import { type KeyboardEvent, useEffect, useRef, useState } from "react";
import { ArrowUpRight, Check, Search, X } from "lucide-react";

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
  const scopeTriggerRef = useRef<HTMLButtonElement | null>(null);

  const base = workspacePath(workspaceId);

  function closeScopeMenu() {
    setScopeMenuOpen(false);
    scopeTriggerRef.current?.focus();
  }

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

    function handleKeyDown(event: globalThis.KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        closeScopeMenu();
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleKeyDown);

    // 모바일 하단 시트는 배경 스크롤이 시트를 밀어 내리면 닫기 대상이
    // 사라져 보이므로, 640px 이하에서만 body 스크롤을 잠근다.
    const previousOverflow = document.body.style.overflow;
    if (window.matchMedia?.("(max-width: 640px)").matches) {
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleKeyDown);
      document.body.style.overflow = previousOverflow;
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
        <section
          className={`ask relative ${scopeMenuOpen ? "z-50" : "z-[1]"}`}
          data-od-id="workspace-question"
        >
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
                ref={scopeTriggerRef}
                data-od-id="search-scope-control"
                aria-haspopup="menu"
                aria-expanded={scopeMenuOpen}
                aria-controls="scopeMenu"
                onClick={() => setScopeMenuOpen((prev) => !prev)}
              >
                <i className="scope-dot" aria-hidden="true" />
                <span id="scopeText">{selectedScope}</span>
                <span className="text-[10px] opacity-70">⌄</span>
              </button>

              {scopeMenuOpen && (
                <>
                  {/* 모바일에서만 보이는 스크림. 데스크톱은 CSS가 display:none.
                      배경을 흐려 시트를 현재 레이어로 읽히게 한다. */}
                  <div
                    className="scope-menu-backdrop"
                    onClick={closeScopeMenu}
                    aria-hidden="true"
                  />
                  <div
                    className="scope-menu open"
                    id="scopeMenu"
                    role="menu"
                    aria-labelledby="scopeTrigger"
                  >
                    <div className="scope-menu-handle" aria-hidden="true" />
                    <div className="scope-menu-head">
                      <span>검색 범위</span>
                      <button
                        type="button"
                        className="scope-menu-close"
                        aria-label="닫기"
                        onClick={closeScopeMenu}
                      >
                        <X size={16} aria-hidden="true" />
                      </button>
                    </div>
                    {SCOPE_OPTIONS.map((opt) => {
                      const selected = selectedScope === opt.label;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          role="menuitem"
                          className={`scope-option cursor-pointer${selected ? " is-selected" : ""}`}
                          data-scope={opt.label}
                          aria-current={selected ? "true" : undefined}
                          onClick={() => {
                            setSelectedScope(opt.label);
                            closeScopeMenu();
                          }}
                        >
                          <span className="scope-option-copy">
                            <b>{opt.label}</b>
                            <span>{opt.desc}</span>
                          </span>
                          {selected ? (
                            <Check
                              size={14}
                              className="scope-option-check"
                              aria-hidden="true"
                            />
                          ) : null}
                        </button>
                      );
                    })}
                  </div>
                </>
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

      <div
        className="chips flex items-center gap-2 flex-nowrap overflow-x-auto max-w-full pb-1 -mb-1 scrollbar-none sm:flex-wrap sm:overflow-visible sm:pb-0 sm:mb-0"
        data-od-id="suggested-questions"
      >
        {defaultChips.map((chip) => (
          <button
            key={chip}
            type="button"
            className="chip flex-none whitespace-nowrap text-xs"
            onClick={() => handleChipClick(chip)}
          >
            {chip}
          </button>
        ))}
      </div>
    </div>
  );
}
