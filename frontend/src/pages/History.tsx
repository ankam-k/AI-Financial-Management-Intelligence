/**
 * History — one chronological stream of everything recorded.
 *
 * Expenses, daily check-ins and life events are three separate resources on the
 * backend; this page fetches all three and merges them into a single
 * date-sorted timeline, the way the prototype's `Store.History.all()` did. It is
 * a read-only view: no figure is derived here beyond rendering the paise the
 * backend already stored.
 */

import { useCallback, useMemo, useState } from 'react';
import { listCheckIns, listExpenses, listLifeEvents } from '../api/endpoints';
import type { CheckInRead } from '../api/types';
import { EmptyState, ErrorState, SkeletonCard } from '../components/StateViews';
import { useAsync } from '../hooks/useAsync';
import { formatCategory, formatDayShort, formatEventType, formatPaise } from '../lib/format';

type Kind = 'expense' | 'checkin' | 'event';

interface Item {
  kind: Kind;
  date: string;
  title: string;
  sub: string;
  amountPaise?: number;
}

const FILTERS: { key: 'all' | Kind; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'expense', label: 'Expenses' },
  { key: 'checkin', label: 'Check-ins' },
  { key: 'event', label: 'Life & Context' },
];

const TAG: Record<Kind, { label: string; cls: string }> = {
  expense: { label: 'Expense', cls: 'tag--expense' },
  checkin: { label: 'Check-in', cls: 'tag--checkin' },
  event: { label: 'Context', cls: 'tag--event' },
};

const PAGE = 15;

/** A short, honest one-liner: only fields the person actually recorded. */
function checkinSummary(c: CheckInRead): string {
  const parts: string[] = [];
  if (c.sleep_hours != null) parts.push(`Sleep ${c.sleep_hours}h`);
  if (c.exercise === true) parts.push('Exercised');
  else if (c.exercise === false) parts.push('No exercise');
  if (c.home_cooked_meals != null) parts.push(`${c.home_cooked_meals} home meals`);
  if (c.stress_level != null) parts.push(`Stress ${c.stress_level}/5`);
  if (c.work_mode) parts.push(formatEventType(c.work_mode));
  return parts.join(' · ') || 'Recorded, no items set';
}

export function History() {
  const state = useAsync(
    useCallback(async (signal: AbortSignal) => {
      const [expenses, checkins, events] = await Promise.all([
        listExpenses({ limit: 500 }, signal),
        listCheckIns(signal),
        listLifeEvents(signal),
      ]);
      return { expenses, checkins, events };
    }, []),
    [],
  );

  const [filter, setFilter] = useState<'all' | Kind>('all');
  const [visible, setVisible] = useState(PAGE);

  const items = useMemo<Item[]>(() => {
    if (!state.data) return [];
    const out: Item[] = [];
    for (const e of state.data.expenses) {
      out.push({
        kind: 'expense',
        date: e.expense_date,
        title: e.merchant || formatCategory(e.category),
        sub: formatCategory(e.category),
        amountPaise: e.amount_paise,
      });
    }
    for (const c of state.data.checkins) {
      out.push({ kind: 'checkin', date: c.log_date, title: 'Daily check-in', sub: checkinSummary(c) });
    }
    for (const ev of state.data.events) {
      out.push({ kind: 'event', date: ev.start_date, title: ev.title, sub: formatEventType(ev.event_type) });
    }
    return out.sort((a, b) => b.date.localeCompare(a.date));
  }, [state.data]);

  const filtered = filter === 'all' ? items : items.filter((item) => item.kind === filter);
  const shown = filtered.slice(0, visible);

  const changeFilter = (next: 'all' | Kind) => {
    setFilter(next);
    setVisible(PAGE);
  };

  return (
    <>
      <header className="topbar">
        <div>
          <h1 className="topbar__title">History</h1>
          <p className="topbar__subtitle">
            Everything you’ve recorded, newest first — expenses, check-ins and life events in one
            stream.
          </p>
        </div>
      </header>

      <div className="controls">
        <div className="control-group" role="group" aria-label="Filter history">
          {FILTERS.map((option) => (
            <button
              key={option.key}
              type="button"
              aria-pressed={filter === option.key}
              onClick={() => changeFilter(option.key)}
            >
              {option.label}
            </button>
          ))}
        </div>
      </div>

      <div className={state.isRefetching ? 'is-refetching' : undefined}>
        {state.error ? (
          <div className="card">
            <ErrorState error={state.error} onRetry={state.refetch} />
          </div>
        ) : state.isLoading ? (
          <SkeletonCard height={320} />
        ) : items.length === 0 ? (
          <div className="card">
            <EmptyState
              title="Nothing recorded yet"
              detail="Add an expense, do a daily check-in, or log a life event, and it will appear here."
            />
          </div>
        ) : filtered.length === 0 ? (
          <div className="card">
            <EmptyState
              title="Nothing in this category yet"
              detail="Switch the filter above, or record something of this type."
            />
          </div>
        ) : (
          <section className="card">
            <ul className="activity-list">
              {shown.map((item, index) => (
                <li className="activity-row" key={`${item.kind}-${item.date}-${index}`}>
                  <span className={`tag ${TAG[item.kind].cls}`}>{TAG[item.kind].label}</span>
                  <div className="activity-row__body">
                    <div className="activity-row__title">{item.title}</div>
                    <div className="activity-row__sub">
                      {item.kind === 'expense'
                        ? `${item.sub} · ${formatDayShort(item.date)}`
                        : item.sub}
                    </div>
                  </div>
                  <div className="activity-row__right">
                    {item.kind === 'expense' && item.amountPaise != null
                      ? formatPaise(item.amountPaise)
                      : formatDayShort(item.date)}
                  </div>
                </li>
              ))}
            </ul>

            {visible < filtered.length ? (
              <div style={{ textAlign: 'center', marginTop: 16 }}>
                <button
                  type="button"
                  className="btn btn--ghost"
                  onClick={() => setVisible((count) => count + PAGE)}
                >
                  Load more ({filtered.length - visible} left)
                </button>
              </div>
            ) : null}
          </section>
        )}
      </div>
    </>
  );
}
