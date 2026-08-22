/**
 * 마크다운은 원문과 LLM 답변에서 오므로 실행 가능한 URL 프로토콜을 링크로
 * 만들지 않는다. React가 텍스트를 이스케이프해도 href의 javascript: 같은
 * 스킴은 별도 경계다.
 */
export function safeMarkdownHref(value: string): string | null {
  const href = value.trim();
  if (!href || /[\u0000-\u001f\u007f]/.test(href)) return null;

  const scheme = /^([a-z][a-z\d+.-]*):/i.exec(href)?.[1]?.toLowerCase();
  if (scheme && !["http", "https", "mailto"].includes(scheme)) return null;

  return href;
}
