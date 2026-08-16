# NexusWiki 워크스페이스 디자인 시스템

```css
:root {
  --bg: oklch(1 0 0);
  --surface: oklch(0.982 0.004 247);
  --fg: oklch(0.208 0.033 264);
  --muted: oklch(0.554 0.033 258);
  --border: oklch(0.928 0.012 255);
  --accent: oklch(0.58 0.11 190);
}
```

보조 상태 토큰은 `--soft: oklch(.965 .025 190)`, `--danger: oklch(.57 .205 20)`, `--good: oklch(.63 .14 155)`를 사용한다. 그림자는 `0 18px 46px oklch(.208 .033 264 / .10)`을 기준으로 한다.

- Display: "Plus Jakarta Sans", "Pretendard", system-ui, sans-serif
- Body: "Pretendard", "Apple SD Gothic Neo", -apple-system, BlinkMacSystemFont, sans-serif
- Mono: "JetBrains Mono", ui-monospace, monospace

흰색 작업 캔버스와 아주 옅은 청회색 내비게이션을 기본으로 하며, 차분한 청록색은 선택된 지식 맥락과 단일 핵심 동작에만 사용한다.

## 적용 규칙

1. 데스크탑에서는 264px 너비의 고정 LNB와 유동형 작업 캔버스를 사용한다. 내비게이션은 `--surface`와 `--border`, 본문은 `--bg`로 분리한다.
2. 청록색 `--accent`는 활성 내비게이션, 선택 상태, 핵심 CTA에만 쓴다. 보조 정보와 비활성 아이콘은 `--muted`를 사용한다.
3. 문서·작업 항목은 제목 우선의 조밀한 가로 행으로 구성하고, 메타데이터는 제목 아래 작은 크기로 배치한다.
4. 모서리는 6px, 8px, 10px, 14px의 절제된 단계만 사용한다. 그림자는 플로팅 메뉴·모달·강조 카드에 한정한다.
5. 활성 항목의 청록 그림자는 `oklch(.58 .11 190 / .18)`을 사용하고, 호버는 전경색을 약화시키지 않는다.
