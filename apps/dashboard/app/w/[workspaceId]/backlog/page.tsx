import { BacklogItem, BacklogList } from "@/components/BacklogList";
import { firstWikiLinkExcerpt, firstWikiLinkSpelling } from "@/lib/wiki-links";
import { createClient } from "@/lib/supabase/server";

type BacklogPageProps = {
  params: Promise<{ workspaceId: string }>;
};

type ReferencingPage = { id: string; slug: string; title: string };

/**
 * 주제별 표기 결정 규칙(design.md "표기 결정 규칙은 결정적이어야 한다"):
 * 인용 페이지를 제목 오름차순으로 훑으며 각 페이지의 첫 등장 표기를 모으고,
 * 최빈 표기를 쓴다. 동수면 그 표기를 낸 페이지 중 제목이 가장 앞선 쪽을
 * 따른다 — `pages`가 이미 제목 오름차순이므로, 최빈값과 동률인 첫 표기를
 * 만나는 순간 반환하면 그 조건이 그대로 성립한다.
 *
 * 어떤 페이지 본문에서도 표기를 찾지 못하면 `null` — 호출부가 slug 역변환으로
 * 폴백한다.
 */
function resolveDisplayTitle(
  targetSlug: string,
  pages: ReferencingPage[],
  contentByPageId: Map<string, string>,
): string | null {
  const spellings: string[] = [];
  for (const page of pages) {
    const content = contentByPageId.get(page.id);
    if (!content) continue;
    const spelling = firstWikiLinkSpelling(content, targetSlug);
    if (spelling) spellings.push(spelling);
  }

  if (spellings.length === 0) return null;

  const frequency = new Map<string, number>();
  for (const spelling of spellings) {
    frequency.set(spelling, (frequency.get(spelling) ?? 0) + 1);
  }
  const maxCount = Math.max(...frequency.values());

  return spellings.find((spelling) => frequency.get(spelling) === maxCount)!;
}

/**
 * ⚠️ 표시용 제목이 원문 표기를 찾지 못했을 때만 쓰는 폴백이다. slug 의
 * 하이픈을 공백으로 되돌리는 근사값이라 `slugify`가 지운 대소문자·문장부호는
 * 복원하지 못한다(backlog-management-prd.md §6-2 미해결 결정).
 */
function deslugify(slug: string): string {
  return slug.replace(/-/g, " ");
}

/**
 * UI-06 백로그 라우트 — Server Component로 요청자 세션(RLS)을 통해
 * 미해결 레드링크(to_wiki_id IS NULL)를 조회하고 주제별로 집계하여 전달한다.
 *
 * add-backlog-topic-context: 표시 제목은 slug 역변환이 아니라 인용 문서 본문의
 * `[[표기]]`에서 복원한다(design.md). 본문 조회는 미해결 링크의 `from_wiki_id`
 * 집합으로 제한한다 — 워크스페이스 전체 본문을 읽지 않는다.
 */
