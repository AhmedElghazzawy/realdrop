---
name: build-ui-component
description: Checklist for building a frontend component or page in RealDrop's terminal-editorial design system: tokens, states, accessibility, Turkish formatting, responsive checks. Use for every new UI component or screen.
---

# Build a UI component

1. **Read `docs/DESIGN_SYSTEM.md`.** Find the component in the table; if it exists there, match it. If it is new,
   add a row to the table first.
2. **Data contract:** props come from the generated API client types. Prices are kurus; never compute
   discounts in the frontend. Show `status`, `real_discount_pct`, `claim_inflated`, `tracked_since` as given.
3. **Build with tokens only** (CSS variables / Tailwind theme). No hard-coded hex values. Prices and
   numbers in the mono font with tabular figures.
4. **Implement all four states:** loading (skeleton), empty (helpful message and next action), error
   (what happened, retry), populated.
5. **Format with `Intl` (`tr-TR`):** currency `₺1.299,90`, percent `%24`, dates `24 Kas 2026`. Use the shared helpers.
6. **Accessibility:** semantic elements, labelled inputs, visible focus ring, 44 px touch targets,
   keyboard operation, text or icon next to any colour signal, AA contrast, `aria-live` for price updates.
7. **Motion:** 150-250 ms ease-out; a price change ticks once; respect `prefers-reduced-motion`.
8. **Turkish text check:** render `ığüşöçİĞÜŞÖÇ` and a long Turkish product title to catch overflow and glyph problems.
9. **Responsive check:** run `pnpm dev`, take Playwright screenshots at 375, 768 and 1280 px; look at them.
10. **Tests:** a component test for each state and one Playwright flow if it is a page.
11. **Run:** `pnpm lint && pnpm typecheck && pnpm test`. Commit: `feat(web): <component>`.
12. Tell the owner in 2-4 sentences which design or frontend principle the component illustrates.
