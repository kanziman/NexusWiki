"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { PublicLandingFaq } from "./public-landing/PublicLandingFaq";
import { PublicLandingHeader } from "./public-landing/PublicLandingHeader";
import { PublicLandingShowcase } from "./public-landing/PublicLandingShowcase";
import { landingFaqs, landingScenarios } from "./public-landing/content";

export function PublicLandingPage() {
  const [currentWsIdx, setCurrentWsIdx] = useState(0);
  const [currentScenarioIdx, setCurrentScenarioIdx] = useState(0);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleWorkspaceChange = (idx: number) => {
    setCurrentWsIdx(idx);
    setCurrentScenarioIdx(0);
  };

  const toggleFaq = (idx: number) => {
    setOpenFaq((prev) => (prev === idx ? null : idx));
  };

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--fg)] font-sans selection:bg-[var(--accent-soft)] selection:text-[var(--accent)]">
      <PublicLandingHeader
        mobileMenuOpen={mobileMenuOpen}
        onToggleMobileMenu={() => setMobileMenuOpen((current) => !current)}
        onCloseMobileMenu={() => setMobileMenuOpen(false)}
      />

      {/* Hero Section */}
      <section className="relative pt-20 pb-16 px-6 text-center overflow-hidden">
        <div className="max-w-4xl mx-auto">
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[var(--surface)] border border-[var(--border)] text-xs font-semibold text-[var(--accent)] mb-6 shadow-sm">
            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] animate-pulse motion-reduce:animate-none" />
            <span>The Living Knowledge Workspace</span>
          </div>

          <h1 className="text-3xl sm:text-4xl md:text-6xl font-extrabold tracking-tight leading-[1.18] mb-5">
            흩어진 영상과 문서를,
            <br />
            <span className="text-[var(--accent)]">
              원문까지 되짚는 살아있는 위키
            </span>
            로.
          </h1>

          <p className="text-lg md:text-xl text-[var(--muted)] max-w-2xl mx-auto mb-9 leading-relaxed">
            스크립트와 팀 문서를 넣으면 상호 링크된 위키로 정리됩니다. 질문을
            던지면 실제 원문과 위키 문서 양쪽의 근거를 함께 보여 줍니다.
          </p>

          <div className="flex items-center justify-center gap-4 flex-wrap mb-8">
            <Link
              href="/login"
              className="nw-focus-ring inline-flex items-center gap-2 px-7 py-3.5 bg-[var(--fg)] text-[var(--bg)] text-base font-bold rounded-xl shadow-lg hover:shadow-xl hover:translate-y-[-1px] transition-all motion-reduce:transform-none"
            >
              <span>내 지식 워크스페이스 만들기</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="5" y1="12" x2="19" y2="12" />
                <polyline points="12 5 19 12 12 19" />
              </svg>
            </Link>
            <a
              href="#showcase"
              className="nw-focus-ring inline-flex items-center gap-2 px-6 py-3.5 text-base font-semibold text-[var(--fg)] hover:bg-[var(--surface)] rounded-xl transition-colors"
            >
              <span>라이브 쇼케이스 둘러보기</span>
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <line x1="12" y1="5" x2="12" y2="19" />
                <polyline points="19 12 12 19 5 12" />
              </svg>
            </a>
          </div>

          <div className="flex items-center justify-center gap-6 text-xs md:text-sm text-[var(--muted)] flex-wrap">
            <span className="inline-flex items-center gap-1.5">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--good)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>텍스트·PDF 소스 지원</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--good)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>첫 소스부터 바로 시작</span>
            </span>
            <span className="inline-flex items-center gap-1.5">
              <svg
                width="15"
                height="15"
                viewBox="0 0 24 24"
                fill="none"
                stroke="var(--good)"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              <span>Postgres RLS 기반 워크스페이스 격리</span>
            </span>
          </div>
        </div>
      </section>

      <PublicLandingShowcase
        scenarios={landingScenarios}
        currentWorkspaceIndex={currentWsIdx}
        currentPresetIndex={currentScenarioIdx}
        onWorkspaceChange={handleWorkspaceChange}
        onPresetChange={setCurrentScenarioIdx}
      />
      {/* Comparison Section */}
      <section className="py-20 px-6 border-t border-[var(--border)] bg-[var(--surface)]">
        <div className="max-w-4xl mx-auto text-center mb-14">
          <p className="mb-3 text-sm font-semibold text-[var(--accent)]">
            기존 지식 관리가 놓치는 것
          </p>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
            지식은 계속 쌓이는데,
            <br />왜 실전에 쓰려고 하면 아무것도 없을까요?
          </h2>
          <p className="mx-auto w-full max-w-prose text-base text-[var(--muted)]">
            단순한 메모나 얕은 AI 챗봇이 해결하지 못한 지식의 문제를 끝냅니다.
          </p>
        </div>

        <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-8 rounded-2xl border border-red-200 bg-red-50/40 text-left">
            <h3 className="text-xl font-bold text-[var(--danger)] mb-2">
              기존 도구의 한계
            </h3>
            <p className="text-sm text-[var(--muted)] mb-6">
              Notion, Confluence, 단순 ChatGPT
            </p>
            <ul className="space-y-4 text-sm leading-relaxed">
              <li className="flex items-start gap-3">
                <span className="text-[var(--danger)] font-bold">✕</span>
                <span>
                  <strong>수동 정리의 지옥:</strong> 사람이 일일이 백링크를 걸고
                  목차를 짜야 해서 시간이 지나면 방치되어 낡아감 (Stale Wiki).
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-[var(--danger)] font-bold">✕</span>
                <span>
                  <strong>AI 환각(거짓말) 불안:</strong> 그럴듯하게 답하지만
                  원본 출처가 없어 중요한 비즈니스 결정에 믿고 쓸 수 없음.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-[var(--danger)] font-bold">✕</span>
                <span>
                  <strong>단편적 3줄 요약:</strong> 수십 개의 영상과 문맥 사이의
                  상호 연결된 지식 체계를 만들어내지 못함.
                </span>
              </li>
            </ul>
          </div>

          <div className="p-8 rounded-2xl border-2 border-[var(--accent)] bg-[var(--bg)] shadow-lg relative text-left">
            <span className="absolute -top-3.5 right-6 bg-[var(--accent)] text-white text-xs font-bold px-3 py-1 rounded-full inline-flex items-center gap-1">
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
              >
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              NEXUSWIKI
            </span>
            <h3 className="text-xl font-bold text-[var(--accent)] mb-2">
              살아있는 위키 엔진
            </h3>
            <p className="text-sm text-[var(--muted)] mb-6">
              자동 컴파일 & 듀얼 인용 시스템
            </p>
            <ul className="space-y-4 text-sm leading-relaxed">
              <li className="flex items-start gap-3">
                <span className="text-[var(--good)] font-bold">✓</span>
                <span>
                  <strong>자동 위키 컴파일:</strong> 파일과 스크립트를 넣으면
                  백그라운드 AI가 상호 링크된 위키로 체계화.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-[var(--good)] font-bold">✓</span>
                <span>
                  <strong>원문·위키 이중 인용:</strong> 답변과 함께 실제 원문
                  위치와 위키 문서를 확인할 수 있는 근거 칩을 제공.
                </span>
              </li>
              <li className="flex items-start gap-3">
                <span className="text-[var(--good)] font-bold">✓</span>
                <span>
                  <strong>4채널 하이브리드 검색:</strong> 위키/원문 듀얼
                  벡터(HNSW) + 키워드(GIN) 융합 RRF 랭킹으로 서로 다른 검색
                  방식을 보완.
                </span>
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* How It Works (3 Steps) */}
      <section
        id="how-it-works"
        className="py-20 px-6 max-w-5xl mx-auto scroll-mt-28 text-center"
      >
        <div className="mb-14">
          <p className="mb-3 text-sm font-semibold text-[var(--accent)]">
            자료가 답변이 되기까지
          </p>
          <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
            단 3단계로 완성되는 나만의 지식 자산
          </h2>
          <p className="mx-auto w-full max-w-prose text-base text-[var(--muted)]">
            소스 투입부터 검증된 질의응답까지, 모든 복잡한 과정은 백그라운드에서
            처리됩니다.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-left">
          <div className="p-7 rounded-2xl bg-[var(--surface)] border border-[var(--border)] hover:-translate-y-1 transition-transform motion-reduce:transform-none">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded font-mono text-xs font-bold mb-4">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
              <span>STEP 01</span>
            </span>
            <h3 className="text-lg font-bold mb-2">소스 파일 드롭</h3>
            <p className="text-sm text-[var(--muted)] leading-relaxed">
              유튜브 스크립트, PDF, 회의록, 아키텍처 문서 등 가공되지 않은 원본
              자료를 자유롭게 업로드하세요.
            </p>
          </div>

          <div className="p-7 rounded-2xl bg-[var(--surface)] border border-[var(--border)] hover:-translate-y-1 transition-transform motion-reduce:transform-none">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded font-mono text-xs font-bold mb-4">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <polygon points="12 2 2 7 12 12 22 7 12 2" />
                <polyline points="2 17 12 22 22 17" />
                <polyline points="2 12 12 17 22 12" />
              </svg>
              <span>STEP 02</span>
            </span>
            <h3 className="text-lg font-bold mb-2">자동 위키 컴파일</h3>
            <p className="text-sm text-[var(--muted)] leading-relaxed">
              백그라운드 워커가 소스를 분석하여 핵심 개념(Concepts), 엔티티,
              가이드로 자동 분류하고 상호 링크를 엮습니다.
            </p>
          </div>

          <div className="p-7 rounded-2xl bg-[var(--surface)] border border-[var(--border)] hover:-translate-y-1 transition-transform motion-reduce:transform-none">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded font-mono text-xs font-bold mb-4">
              <svg
                width="13"
                height="13"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
              </svg>
              <span>STEP 03</span>
            </span>
            <h3 className="text-lg font-bold mb-2">
              근거 기반 질의응답 & 공유
            </h3>
            <p className="text-sm text-[var(--muted)] leading-relaxed">
              질문을 던지면 실제 원문 청크와 함께 신뢰할 수 있는 답을 얻습니다.
              원클릭으로 멋진 공개 위키로 발행할 수 있습니다.
            </p>
          </div>
        </div>
      </section>

      {/* Use Cases */}
      <section
        id="usecases"
        className="py-20 px-6 scroll-mt-28 border-t border-[var(--border)] bg-[var(--surface)]"
      >
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-14">
            <p className="mb-3 text-sm font-semibold text-[var(--accent)]">
              개인과 팀을 위한 두 가지 활용법
            </p>
            <h2 className="text-3xl md:text-4xl font-extrabold tracking-tight mb-4">
              하나의 강력한 엔진, 두 개의 세상
            </h2>
            <p className="mx-auto w-full max-w-prose text-base text-[var(--muted)]">
              개인의 지적 자산부터 팀의 핵심 문서까지 한곳에서 활용할 수
              있습니다.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-left">
            <div className="p-8 md:p-10 rounded-2xl bg-[var(--bg)] border border-[var(--border)] flex flex-col justify-between shadow-sm">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[var(--surface-raised)] text-[var(--fg)] rounded font-mono text-xs font-bold mb-5">
                  <svg
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                  <span>PROSUMER & CREATOR</span>
                </span>
                <h3 className="text-2xl font-extrabold mb-3">
                  거장의 사고방식 복제
                  <br />
                  (Brain Clone)
                </h3>
                <p className="text-sm text-[var(--muted)] mb-6">
                  좋아하는 마케터, 투자자, 전문가의 영상 스크립트를 모아 필요할
                  때 원문 근거를 확인하는 개인 지식 위키로 만듭니다.
                </p>
                <div className="space-y-3 mb-8 text-sm">
                  <div className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span>
                      &quot;이 랜딩페이지 오퍼 어떻게 짤까?&quot; 거장의 실제
                      발언 근거로 피드백
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span>
                      방대한 스크립트가 체계적인 백과사전식 위키로 자동 정리
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span>
                      원클릭으로 웹에 공개 발행해 나만의 지식 큐레이션 브랜딩
                    </span>
                  </div>
                </div>
              </div>
              <Link
                href="/login"
                className="nw-focus-ring w-full py-3 px-4 rounded-xl border border-[var(--border)] hover:bg-[var(--surface)] text-sm font-semibold flex items-center justify-between transition-colors"
              >
                <span>거장 브레인 만들기</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </Link>
            </div>

            <div className="p-8 md:p-10 rounded-2xl bg-[var(--bg)] border border-[var(--border)] flex flex-col justify-between shadow-sm">
              <div>
                <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-[var(--surface-raised)] text-[var(--fg)] rounded font-mono text-xs font-bold mb-5">
                  <svg
                    width="13"
                    height="13"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                  >
                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
                    <circle cx="9" cy="7" r="4" />
                    <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
                    <path d="M16 3.13a4 4 0 0 1 0 7.75" />
                  </svg>
                  <span>B2B TECH TEAM</span>
                </span>
                <h3 className="text-2xl font-extrabold mb-3">
                  살아있는 팀 위키
                  <br />& 온보딩 자동화
                </h3>
                <p className="text-sm text-[var(--muted)] mb-6">
                  슬랙과 노션에 흩어진 정책, 결제 규정, 개발 문서를 통합해 신입
                  팀원도 원문 근거와 함께 필요한 답을 찾게 합니다.
                </p>
                <div className="space-y-3 mb-8 text-sm">
                  <div className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span>
                      신규 입사자가 질문하면 &quot;사내 규정 몇 조 몇 항&quot;
                      원문 즉각 표시
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span>새 소스를 추가해 연결된 위키를 다시 컴파일</span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span>
                      요청자 JWT와 Postgres RLS 기반 워크스페이스 데이터 격리
                    </span>
                  </div>
                </div>
              </div>
              <Link
                href="/login"
                className="nw-focus-ring w-full py-3 px-4 rounded-xl border border-[var(--border)] hover:bg-[var(--surface)] text-sm font-semibold flex items-center justify-between transition-colors"
              >
                <span>팀 워크스페이스 시작하기</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <line x1="5" y1="12" x2="19" y2="12" />
                  <polyline points="12 5 19 12 12 19" />
                </svg>
              </Link>
            </div>
          </div>
        </div>
      </section>

      <PublicLandingFaq
        items={landingFaqs}
        openIndex={openFaq}
        onToggle={toggleFaq}
      />
      {/* Final Banner */}
      <section className="px-6 pb-20 max-w-5xl mx-auto">
        <div className="p-12 md:p-16 rounded-3xl bg-[var(--fg)] text-[var(--bg)] text-center">
          <h2 className="text-3xl md:text-5xl font-extrabold tracking-tight mb-4">
            흩어지는 지식을 방치하지 마세요.
          </h2>
          <p className="mx-auto mb-8 w-full max-w-prose text-base text-[var(--bg)]/75 md:text-lg">
            좋아하는 전문가의 유튜브 스크립트 1개부터 시작해 보세요.
            <br />첫 소스부터 상호 연결된 &apos;살아있는 지식 자산&apos;을
            만들어 보세요.
          </p>
          <Link
            href="/login"
            className="nw-focus-ring inline-flex items-center gap-2 px-8 py-4 bg-white text-[var(--fg)] font-bold text-base rounded-xl shadow-lg hover:shadow-xl hover:translate-y-[-1px] transition-all motion-reduce:transform-none"
          >
            <span>무료로 내 첫 워크스페이스 시작하기</span>
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="5" y1="12" x2="19" y2="12" />
              <polyline points="12 5 19 12 12 19" />
            </svg>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-10 px-6 border-t border-[var(--border)] text-xs text-[var(--muted)]">
        <div className="max-w-6xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2 font-bold text-[var(--fg)] text-sm">
            <Image
              src="/nexuswiki-mark.png"
              alt="NexusWiki"
              width={24}
              height={24}
              className="rounded"
            />
            <span>NexusWiki</span>
          </div>
          <p>
            © 2026 NexusWiki Inc. All rights reserved. Built for thinkers and
            teams.
          </p>
        </div>
      </footer>
    </div>
  );
}
