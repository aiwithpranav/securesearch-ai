# STATUS: Phase 1, Layer 1 (7 Oct 2026)

## Done
- Next.js 16.4.0, React 19.3.0, Tailwind 4.3.3, TypeScript 5.9 (pinned) in `frontend/`.
- Design tokens in `frontend/app/globals.css` (will be FROZEN when you approve Layer 1).
- Home page: hero, problem, how it works, static demo, first 2 minutes, security, features, teams, FAQ, final CTA, footer.
- Pages: /privacy, /terms, /security, 404, sitemap, robots, favicon, share image.
- `npm run build` passes (10 static pages).

## In progress
- Nothing. Layer 1 is waiting for owner review.

## Next step
- Owner reviews Layer 1. Then Layer 2 (motion): hover glow, scroll reveal, step highlight, hero demo loop.

## Open issues
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
