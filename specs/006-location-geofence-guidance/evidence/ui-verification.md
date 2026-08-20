# UI Verification Evidence

- Verification date: 2026-08-20
- Scope: Feature 006 UI modernization

## Automated evidence

| Gate | Result | Coverage |
|---|---|---|
| Vitest | PASS — 62 files / 390 tests | Shared primitives/shell and responsive MobiFone logo; all GPS acquisition and presentation states; Location ordering, overlap, focus and disclosure; spatial semantics; Attendance CTA, outcomes, candidates, and fresh-punch separation. |
| Playwright Chromium | PASS | 13 semantic browser scenarios at 320, 375, 390, 430, 768, 1280 and 1440 CSS pixels. |
| Accessibility | PASS | Axe scan, keyboard/native semantics, visible focus, 44px targets, textual spatial alternative, color-independent status, reduced-motion behavior. |
| Responsive | PASS | No horizontal overflow; mobile bottom navigation switches to the same registry as a rail at 768px; CTA is reachable; spatial/details disclosures are closed by default. |
| Static checks | PASS | Prettier; ESLint with zero errors (27 warnings); TypeScript; OpenAPI drift; and Next production build with `/attendance` generated successfully. |

The final exact command outputs and test counts are produced by T206–T208. The
browser checks assert behavior and semantics, not pixel coordinates or a fixed
390px layout.

## Architecture and dependency evidence

- CSS custom properties are the only source of brand/status colors in the new
  shell, guidance, Attendance, and shared-component styles.
- The shared Button, Card, Badge, SectionHeading, and AsyncState patterns replace
  feature-local equivalents.
- Browser preview acquisition and authoritative Attendance acquisition remain
  separate. Presentation components consume calculated/server-returned state.
- Spatial guidance is a lazy local SVG composition. No map SDK, tile provider,
  iframe, external font, external position URL, or runtime map dependency was
  added.
- Playwright and axe are development-only test dependencies; the application
  runtime dependency set is unchanged.

## Outstanding human/external evidence

- T116/T116a and the SC-015 moderated legend trial require human participants and
  remain pending. Automated accessibility and browser checks do not substitute
  for those trials.
