## 1. Token rewiring

- [x] 1.1 Repoint `--color-primary` to `var(--nw-action)` and `--color-primary-active` to `var(--nw-action-hover)`. **설계 변경**: 처음엔 `@theme` 블록 안에서 재배선했으나, 컴파일된 CSS를 직접 검사해보니 Tailwind v4의 `@theme`은 `@layer theme`으로 컴파일되고, CSS Cascade Layers 규칙상 레이어 없는(unlayered) 규칙이 항상 이긴다 — design-tokens.css의 `:root { --color-primary: #ff385c }`가 바로 그 unlayered 규칙이라 `@theme` 안에서 덮어써도 이길 수 없었다(빌드된 CSS에 `--color-primary:#ff385c`가 여전히 유효한 값으로 남는 것을 확인). 대신 `globals.css`의 기존 plain `:root` 블록(`--font-family-base` 오버라이드가 이미 쓰던 것과 같은 자리 — 그 주석이 정확히 이 메커니즘을 설명하고 있었음)에 추가해 unlayered 규칙끼리의 소스 순서로 이기도록 했다.
- [x] 1.2 Repoint `--color-primary-disabled` to `color-mix(in srgb, var(--nw-action) 42%, white)` (matches `.nw-action:disabled`'s existing 0.42 opacity look).
- [x] 1.3 Leave `--color-on-primary`, `--color-primary-error-text`, and every component file untouched. (확인만, 코드 변경 없음.)

## 2. Verification

- [x] 2.1 Run dashboard tests, typecheck, and lint. — 117 tests passed, typecheck clean, lint clean.
- [x] 2.2 Browser-check that primary buttons/links/borders across at least one affected screen (e.g. Ask, Login) render in the `.nw-action` ink tone if credentials are available this session; otherwise static verification only (same caveat as prior changes in this session). — 이번 세션도 클라우드 Supabase 자격 증명 없음. 대신 `pnpm build`로 프로덕션 CSS를 실제로 컴파일하고, 빌드 산출물(`.next/static/css/*.css`)을 직접 파싱해 `--color-primary`의 최종 캐스케이드 승자가 `var(--nw-action)`(unlayered, design-tokens.css의 unlayered `:root`보다 소스상 뒤)임을 확인 — 브라우저 없이도 실제 컴파일된 CSS로 검증.
- [x] 2.3 Run `openspec validate unify-primary-action-color --strict`.
