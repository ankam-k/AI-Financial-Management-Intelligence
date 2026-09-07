# ADR-012 — React + TypeScript + Vite

**Status:** Accepted · **Date:** 2026-07-27 · **Serves:** PDR-046🟠, PDR-006, NFR-2 · **Closes:** D-17

## Decision

**React 18 + TypeScript + Vite**, responsive web, no server-side rendering. State via TanStack Query for server state and local component state otherwise. No global state library in V1.

## Context

PDR-046🟠 excludes native mobile — V1 is responsive web. The frontend's job is narrow: upload flow, ledger view with drill-down, a daily check-in form, a life-event form, an insight feed with evidence expansion, and a single-turn Q&A box.

The dominant UI requirement comes from PDR-017: **every insight must drill to its supporting records in one interaction.** That is an interactive data-display problem, not a content-publishing problem.

## Alternatives

**A. Server-rendered templates (Jinja2 via FastAPI).** No separate build, no API duplication, fastest to ship. But insight drill-down, inline category correction, and the check-in form all want optimistic local interaction; full-page reloads make evidence exploration feel heavy, undermining the verification behavior PDR-045🟠 tracks as a success metric.

**B. HTMX + server templates.** A genuine middle path — much of the interactivity with far less machinery. Rejected narrowly: charting and the insight-evidence expansion still want component-level state, and TypeScript's type sharing with the API contract (`06_API_Design.md`) is worth more here than the simplicity saved.

**C. React + TypeScript + Vite.** Mature, well-documented, strong typing across the API boundary. Build tooling to maintain.

**D. Next.js.** SSR, routing, and more out of the box. Rejected as over-engineering: there is no SEO requirement (authenticated app), no SSR benefit for a single-user dashboard, and it adds a Node server to ADR-013's deployment.

**E. Vue / Svelte.** Both fine. React chosen for ecosystem depth around data-table and charting components, which is the bulk of this UI.

## Tradeoffs

| Gain | Cost |
|---|---|
| Component state suits insight/evidence expansion naturally | Separate build pipeline and dependency surface |
| TypeScript types mirror API schemas — contract drift caught at compile time | Types must be kept in sync with `06_API_Design.md` |
| Rich ecosystem for tables and charts | Larger bundle than templates or HTMX |
| Vite gives fast dev iteration | Another toolchain for a solo developer to maintain |
| No SSR server to operate | Initial load slower than server-rendered HTML |

## Final Choice

**React + TypeScript + Vite, no SSR, no global state library.**

Deliberately omitting Redux/Zustand: server state belongs in TanStack Query, and this app has almost no genuinely global client state. PDR-004's "avoid unnecessary abstractions" applies directly — adding a state library before there is state to manage is the kind of speculative complexity that instruction exists to prevent.

## Consequences

- Frontend is a static bundle served by any static host or a reverse proxy (ADR-013).
- API response types are generated from or manually mirrored against the OpenAPI schema; drift is a build failure.
- Responsive layout targets mobile browsers, satisfying PDR-046🟠's web-only constraint without a native app.
- No SEO considerations — the app is entirely behind authentication (ADR-011).
- If SSR is ever needed, migrating to Next.js is possible but would be a deliberate re-decision, not a drift.
- Charting library selection is deferred to `08_UI_UX.md`.
