# STATUS: Phase 1 (landing page): CLOSED

Signed off by the owner and tagged `v0.1` (9 Oct 2026). This file was corrected on 19 Oct 2026; it used to say "waiting for owner review".

## Done
- Next.js 16.4.0, React 19.3.0, Tailwind 4.3.3, TypeScript 5.9 (pinned) in `frontend/`.
- Design tokens in `frontend/app/globals.css` (FROZEN).
- Installed `motion` 14.x for interactions.
- Added smooth scrolling to `<html>`.
- Extracted interactive components to `_components/` (Server Component `page.tsx` preserved).
- Implemented `<GlowCard>` hover effects with `pointermove` radial glow (fixed for mouse).
- Implemented `<Reveal>` scroll animations with `<noscript>` fallback.
- Implemented `<HowItWorks>` scroll-linked step highlights.
- Implemented `<HeroDemo>` typing loop with hover pause and `sr-only` accessibility text.
- Implemented `<AnimatedButton>` click press feedback.
- Implemented `<InteractiveDemo>` with accessible tablist, selectable question chips, and cross-fading results.
- Implemented `<TourDialog>` native dialog with 60-second tour steps and animations.
- Ensured `useReducedMotion` is supported across all motion components.
- `npm run build` passes with no errors.
- Owner-measured Lighthouse on a production build (npm run start), mobile: Performance 99, Accessibility 96.

## In progress
- Nothing.

## Open issues (carried forward)
- `CONTACT_EMAIL` in `frontend/lib/site.ts` is still a placeholder (`you@example.com`). Tracked in `docs/BACKLOG.md`.
- Legal pages are drafts, not legal advice.
- The "Sign in" links now lead to the real login page (Phase 2C).
- Font is the system font stack. A self-hosted font with a licence check is optional later.

## Decisions made
- TypeScript pinned to 5.x (registry latest 7.x too new to vouch for).
- No ESLint in Layer 1 (add with CI in Phase 9).
