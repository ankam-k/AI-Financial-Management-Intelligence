/**
 * The spending charts, assembled from insights.
 *
 * Each panel reads one insight and renders it. The only transformation is
 * shape — a list of `{date, total_paise}` becomes a list of `{label, value}` —
 * never arithmetic. Shares, differences and directions all arrive computed.
 */

import type { Insight } from '../api/types';
import { formatCategory, formatDayShort, formatPaise, formatPaiseCompact, formatRatio } from '../lib/format';
import { num, rows, str } from '../lib/metrics';
import { ChartCard } from './Card';
import { DataTable } from './DataTable';
import { DonutChart, DonutLegend, type DonutSlice } from './charts/DonutChart';
import { LineChart, type LinePoint } from './charts/LineChart';

/** Fixed slot order. Colour follows the entity, never its rank in a filter. */
const SERIES = [
  'var(--series-1)',
  'var(--series-2)',
  'var(--series-3)',
  'var(--series-4)',
  'var(--series-5)',
  'var(--series-6)',
];

/**
 * Five coloured slices, so the "Other" arc brings the total to six — the point
 * past which a donut stops being readable at a glance. The remaining
 * categories are not lost; they are listed individually in the table view.
 */
const MAX_SLICES = 5;

export function SpendingTrendCard({ trend }: { trend: Insight | null }) {
  const series = trend ? rows(trend.metrics, 'series') : [];
  const points: LinePoint[] = series.map((row) => ({
    label: str(row, 'date'),
    value: num(row, 'total_paise'),
  }));

  const direction = trend ? str(trend.metrics, 'direction') : '';
  const busiest = trend ? str(trend.metrics, 'busiest_day') : '';

  return (
    <ChartCard
      title="Spending trend"
      hint={direction ? direction.toLowerCase() : undefined}
      tableLabel="daily table"
      table={
        <DataTable
          caption="Spending per day across the analysis window"
          columns={[
            { key: 'date', header: 'Date', render: (row) => str(row, 'date') },
            {
              key: 'total',
              header: 'Spent',
              numeric: true,
              render: (row) => formatPaise(num(row, 'total_paise')),
            },
          ]}
          rows={series}
        />
      }
      footnote={
        busiest
          ? `Heaviest day ${formatDayShort(busiest)} at ${formatPaise(
              trend ? num(trend.metrics, 'busiest_day_paise') : 0,
            )}. Days with no spending are shown as zero, not skipped.`
          : undefined
      }
    >
      <LineChart
        points={points}
        formatValue={formatPaise}
        formatTick={formatPaiseCompact}
        formatLabel={formatDayShort}
        ariaLabel="Daily spending across the analysis window"
      />
    </ChartCard>
  );
}

export function CategoryBreakdownCard({ breakdown }: { breakdown: Insight | null }) {
  const categories = breakdown ? rows(breakdown.metrics, 'categories') : [];
  const total = breakdown ? num(breakdown.metrics, 'total_paise') : 0;

  const head = categories.slice(0, MAX_SLICES);
  const tail = categories.slice(MAX_SLICES);

  const slices: DonutSlice[] = head.map((row, index) => ({
    key: str(row, 'category'),
    label: formatCategory(str(row, 'category')),
    share: num(row, 'share_ratio'),
    display: formatPaise(num(row, 'total_paise')),
    color: SERIES[index] ?? 'var(--series-other)',
  }));

  if (tail.length > 0) {
    // The arc is the leftover of the circle. The individual categories keep
    // their own backend-provided values in the table view; no summed figure
    // is derived here.
    const remainder = Math.max(0, 1 - slices.reduce((sum, slice) => sum + slice.share, 0));
    slices.push({
      key: '__other__',
      label: `${tail.length} smaller categor${tail.length === 1 ? 'y' : 'ies'}`,
      share: remainder,
      display: '—',
      color: 'var(--series-other)',
    });
  }

  return (
    <ChartCard
      title="Category breakdown"
      hint={categories.length ? `${categories.length} categories` : undefined}
      tableLabel="all categories"
      table={
        <DataTable
          caption="Spending by category across the analysis window"
          columns={[
            {
              key: 'category',
              header: 'Category',
              render: (row) => formatCategory(str(row, 'category')),
            },
            {
              key: 'total',
              header: 'Spent',
              numeric: true,
              render: (row) => formatPaise(num(row, 'total_paise')),
            },
            {
              key: 'share',
              header: 'Share',
              numeric: true,
              render: (row) => formatRatio(num(row, 'share_ratio')),
            },
            {
              key: 'count',
              header: 'Expenses',
              numeric: true,
              render: (row) => String(num(row, 'expense_count')),
            },
          ]}
          rows={categories}
        />
      }
      footnote="Transfers and income are excluded — moving money between your own accounts is not consumption."
    >
      <div className="donut-layout">
        <DonutChart
          slices={slices}
          centreValue={formatPaiseCompact(total)}
          centreLabel="total"
          ariaLabel="Share of spending by category"
        />
        <DonutLegend slices={slices} />
      </div>
    </ChartCard>
  );
}