export default async function BacklogPage({ params }: BacklogPageProps) {
  const { workspaceId } = await params;
  const supabase = await createClient();

  // 1. 미해결 위키 링크 조회
  const { data: linksData, error: linksError } = await supabase
    .from("wiki_links")
    .select("id,target_slug,from_wiki_id,created_at")
    .eq("workspace_id", workspaceId)
    .is("to_wiki_id", null);

  const links = linksData ?? [];

  // 2. 출발지 위키 페이지 메타데이터 조회 — 인용 칩·정렬에 쓰인다.
  const { data: pagesData, error: pagesError } = await supabase
    .from("wiki_pages")
    .select("id,slug,title")
    .eq("workspace_id", workspaceId);

  // ⚠️ error 를 흘려보내면 안 된다. `linksData ?? []`만 쓰면 조회 실패가
  // "미해결 링크 없음"과 똑같은 빈 배열이 되어, 화면이 "모든 위키 링크가
  // 정상적으로 연결되어 있습니다"라고 단정하게 된다 — 안심시키는 거짓말이다.
  const loadFailed = Boolean(linksError) || Boolean(pagesError);
  if (loadFailed) {
    console.error("지식 공백 목록 조회 실패", {
      workspaceId,
      linksError,
      pagesError,
    });
  }

  const pagesMap = new Map<string, ReferencingPage>(
    (pagesData ?? []).map((page) => [page.id, page]),
  );

  // 3. 표기 복원용 본문 조회 — 미해결 링크가 실제로 가리키는 출발지 문서로만
  //    제한한다. 백로그가 비어 있으면 이 쿼리는 나가지 않는다.
  const referringPageIds = Array.from(
    new Set(
      links
        .map((link) => link.from_wiki_id)
        .filter((id): id is string => id !== null),
    ),
  );

  const { data: contentData } = referringPageIds.length
    ? await supabase
        .from("wiki_pages")
        .select("id,content")
        .eq("workspace_id", workspaceId)
        .in("id", referringPageIds)
    : { data: [] as { id: string; content: string }[] };

  const contentByPageId = new Map<string, string>(
    (contentData ?? []).map((page) => [page.id, page.content]),
  );

  const itemsMap = new Map<
    string,
    {
      target_slug: string;
      impact: number;
      first_detected_at: string;
      referencing_pages: ReferencingPage[];
    }
  >();

  for (const link of links) {
    const existing = itemsMap.get(link.target_slug);
    const referringPage = link.from_wiki_id
      ? pagesMap.get(link.from_wiki_id)
      : undefined;

    if (existing) {
      existing.impact += 1;
      if (
        new Date(link.created_at).getTime() <
        new Date(existing.first_detected_at).getTime()
      ) {
        existing.first_detected_at = link.created_at;
      }
      if (
        referringPage &&
        !existing.referencing_pages.some((p) => p.id === referringPage.id)
      ) {
        existing.referencing_pages.push(referringPage);
      }
    } else {
      itemsMap.set(link.target_slug, {
        target_slug: link.target_slug,
        impact: 1,
        first_detected_at: link.created_at,
        referencing_pages: referringPage ? [referringPage] : [],
      });
    }
  }

  const items: BacklogItem[] = Array.from(itemsMap.values())
    .map((item) => {
      // §4.1 이 SQL 레벨에서 referencing_pages 를 wp.title 오름차순으로
      // 낸다 — 표기 결정 규칙의 tie-break 전제다. 이 라우트는 JS에서 집계하므로
      // 여기서 같은 순서를 명시적으로 만든다.
      const pages = [...item.referencing_pages].sort((a, b) =>
        a.title.localeCompare(b.title, "ko"),
      );
      const displayTitle =
        resolveDisplayTitle(item.target_slug, pages, contentByPageId) ??
        deslugify(item.target_slug);

      // 3.1: 인용 문서마다 발췌를 하나씩 붙인다. 본문(content) 자체는 여기서
      // 소비되고 끝난다 — BacklogItem 은 display_title/excerpt 같은 계산된
      // 문자열만 들고 클라이언트로 나간다(design.md "위키 본문 전문이
      // 클라이언트로 전달되지 않는다").
      const referencingPages = pages.map((page) => {
        const content = contentByPageId.get(page.id);
        const excerpt = content
          ? firstWikiLinkExcerpt(content, item.target_slug)
          : null;
        return { ...page, excerpt };
      });

      return {
        ...item,
        referencing_pages: referencingPages,
        display_title: displayTitle,
      };
    })
    .sort(
      (a, b) =>
        b.impact - a.impact ||
        new Date(a.first_detected_at).getTime() -
          new Date(b.first_detected_at).getTime(),
    );

  return (
    <BacklogList
      workspaceId={workspaceId}
      initialItems={items}
      loadFailed={loadFailed}
    />
  );
}
