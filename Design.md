# Design — AI Financial Intelligence Platform

> The visual system: color, theme, typography, components. The tokens below are
> the real ones from [`frontend/src/index.css`](frontend/src/index.css) — that
> file is the source of truth; keep this in sync. Fuller UX rationale is in
> [`docs/08_UI_UX.md`](docs/08_UI_UX.md).

## 1. Design principles

- **Colour never carries meaning alone.** Every donut segment is directly
  labelled in a list beside it; every chart has a table view; every status colour
  ships with an icon or word. This is a hard accessibility rule, not a preference.
- **Evidence is always reachable** — every relationship drills down to the numbers
  behind it.
- **Honest empty and error states** — say what's missing and what unlocks the next
  thing. An AI-unavailable state is first-class, not an afterthought.
- **Quiet, data-first surfaces** — restrained chrome so the numbers lead.

## 2. Theme

Light and dark, both hand-tuned (dark is a *selected* set, not an auto-inversion).
Theme resolves in three states: explicit `data-theme="light"` /
`data-theme="dark"`, and system default via `prefers-color-scheme`.

## 3. Colour tokens

### Surfaces & ink
| Token | Light | Dark |
|---|---|---|
| `--page` | `#f9f9f7` | `#0d0d0d` |
| `--surface` | `#fcfcfb` | `#1a1a19` |
| `--surface-sunken` | `#f2f2ee` | `#232322` |
| `--text-primary` | `#0b0b0b` | `#ffffff` |
| `--text-secondary` | `#52514e` | `#c3c2b7` |
| `--text-muted` | `#898781` | `#898781` |

### Chart chrome
`--grid`, `--baseline`, `--border` (`rgba` of ink at ~10%), `--border-strong` (~16–18%).

### Categorical series (fixed slot order — this order *is* the colourblind-safety mechanism)
| Slot | Light | Dark |
|---|---|---|
| `--series-1` | `#2a78d6` | `#3987e5` |
| `--series-2` | `#eb6834` | `#d95926` |
| `--series-3` | `#1baf7a` | `#199e70` |
| `--series-4` | `#eda100` | `#c98500` |
| `--series-5` | `#e87ba4` | `#d55181` |
| `--series-6` | `#008300` | `#008300` |
| `--series-other` | `#a8a69d` | `#6b6a64` |

Validated against the palette validator: passes the lightness band, chroma floor,
adjacent-CVD separation (worst ΔE 9.1 light / 8.4 dark) and normal-vision floor.
**Do not reorder or hand-pick series colours** — assign by slot. Light mode warns
on contrast for aqua/yellow/magenta below 3:1, which is exactly why the
direct-label + table-view relief rule is mandatory.

### Status (reserved — never reused as a series colour)
`--status-good #0ca30c` · `--status-warning #fab219` · `--status-serious #ec835a`
· `--status-critical #d03b3b` · `--success-text #006300` (light) / `#0ca30c` (dark).

## 4. Typography

- **Font:** `system-ui, -apple-system, 'Segoe UI', sans-serif` — no web-font
  dependency (matches the "add no dependencies" rule).
- **Base:** 15px / line-height 1.55.
- **Headings:** weight 600, `letter-spacing: -0.01em`. Topbar title 26px; brand
  22px/650; stat value 30px/650 `-0.02em`.
- **Numbers:** `font-variant-numeric: tabular-nums` in columns that align
  vertically (tables, legends, ticks); proportional for large standalone figures.

## 5. Shape, spacing, elevation

- Radius: `--radius 12px`, `--radius-sm 8px`; pills use `999px`.
- Shadow: `--shadow` — soft two-layer, lighter in light mode.
- Layout: `.shell` max-width 1240px; 12-column `.grid` with `span-*` helpers that
  collapse to full width at 1040px / 680px. Every grid child gets `min-width: 0`
  so wide content never pushes the page sideways; wide tables/charts scroll inside
  their own container.

## 6. Component vocabulary (in `index.css`)

Card · stat tile · status chip (dot + word) · progress bar · charts (with tooltip,
grid, table toggle) · legend / category list (the relief for sub-3:1 slots) ·
insight card (observation → evidence → suggestion → confidence meter) · event
timeline · chat (intro, log, turns, composer, typing dots) · empty/error/loading
states · buttons (`primary` / `ghost` / `danger` / `small`) · forms (field, hint,
error) · **three-state control** (Unknown is visually distinct — dashed border,
because it's a different *kind* of answer, not just another value) · AI
availability banner · evidence drill-down.

## 7. Interaction & accessibility rules

- Visible `:focus-visible` outline (2px `--series-1`) on every interactive
  element — **never removed**. Skip link present.
- `prefers-reduced-motion` collapses all animation/transition to ~0ms.
- Refetch **dims** the previous render (`.is-refetching`) instead of flashing a
  skeleton, so nothing jumps.
- Typing indicator is three dots (a skeleton would imply a known answer shape).
- `.visually-hidden` for screen-reader-only labels.

## 8. When adding UI

1. Reuse existing tokens and component classes; don't introduce new raw colours.
2. Assign categorical colours by slot order, never by taste.
3. Pair every colour signal with text/icon and give charts a table view.
4. Verify both themes and keyboard focus before calling it done.
