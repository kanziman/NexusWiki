import Image from "next/image";
import Link from "next/link";
import { Menu, X } from "lucide-react";

type PublicLandingHeaderProps = {
  mobileMenuOpen: boolean;
  onToggleMobileMenu: () => void;
  onCloseMobileMenu: () => void;
};

const sectionLinks = [
  { href: "#showcase", label: "라이브 쇼케이스" },
  { href: "#how-it-works", label: "동작 원리" },
  { href: "#usecases", label: "활용 사례" },
  { href: "#faq", label: "FAQ" },
] as const;

export function PublicLandingHeader({
  mobileMenuOpen,
  onToggleMobileMenu,
  onCloseMobileMenu,
}: PublicLandingHeaderProps) {
  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--bg)]/92 backdrop-blur-md">
      <div className="mx-auto flex min-h-17 max-w-6xl items-center justify-between gap-3 px-4 sm:px-6">
        <Link
          href="/"
          className="nw-focus-ring flex min-w-0 items-center gap-2.5 rounded-lg font-extrabold tracking-tight"
          aria-label="NexusWiki 홈"
        >
          <Image
            src="/nexuswiki-mark.png"
            alt=""
            width={32}
            height={32}
            className="shrink-0 rounded-lg shadow-sm"
            priority
          />
          <span className="truncate text-base sm:text-lg">NexusWiki</span>
          <span className="hidden rounded bg-[var(--accent-soft)] px-1.5 py-0.5 text-[10px] font-bold tracking-wider text-[var(--accent)] lg:inline">
            LIVING KNOWLEDGE
          </span>
        </Link>

        <nav
          aria-label="공개 랜딩 주요 섹션"
          className="hidden items-center gap-7 text-sm font-medium text-[var(--muted)] md:flex"
        >
          {sectionLinks.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="nw-focus-ring rounded-md px-1.5 py-2 transition-colors hover:text-[var(--fg)]"
            >
              {item.label}
            </a>
          ))}
        </nav>

        <div className="flex shrink-0 items-center gap-1.5 sm:gap-2">
          <Link
            href="/login"
            className="nw-focus-ring hidden rounded-lg px-3 py-2 text-sm font-semibold text-[var(--fg)] transition-colors hover:bg-[var(--surface)] sm:inline-flex"
          >
            로그인
          </Link>
          <Link
            href="/login"
            className="nw-focus-ring rounded-lg bg-[var(--fg)] px-3 py-2 text-xs font-semibold text-[var(--bg)] shadow-sm transition-all hover:-translate-y-px hover:shadow-md motion-reduce:transform-none sm:px-4 sm:text-sm"
          >
            <span className="sm:hidden">시작하기</span>
            <span className="hidden sm:inline">무료로 시작하기</span>
          </Link>
          <button
            type="button"
            onClick={onToggleMobileMenu}
            className="nw-focus-ring inline-flex size-10 items-center justify-center rounded-lg text-[var(--fg)] transition-colors hover:bg-[var(--surface)] md:hidden"
            aria-label={mobileMenuOpen ? "메뉴 닫기" : "메뉴 열기"}
            aria-expanded={mobileMenuOpen}
            aria-controls="public-mobile-navigation"
          >
            {mobileMenuOpen ? (
              <X size={19} aria-hidden="true" />
            ) : (
              <Menu size={19} aria-hidden="true" />
            )}
          </button>
        </div>
      </div>

      {mobileMenuOpen ? (
        <nav
          id="public-mobile-navigation"
          aria-label="모바일 공개 랜딩 메뉴"
          className="border-t border-[var(--border)] bg-[var(--bg)] px-4 py-3 md:hidden"
        >
          <div className="mx-auto flex max-w-6xl flex-col gap-1">
            {sectionLinks.map((item) => (
              <a
                key={item.href}
                href={item.href}
                onClick={onCloseMobileMenu}
                className="nw-focus-ring rounded-lg px-3 py-2.5 text-sm font-semibold text-[var(--fg)] transition-colors hover:bg-[var(--surface)]"
              >
                {item.label}
              </a>
            ))}
            <Link
              href="/login"
              onClick={onCloseMobileMenu}
              className="nw-focus-ring mt-1 rounded-lg border border-[var(--border)] px-3 py-2.5 text-center text-sm font-semibold text-[var(--fg)]"
            >
              로그인
            </Link>
          </div>
        </nav>
      ) : null}
    </header>
  );
}
