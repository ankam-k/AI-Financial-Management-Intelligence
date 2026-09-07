/**
 * Budget usage.
 *
 * Every figure here — spent, budget, remaining, the ratio, the status — comes
 * from the `BUDGET_UTILIZATION` insight. The component picks a colour and a
 * word for the status the backend already decided; it never decides one.
 *
 * When no budget is set the insight is absent, and the card says so rather
 * than inventing a target from average spend.
 */

import type { Insight } from '../api/types';
import { formatPaise, formatRatio } from '../lib/format';
import { bool, num, str } from '../lib/metrics';
import { Card } from './Card';
import { StatusChip, type StatusTone } from './SummaryCard';

const STATUS: Record<string, { tone: StatusTone; text: string; fill: string }> = {
  WITHIN_BUDGET: { tone: 'good', text: 'Within budget', fill: 'progress__fill--good' },
  NEAR_LIMIT: { tone: 'warning', text: 'Near limit', fill: 'progress__fill--warning' },
  OVER_BUDGET: { tone: 'critical', text: 'Over budget', fill: 'progress__fill--critical' },
};

export function BudgetProgress({ insight }: { insight: Insight | null }) {
  if (!insight) {
    return (
      <Card title="Budget">
        <p className="stat__value stat__label" style={{ fontSize: 15, fontWeight: 500 }}>
          No monthly budget set.
        </p>
        <p className="stat__meta">
          Set one on your profile to see usage here. Nothing is estimated from your average
          spending — a budget you did not choose is not a budget.
        </p>
      </Card>
    );
  }

  const metrics = insight.metrics;
  const status = STATUS[str(metrics, 'status')] ?? {
    tone: 'neutral' as StatusTone,
    text: 'Tracking',
    fill: 'progress__fill--good',
  };
  const ratio = num(metrics, 'utilization_ratio');
  const remaining = num(metrics, 'remaining_paise');
  const partial = !bool(metrics, 'covers_full_month_to_date', true);

  return (
    <Card
      title="Budget usage"
      footnote={
        partial
          ? 'The analysis window starts mid-month, so this counts only the covered part.'
          : undefined
      }
    >
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, flexWrap: 'wrap' }}>
        <span className="stat__value">{formatRatio(ratio)}</span>
        <StatusChip tone={status.tone}>{status.text}</StatusChip>
      </div>

      <div style={{ marginTop: 14 }}>
        <div
          className="progress"
          role="meter"
          aria-valuenow={Math.round(ratio * 100)}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label="Budget used"
        >
          <div
            className={`progress__fill ${status.fill}`}
            style={{ width: `${Math.min(100, Math.max(0, ratio * 100))}%` }}
          />
        </div>
        <div className="progress-row">
          <span>{formatPaise(num(metrics, 'spent_paise'))} spent</span>
          <span>{formatPaise(num(metrics, 'budget_paise'))} budget</span>
        </div>
      </div>

      <p className="stat__meta" style={{ marginTop: 12 }}>
        {remaining >= 0
          ? `${formatPaise(remaining)} remaining`
          : `${formatPaise(Math.abs(remaining))} over`}
        {' · '}
        {num(metrics, 'days_elapsed')} of {num(metrics, 'days_in_month')} days
      </p>
    </Card>
  );
}
