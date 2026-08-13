## 1. Route normalization

- [x] 1.1 Add a route-slug normalization boundary that accepts decoded and percent-encoded values without changing workspace or requester scoping.
- [x] 1.2 Return the existing generic wiki not-found state when the slug cannot be decoded safely.

## 2. Regression coverage

- [x] 2.1 Add route-level tests for ASCII, percent-encoded Hangul, and already-decoded mixed slugs.
- [x] 2.2 Add a malformed percent-encoding test that verifies no server error or page-data disclosure.
- [x] 2.3 Run the dashboard test suite, type check, and lint checks relevant to the route change.
