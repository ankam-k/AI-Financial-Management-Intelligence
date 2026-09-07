/**
 * Spending over time. One series, so no legend — the card title names it.
 *
 * Mark spec: 2px line, hairline solid gridlines one shade off the surface, a
 * recessive axis, and selective direct labelling (the peak only — a number on
 * every point is chaos and goes unread). The crosshair and tooltip enhance;
 * the table view in the card header is what guarantees every value is
 * reachable without hovering.
 */

import { useMemo, useState } from 'react';
import { useElementWidth } from '../../hooks/useElementWidth';
import { ChartEmpty } from '../StateViews';

export interface LinePoint {
  label: string;
  value: number;
}

interface Props {
  points: LinePoint[];
  formatValue: (value: number) => string;
  formatTick: (value: number) => string;
  formatLabel: (label: string) => string;
  ariaLabel: string;
  height?: number;
}

const PAD = { top: 14, right: 16, bottom: 26, left: 60 };

/** A "nice" upper bound so gridlines land on round numbers. */
function niceMax(value: number): number {
  if (value <= 0) return 1;
  const magnitude = 10 ** Math.floor(Math.log10(value));
  const steps = [1, 2, 2.5, 5, 10];
  for (const step of steps) {
    const candidate = step * magnitude;
    if (candidate >= value) return candidate;
  }
  return 10 * magnitude;
}

export function LineChart({
  points,
  formatValue,
  formatTick,
  formatLabel,
  ariaLabel,
  height = 220,
}: Props) {
  const [ref, width] = useElementWidth<HTMLDivElement>();
  const [active, setActive] = useState<number | null>(null);

  const geometry = useMemo(() => {
    if (points.length === 0) return null;

    const plotWidth = Math.max(120, width - PAD.left - PAD.right);
    const plotHeight = height - PAD.top - PAD.bottom;
    const max = niceMax(Math.max(...points.map((point) => point.value)));

    const x = (index: number) =>
      PAD.left + (points.length === 1 ? plotWidth / 2 : (index / (points.length - 1)) * plotWidth);
    const y = (value: number) => PAD.top + plotHeight - (value / max) * plotHeight;

    const line = points.map((point, index) => `${x(index)},${y(point.value)}`).join(' ');
    const area = `${PAD.left},${PAD.top + plotHeight} ${line} ${x(points.length - 1)},${
      PAD.top + plotHeight
    }`;

    let peakIndex = 0;
    points.forEach((point, index) => {
      if (point.value > (points[peakIndex]?.value ?? 0)) peakIndex = index;
    });

    const ticks = [0, 0.25, 0.5, 0.75, 1].map((fraction) => ({
      value: max * fraction,
      y: PAD.top + plotHeight - fraction * plotHeight,
    }));

    return { plotWidth, plotHeight, max, x, y, line, area, peakIndex, ticks };
  }, [points, width, height]);

  if (!geometry) {
    return <ChartEmpty>No spending recorded in this window.</ChartEmpty>;
  }

  const { plotHeight, x, y, line, area, peakIndex, ticks } = geometry;
  const activePoint = active === null ? null : points[active];

  // The nearest point to the pointer, so the hit target is a vertical band
  // rather than a 2px line.
  const handleMove = (event: React.MouseEvent<SVGSVGElement>) => {
    const bounds = event.currentTarget.getBoundingClientRect();
    const offset = event.clientX - bounds.left - PAD.left;
    const step = geometry.plotWidth / Math.max(1, points.length - 1);
    const index = Math.round(offset / step);
    setActive(Math.max(0, Math.min(points.length - 1, index)));
  };

  return (
    <div className="chart-frame" ref={ref}>
      <svg
        className="chart"
        viewBox={`0 0 ${width} ${height}`}
        width={width}
        height={height}
        role="img"
        aria-label={ariaLabel}
        onMouseMove={handleMove}
        onMouseLeave={() => setActive(null)}
      >
        {ticks.map((tick) => (
          <g key={tick.value}>
            <line
              className="grid-line"
              x1={PAD.left}
              x2={width - PAD.right}
              y1={tick.y}
              y2={tick.y}
            />
            <text className="tick-label" x={PAD.left - 8} y={tick.y + 4} textAnchor="end">
              {formatTick(tick.value)}
            </text>
          </g>
        ))}

        <line
          className="axis-line"
          x1={PAD.left}
          x2={width - PAD.right}
          y1={PAD.top + plotHeight}
          y2={PAD.top + plotHeight}
        />

        <polyline points={area} fill="var(--series-1)" opacity="0.08" stroke="none" />
        <polyline
          points={line}
          fill="none"
          stroke="var(--series-1)"
          strokeWidth="2"
          strokeLinejoin="round"
          strokeLinecap="round"
        />

        {/* Selective direct label: the peak, and only the peak. */}
        {points.length > 2 ? (
          <circle
            cx={x(peakIndex)}
            cy={y(points[peakIndex]?.value ?? 0)}
            r="4"
            fill="var(--series-1)"
            stroke="var(--surface)"
            strokeWidth="2"
          />
        ) : null}

        {activePoint ? (
          <>
            <line
              className="axis-line"
              x1={x(active as number)}
              x2={x(active as number)}
              y1={PAD.top}
              y2={PAD.top + plotHeight}
            />
            <circle
              cx={x(active as number)}
              cy={y(activePoint.value)}
              r="5"
              fill="var(--series-1)"
              stroke="var(--surface)"
              strokeWidth="2"
            />
          </>
        ) : null}

        <text className="tick-label" x={PAD.left} y={height - 8} textAnchor="start">
          {formatLabel(points[0]?.label ?? '')}
        </text>
        {points.length > 1 ? (
          <text className="tick-label" x={width - PAD.right} y={height - 8} textAnchor="end">
            {formatLabel(points[points.length - 1]?.label ?? '')}
          </text>
        ) : null}
      </svg>

      {activePoint ? (
        <div
          className="tooltip"
          style={{ left: x(active as number), top: y(activePoint.value) - 10 }}
          role="presentation"
        >
          <span className="tooltip__label">{formatLabel(activePoint.label)}</span>
          <span className="tooltip__value">{formatValue(activePoint.value)}</span>
        </div>
      ) : null}
    </div>
  );
}
