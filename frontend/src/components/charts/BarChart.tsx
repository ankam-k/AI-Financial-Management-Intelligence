/**
 * Horizontal bars for a single measure across named rows.
 *
 * One series means one colour for every bar. Shading each bar darker-where-
 * bigger would double-encode length as hue and burn the only free channel on
 * information the bar already shows.
 *
 * Data-ends are rounded 4px and anchored to the baseline; a 2px surface gap
 * separates adjacent fills rather than a border drawn around them.
 */

import { ChartEmpty } from '../StateViews';

export interface BarRow {
  key: string;
  label: string;
  /** 0…1, from the backend. */
  value: number;
  display: string;
  /** Optional per-row colour for status rows; defaults to series slot 1. */
  color?: string;
}

interface Props {
  rows: BarRow[];
  ariaLabel: string;
  /** A reference line, e.g. the analysis coverage gate. 0…1. */
  threshold?: { value: number; label: string };
}

const ROW_HEIGHT = 30;
const BAR_HEIGHT = 9;
const LABEL_WIDTH = 128;
const VALUE_WIDTH = 54;
const RADIUS = 4;

/** A bar with only its data-end rounded, anchored flush to the baseline. */
function barPath(x: number, y: number, width: number, height: number): string {
  const radius = Math.min(RADIUS, width);
  if (width <= 0) return '';
  return [
    `M ${x} ${y}`,
    `H ${x + width - radius}`,
    `Q ${x + width} ${y} ${x + width} ${y + radius}`,
    `V ${y + height - radius}`,
    `Q ${x + width} ${y + height} ${x + width - radius} ${y + height}`,
    `H ${x}`,
    'Z',
  ].join(' ');
}

export function BarChart({ rows, ariaLabel, threshold }: Props) {
  if (rows.length === 0) {
    return <ChartEmpty>Nothing recorded in this window.</ChartEmpty>;
  }

  const height = rows.length * ROW_HEIGHT + 8;
  const width = 480;
  const trackStart = LABEL_WIDTH;
  const trackWidth = width - LABEL_WIDTH - VALUE_WIDTH;

  return (
    <svg
      className="chart"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={ariaLabel}
      preserveAspectRatio="xMinYMin meet"
    >
      {threshold ? (
        <>
          <line
            className="grid-line"
            x1={trackStart + trackWidth * threshold.value}
            x2={trackStart + trackWidth * threshold.value}
            y1={2}
            y2={height - 6}
          />
          <text
            x={trackStart + trackWidth * threshold.value + 4}
            y={height - 1}
            style={{ fontSize: 10 }}
          >
            {threshold.label}
          </text>
        </>
      ) : null}

      {rows.map((row, index) => {
        const y = index * ROW_HEIGHT + 6;
        const filled = Math.max(0, Math.min(1, row.value)) * trackWidth;
        return (
          <g key={row.key}>
            <text x={0} y={y + BAR_HEIGHT} style={{ fill: 'var(--text-secondary)', fontSize: 12 }}>
              {row.label}
            </text>
            <rect
              x={trackStart}
              y={y}
              width={trackWidth}
              height={BAR_HEIGHT}
              rx={RADIUS}
              fill="var(--surface-sunken)"
            />
            <path
              d={barPath(trackStart, y, filled, BAR_HEIGHT)}
              fill={row.color ?? 'var(--series-1)'}
            />
            <text
              x={width}
              y={y + BAR_HEIGHT}
              textAnchor="end"
              className="tick-label"
              style={{ fill: 'var(--text-primary)', fontSize: 12 }}
            >
              {row.display}
            </text>
          </g>
        );
      })}
    </svg>
  );
}
