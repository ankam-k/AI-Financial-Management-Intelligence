/**
 * Category share, part-to-whole at a glance.
 *
 * Capped at six coloured segments with the tail folded into a neutral
 * "Other" — a donut stops being readable past that, and the ninth hue of a
 * validated palette does not exist. The exact numbers live in the legend
 * beside it, which is also the relief the palette's light-mode contrast
 * warning requires: three slots sit below 3:1 on the light surface, so every
 * segment is directly labelled and never identified by colour alone.
 *
 * The "Other" arc is drawn from the leftover of the circle. Its individual
 * categories keep their own backend-provided values in the legend and the
 * table; no summed figure is derived here.
 */

import { useState } from 'react';
import { ChartEmpty } from '../StateViews';

export interface DonutSlice {
  key: string;
  label: string;
  /** Fraction of the whole, from the backend. Never computed here. */
  share: number;
  /** Display string for the value, already formatted. */
  display: string;
  color: string;
}

interface Props {
  slices: DonutSlice[];
  centreValue: string;
  centreLabel: string;
  ariaLabel: string;
  size?: number;
}

const THICKNESS = 22;
/** The 2px surface gap between adjacent fills, expressed in degrees at render. */
const GAP_DEGREES = 1.6;

function arcPath(cx: number, cy: number, radius: number, from: number, to: number): string {
  const start = ((from - 90) * Math.PI) / 180;
  const end = ((to - 90) * Math.PI) / 180;
  const large = to - from > 180 ? 1 : 0;
  return [
    `M ${cx + radius * Math.cos(start)} ${cy + radius * Math.sin(start)}`,
    `A ${radius} ${radius} 0 ${large} 1 ${cx + radius * Math.cos(end)} ${cy + radius * Math.sin(end)}`,
  ].join(' ');
}

export function DonutChart({ slices, centreValue, centreLabel, ariaLabel, size = 190 }: Props) {
  const [active, setActive] = useState<string | null>(null);

  if (slices.length === 0) {
    return <ChartEmpty>No spending to break down yet.</ChartEmpty>;
  }

  const centre = size / 2;
  const radius = centre - THICKNESS / 2 - 2;

  let cursor = 0;
  const arcs = slices.map((slice) => {
    const sweep = slice.share * 360;
    const from = cursor;
    cursor += sweep;
    return { slice, from, to: from + sweep, sweep };
  });

  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <svg
        className="chart"
        viewBox={`0 0 ${size} ${size}`}
        width={size}
        height={size}
        role="img"
        aria-label={ariaLabel}
        style={{ flex: 'none' }}
      >
        {arcs.map(({ slice, from, to, sweep }) => {
          // Below the gap width the arc would vanish; draw it flush instead.
          const inset = sweep > GAP_DEGREES * 2 ? GAP_DEGREES / 2 : 0;
          return (
            <path
              key={slice.key}
              d={arcPath(centre, centre, radius, from + inset, Math.max(from + inset, to - inset))}
              fill="none"
              stroke={slice.color}
              strokeWidth={active === slice.key ? THICKNESS + 4 : THICKNESS}
              strokeLinecap="butt"
              opacity={active === null || active === slice.key ? 1 : 0.42}
              onMouseEnter={() => setActive(slice.key)}
              onMouseLeave={() => setActive(null)}
              style={{ transition: 'stroke-width 120ms ease, opacity 120ms ease' }}
            >
              <title>{`${slice.label}: ${slice.display}`}</title>
            </path>
          );
        })}

        <text
          x={centre}
          y={centre - 2}
          textAnchor="middle"
          style={{ fontSize: 19, fontWeight: 650, fill: 'var(--text-primary)' }}
        >
          {centreValue}
        </text>
        <text x={centre} y={centre + 16} textAnchor="middle" style={{ fontSize: 11 }}>
          {centreLabel}
        </text>
      </svg>
    </div>
  );
}

/** The legend beside the donut — identity by label, never by colour alone. */
export function DonutLegend({
  slices,
  shareLabel,
}: {
  slices: DonutSlice[];
  shareLabel?: (slice: DonutSlice) => string;
}) {
  return (
    <ul className="legend">
      {slices.map((slice) => (
        <li className="legend__row" key={slice.key}>
          <span className="legend__swatch" style={{ background: slice.color }} aria-hidden="true" />
          <span className="legend__name">{slice.label}</span>
          <span className="legend__value">{slice.display}</span>
          <span className="legend__share">
            {shareLabel ? shareLabel(slice) : `${(slice.share * 100).toFixed(1)}%`}
          </span>
        </li>
      ))}
    </ul>
  );
}
