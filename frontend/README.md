# Frontend

React + TypeScript + Vite (ADR-012). A presentation layer over the existing
API — it performs no business logic and duplicates no calculation.

## Run it

```bash
# terminal 1 — the API
python -m uvicorn app.main:app --reload --app-dir backend

# terminal 2 — the dashboard
cd frontend && npm install && npm run dev     # → http://127.0.0.1:5173
```

The dev server proxies `/api` to `127.0.0.1:8000`, so the browser only ever
talks to one origin and **the backend needs no CORS configuration**. Point it
elsewhere with `VITE_API_TARGET`.

```bash
npm test        # 76 tests
npm run build   # 176 KB, 57 KB gzipped
npm run typecheck
```

## Layout

```
src/
├── api/          client.ts (fetch + ApiError) · endpoints.ts · types.ts
├── hooks/        useAsync · useDashboardData · useTheme · useElementWidth
├── lib/          format.ts (presentation) · metrics.ts (narrowed reads)
├── components/
│   ├── Card.tsx · DataTable.tsx · StateViews.tsx
│   ├── SummaryCard · BudgetProgress · HabitCard · InsightCard · EventTimeline
│   ├── SpendingPanels.tsx      panels that assemble charts from insights
│   └── charts/  LineChart · DonutChart · BarChart
└── pages/Dashboard.tsx
```

## What this layer may and may not do

**May:** render `412050` as `₹4,120.50`, label `FOOD_DINING` as "Food & dining",
turn a provided ratio into an arc angle, decide layout and colour.

**May not:** sum, difference, average, or derive any financial figure. Shares,
changes, directions and statuses all arrive computed from
`app/analysis/`; prose arrives written from `app/narration/`. `lib/format.ts`
holds that line and says so.

## Charts

No charting library. Four hand-written SVG components — a line, a donut,
horizontal bars, a progress meter — which is why the bundle is 176 KB with
accessibility built in rather than worked around. See
[ADR-017](../docs/11_Architecture_Decision_Records/ADR-017-dashboard-v1.md).

**Colour is validated, not chosen.** The six categorical slots are the
reference palette, checked in both light and dark for the lightness band,
chroma floor, colourblind separation (worst adjacent ΔE 9.1 light / 8.4 dark)
and normal-vision floor. Three light-mode slots sit below 3:1 contrast, which
obligates the relief rule — so every donut segment is directly labelled with
its value beside the chart, and colour never carries meaning alone.

**Every chart has a table view.** A tooltip enhances a value; it is never the
only way to read one.

## States

`useAsync` defines loading, error, empty and refetch once. Two behaviours
worth knowing: a refetch keeps the previous data and dims it rather than
flashing a skeleton, and a superseded response is discarded — a slow 90-day
request cannot land after a fast 30-day one and show the wrong window.

## Not built

Chat, recommendations, PDF export, forecasting, notifications. Generated
narration is opt-in via the filter row (`generate=false` by default) because a
local 7B model takes roughly 18 seconds per insight.
