## Context

See [proposal.md](proposal.md) for motivation. The workspace layout already owns the authenticated header and middleware remains the sole writer of auth cookies and the gate for `/w/*` routes. Existing browser-side Supabase usage establishes the session after password login.

## Goals / Non-Goals

**Goals:**

- Place session controls in the shared workspace header so they are available on every protected screen.
- End the session through the existing browser Auth client, then use a full navigation to observe the cleared session.
- Preserve the middleware as the authoritative post-logout route gate.

**Non-Goals:**

- Profile editing, avatars, account recovery, or organization administration.
- Changing provider configuration or adding OAuth.
- Displaying full account metadata in the navigation header.

## Decisions

### Supply minimal session identity from the server layout

The protected workspace layout will resolve the requester's current user once and pass only the display-safe identity needed by the header control. This avoids an extra client-side identity query and keeps the header consistent with the request that passed middleware. A client-side `getUser` alternative would introduce an avoidable loading state and duplicate session handling.

### Use an accessible menu action for logout

The header control will use the existing Radix menu conventions and an explicit `로그아웃` item, giving pointer and keyboard users the same action. The menu contains no sensitive profile details; email may be shown only when it is the minimal session identifier already present in the authenticated session.

### Sign out before full navigation

The action will await browser-client `signOut`, then navigate to `/login` with a full browser navigation. This mirrors the login flow's cookie-propagation safeguard and ensures server-rendered protected routes see the new anonymous request. A soft client router navigation is rejected because it can race session-cookie propagation.

## Risks / Trade-offs

- [Network failure prevents sign-out confirmation] → Keep the user on the current route and present a non-sensitive retry message.
- [An email address can be sensitive in a shared display] → Limit identity to an abbreviated or explicitly minimal display, with logout available regardless of whether identity is shown.
- [A stale client menu persists during navigation] → Disable the logout item while sign-out is pending.

## Migration Plan

1. Add the header account control and server-layout identity plumbing.
2. Add component and protected-route regression coverage.
3. Deploy without database or configuration migration; rollback by removing the account control while middleware protection remains unchanged.