export function PeriodComparisonCard({
  comparison,
  label,
}: {
  comparison: Insight | null;
  label: string;
}) {
  if (!comparison) return null;
  const metrics = comparison.metrics;
  const relative = typeof metrics['relative_change'] === 'number' ? num(metrics, 'relative_change') : null;
  const direction = str(metrics, 'direction');

  const periods = rows(metrics, 'periods');
  const maxTotal = Math.max(...periods.map((row) => num(row, 'total_paise')), 1);

  return (
    <ChartCard
      title={`${label} comparison`}
      hint={direction.toLowerCase()}
      tableLabel="table"
      table={
        <DataTable
          caption={`Complete ${label.toLowerCase()}s in the analysis window`}
          columns={[
            { key: 'period', header: label, render: (row) => str(row, 'period') },
            {
              key: 'total',
              header: 'Spent',
              numeric: true,
              render: (row) => formatPaise(num(row, 'total_paise')),
            },
            {
              key: 'count',
              header: 'Expenses',
              numeric: true,
              render: (row) => String(num(row, 'expense_count')),
            },
          ]}
          rows={periods}
        />
      }
      footnote={`Only complete ${label.toLowerCase()}s are compared, so this is not an artefact of where the window starts.`}
    >
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
          <span className="stat__value">{formatPaise(num(metrics, 'current_paise'))}</span>
          {relative !== null ? (
            <span
              style={{
                fontSize: 14,
                fontWeight: 600,
                color:
                  direction === 'INCREASED'
                    ? 'var(--status-critical)'
                    : direction === 'DECREASED'
                      ? 'var(--success-text)'
                      : 'var(--text-muted)',
              }}
            >
              {direction === 'INCREASED' ? '▲' : direction === 'DECREASED' ? '▼' : '■'}{' '}
              {formatRatio(Math.abs(relative))}
            </span>
          ) : null}
        </div>
        <p className="stat__meta" style={{ marginTop: 0 }}>
          {str(metrics, 'current_period')} vs {str(metrics, 'previous_period')} (
          {formatPaise(num(metrics, 'previous_paise'))})
        </p>

        <ul className="legend" style={{ marginTop: 4 }}>
          {periods.slice(-4).map((row) => (
            <li className="legend__row" key={str(row, 'period')} style={{ gap: 10 }}>
              <span className="legend__name" style={{ flex: '0 0 74px' }}>
                {str(row, 'period')}
              </span>
              <span
                aria-hidden="true"
                style={{
                  flex: 1,
                  height: 8,
                  borderRadius: 4,
                  background: 'var(--surface-sunken)',
                  position: 'relative',
                  overflow: 'hidden',
                }}
              >
                <span
                  style={{
                    display: 'block',
                    height: '100%',
                    borderRadius: 4,
                    width: `${(num(row, 'total_paise') / maxTotal) * 100}%`,
                    background: 'var(--series-1)',
                  }}
                />
              </span>
              <span className="legend__value">{formatPaise(num(row, 'total_paise'))}</span>
            </li>
          ))}
        </ul>
      </div>
    </ChartCard>
  );
}
