# ADR 029: Design refresh (purple palette and dots sphere)

## Status
Accepted (2026-10-21). The owner chose the look from mock-ups ("1 number ch better", "to sphere medium theva", sphere on the landing and sign-in pages, stable after sign-in) and approved the change with "ho kara".

## Context
The product looked plain (blue, no motion). The owner wanted a premium, futuristic first impression and a calm, stable app after sign-in. The change must not touch behaviour: no API, database, permission or search logic.

## Decision
- **One palette everywhere** through the existing theme tokens in `app/globals.css`: dark violet-black base (`#0B0A12`), purple accent (`#8B5CF6`), light purple hover and links (`#B69CFF`). Component code keeps using the same token names, so no screen needed rewriting. Contrast was checked: dark button text on the purple accent is 4.65:1, muted text on the surface 7.7:1.
- **Dots sphere** (`app/_components/DotsSphere.tsx`, maths in `lib/sphere.ts`): about 5,600 glowing dots (2,200 on phones, 3,800 on tablets), pink at the top, purple in the middle, blue-violet at the bottom. When the page opens the dots fly in from both sides and form the sphere; then it turns slowly and tilts a little towards the mouse. Medium size (radius at most 290 px).
- **Where:** the landing hero and the sign-in pages (sign in, forgot password, reset password) only. After sign-in there is no background animation, only 150 ms colour and border transitions on links, buttons and fields.
- **Safe by design:** `aria-hidden`, ignores keyboard and mouse input, pauses when the tab is hidden or scrolled out of view, one still picture for people who asked for reduced motion, capped pixel ratio, no network calls, no data.
- Landing text, sections and buttons are unchanged.

## Consequences
- The hero uses a left-to-right dark gradient over the sphere so the headline stays readable.
- Pre-existing issue found (not caused by this change): the Phase 1 landing components use the `motion` library's `useReducedMotion()` while rendering, which mismatches server and browser output when reduced motion is on (backlog 30).
