# STATUS: Phase 1, Layer 3 (interactive demo)

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

## In progress
- Nothing. Layer 3 is waiting for owner review.

## Next step
- Owner reviews Layer 3 interactive demo and tour dialog.
- Set CONTACT_EMAIL in `frontend/lib/site.ts` (placeholder you@example.com).
- "Sign in" links to /login, which shows the 404 page until Phase 2.
- Font is the system font stack. Self-hosted font + licence check is optional later.
- Lighthouse not yet measured (needs your browser).
- Legal pages are drafts, not legal advice.

## Decisions made this session
- TypeScript pinned to 5.x (registry latest 7.x too new to vouch for).
- No ESLint in Layer 1 (keeps it compact; add with CI in Phase 9).

## Credentials/prerequisites still needed
- None.
