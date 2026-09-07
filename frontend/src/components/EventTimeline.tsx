/**
 * Life events, and what spending looked like around them.
 *
 * The during-versus-outside comparison is per day, because that is how the
 * backend computes it — a four-day trip will always total less than the other
 * eighty-six days, and showing totals would report that as spending less on
 * holiday.
 *
 * The card repeats the backend's own caveat: this is a descriptive split, not
 * a hypothesis test. Nothing here claims the event caused the spending.
 */

import type { Insight } from '../api/types';
import { formatDayLong, formatEventType, formatPaise, formatRatio, pluralise } from '../lib/format';
import { num, str } from '../lib/metrics';
import { Card } from './Card';
import { EmptyState } from './StateViews';

function eventRange(metrics: Insight['metrics']): string {
  const start = str(metrics, 'start_date');
  const end = str(metrics, 'end_date');
  if (!end || end === start) return formatDayLong(start);
  return `${formatDayLong(start)} – ${formatDayLong(end)}`;
}

export function EventTimeline({
  events,
  impact,
}: {
  events: Insight[];
  impact: Insight | null;
}) {
  if (events.length === 0) {
    return (
      <Card title="Life events">
        <EmptyState
          title="No life events in this window"
          detail="Annotating travel, illness or a relocation lets the analysis report spending around them separately, instead of leaving you to guess what a spike was."
        />
      </Card>
    );
  }

  return (
    <Card
      title="Life events"
      hint={pluralise(events.length, 'event')}
      footnote={
        impact
          ? 'Comparison is per day, not per total — a short event will always total less than the rest of the window. This is a descriptive split, not a statistical test.'
          : undefined
      }
    >
      {impact ? (
        <div
          style={{
            display: 'flex',
            gap: 20,
            flexWrap: 'wrap',
            paddingBottom: 14,
            marginBottom: 6,
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div>
            <p className="stat__label">During events</p>
            <p style={{ fontSize: 20, fontWeight: 650, margin: 0 }}>
              {formatPaise(num(impact.metrics, 'during_daily_paise'))}
              <span className="stat__meta"> / day</span>
            </p>
          </div>
          <div>
            <p className="stat__label">Ordinary days</p>
            <p style={{ fontSize: 20, fontWeight: 650, margin: 0 }}>
              {formatPaise(num(impact.metrics, 'outside_daily_paise'))}
              <span className="stat__meta"> / day</span>
            </p>
          </div>
          {typeof impact.metrics['relative_difference'] === 'number' ? (
            <div>
              <p className="stat__label">Difference</p>
              <p style={{ fontSize: 20, fontWeight: 650, margin: 0 }}>
                {formatRatio(num(impact.metrics, 'relative_difference'))}
                <span className="stat__meta">
                  {' '}
                  {str(impact.metrics, 'direction').toLowerCase()}
                </span>
              </p>
            </div>
          ) : null}
        </div>
      ) : null}

      <ul className="timeline">
        {events.map((event) => (
          <li className="timeline__item" key={event.id}>
            <span className="timeline__marker" aria-hidden="true" />
            <div className="timeline__head">
              <span className="timeline__title">{str(event.metrics, 'title')}</span>
              <span className="timeline__amount">
                {formatPaise(num(event.metrics, 'total_paise'))}
              </span>
            </div>
            <p className="timeline__meta">
              {formatEventType(str(event.metrics, 'event_type'))} · {eventRange(event.metrics)} ·{' '}
              {pluralise(num(event.metrics, 'event_days_in_window'), 'day')} in window ·{' '}
              {formatPaise(num(event.metrics, 'average_per_day_paise'))}/day
            </p>
          </li>
        ))}
      </ul>
    </Card>
  );
}
