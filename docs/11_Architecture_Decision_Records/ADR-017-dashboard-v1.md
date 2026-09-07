# ADR-017 — Dashboard V1: hand-rolled SVG charts, a dev proxy, and a validated palette

**Status:** Accepted · **Date:** 2026-07-28 · **Serves:** PDR-046🟠, SRS-2.5 · **Implements:** ADR-012

## Decision

Five decisions taken while building the dashboard (Sprint 4):

| # | Decision |
|---|---|
| 1 | **No charting library.** The four charts are hand-written SVG components. |
| 2 | **A Vite dev proxy**, so the browser sees one origin and the backend needs no CORS. |
| 3 | **The categorical palette is validated, not chosen.** Six slots, both modes, run through the palette checker. |
| 4 | **Every chart has a table view.** A tooltip may enhance a value; it may never be the only way to read one. |
| 5 | **Two requests, joined on content-addressed insight ids** — `/api/insights` for metrics, `/api/narrations` for prose. |

## Context

ADR-012 fixes React + TypeScript + Vite and leaves everything else open. The brief for this sprint is explicit that the dashboard is a presentation layer: it consumes existing APIs, performs no business logic, and duplicates no calculation. That constraint decides more of the design than any aesthetic preference — most of what a dashboard would normally compute (shares, differences, directions, statuses) already arrives computed, so the components are readers.

## Alternatives

**1. Recharts / Chart.js / visx versus hand-written SVG.** A library is the conventional answer and would have been faster to a first render. Against it: the four forms needed here are a line, a donut, horizontal bars and a progress meter — a few hundred lines of SVG between them. A library adds 150–400 KB to a 176 KB bundle, brings its own theming model to fight with the design tokens, and makes accessibility work *around* the library rather than in it. The finished bundle is **176 KB (57 KB gzipped)** and every chart carries an `aria-label`, a table twin and a keyboard-reachable toggle. Revisit if brushing, zooming, or dense scatter appears — that is where hand-rolling stops paying.

**2. Dev proxy versus CORS.** Enabling CORS on the backend for `localhost:5173` would work and would add a security-relevant configuration surface to a service that currently has none. The proxy keeps the browser on one origin, which is also how the deployed build will sit behind a single reverse proxy (`10_Deployment.md`), so development and production share a shape. **No backend change was needed for the frontend to exist.**

**3. Picking colours versus validating them.** The palette is the reference instance from the visualization method, run through its checker in both modes: lightness band, chroma floor, adjacent colourblind separation (worst ΔE 9.1 light / 8.4 dark), and normal-vision floor (19.6 / 19.3). Three light-mode slots fall below 3:1 contrast on the light surface, which obligates the relief rule — so every donut segment is directly labelled with its value in the list beside it, and identity never rests on colour. Slot order is the safety mechanism, not a style choice.

**4. One combined endpoint versus two requests.** A `/api/dashboard` returning metrics and prose together would halve the round trips and would put a presentation concern into the backend's URL space. Two parallel requests cost one round trip in wall-clock, and the join is free because insight ids are content-addressed: the same window produces the same ids in both responses. That property was built in Sprint 2 for reproducibility and turns out to pay here.

**5. Six donut slices versus five plus "Other".** Six coloured segments is the readable limit, and an "Other" arc is a seventh. Five coloured plus the fold keeps the total at six. The folded categories are not lost — each keeps its own backend-provided value in the table view.

## Tradeoffs

| Gain | Cost |
|---|---|
| 176 KB bundle; no chart-library API to theme around | Brushing, zoom and dense scatter would have to be written |
| Backend needs no CORS configuration | The dev proxy is a second place the API's location is written down |
| Colour is checked, not asserted; safe under CVD in both modes | Three light-mode slots need direct labels — the layout is not free to drop them |
| Every value reachable without a pointer | Each chart card carries a table twin to maintain |
| No presentation concern leaks into the API | Two requests, and `/api/narrations` re-runs the engine |

## Final Choice

**A reader, not a calculator.**

`lib/format.ts` holds the line: rendering `412050` as `₹4,120.50` is presentation of an integer the backend computed; deriving a new financial figure is analytics and does not happen here. The one place that came close — an "Other" donut arc — takes its *angle* from the leftover of the circle and shows no summed rupee figure at all.

`lib/metrics.ts` narrows every read out of an insight's `metrics` bag and returns a fallback rather than throwing, so a metric that changes shape degrades one card instead of blanking the dashboard.

## Consequences

- **`/api/narrations` re-runs the analysis engine**, so a dashboard load analyses the window twice. Milliseconds at V1 volumes; the fix, if it ever matters, is a cache keyed on the window rather than a combined endpoint.
- **Generated narration is opt-in.** `generate=false` is the default because a local 7B model takes ~18s per insight and a dashboard that waited would look broken. The toggle is in the filter row; template prose is identical in substance.
- **Adding a `Category` to the backend enum needs no frontend change** — `formatCategory` falls back to a de-slugged label, and the donut's sixth slot folds the tail.
- **A ninth categorical series does not exist.** Anything past the validated slots folds into "Other" or becomes a facet; generating a hue would break the checks the palette passes.
- **Screenshots in `docs/screenshots/` are generated by headless Chrome**, which on Windows clamps the viewport to ~485 CSS px. A narrower capture crops the render rather than reflowing it — the narrow screenshot is taken at 500 px for that reason, not because the layout stops there.
