/**
 * Habit logging: completion, streaks, and per-habit coverage.
 *
 * The coverage bars carry the gate line at 60% because that is the threshold
 * the analysis engine uses to decide whether a habit can be tested at all —
 * it makes the chart answer "why is there no insight about my sleep?" without
 * anyone having to ask.
 *
 * A missing day is not a zero. The card says so, because the whole schema is
 * shaped around that distinction and a coverage bar is exactly where someone
 * would otherwise misread it.
 */

import type { Insight } from '../api/types';
import { formatHabit, formatRatio, pluralise } from '../lib/format';
import { num, rows, str } from '../lib/metrics';
import { BarChart, type BarRow } from './charts/BarChart';
import { ChartCard } from './Card';
import { DataTable } from './DataTable';
import { SummaryCard } from './SummaryCard';

const COVERAGE_GATE = 0.6;

export function HabitSummary({
  completion,
  streak,
}: {
  completion: Insight | null;
  streak: Insight | null;
}) {
  const completionRatio = completion ? num(completion.metrics, 'completion_ratio') : 0;
  const loggedDays = completion ? num(completion.metrics, 'logged_days') : 0;
  const windowDays = completion ? num(completion.metrics, 'window_days') : 0;

  const current = streak ? num(streak.metrics, 'current_logging_streak') : 0;
  const longest = streak ? num(streak.metrics, 'longest_logging_streak') : 0;
  const lastLogged = streak ? str(streak.metrics, 'last_logged_date') : '';

  return (
    <>
      <div className="span-4">
        <SummaryCard
          label="Check-in completion"
          value={formatRatio(completionRatio)}
          meta={`${loggedDays} of ${windowDays} days logged`}
        />
      </div>
      <div className="span-4">
        <SummaryCard
          label="Current streak"
          value={pluralise(current, 'day')}
          meta={
            current === 0 && lastLogged
              ? `Last check-in ${lastLogged}`
              : current === 0
                ? 'No check-ins yet'
                : 'Running to the end of the window'
          }
        />
      </div>
      <div className="span-4">
        <SummaryCard
          label="Longest streak"
          value={pluralise(longest, 'day')}
          meta={
            streak
              ? `Longest exercise run ${pluralise(
                  num(streak.metrics, 'longest_exercise_streak'),
                  'day',
                )}`
              : undefined
          }
        />
      </div>
    </>
  );
}

export function HabitCoverageCard({ completion }: { completion: Insight | null }) {
  const perHabit = completion ? rows(completion.metrics, 'per_habit') : [];

  const bars: BarRow[] = perHabit.map((row) => ({
    key: str(row, 'habit'),
    label: formatHabit(str(row, 'habit')),
    value: num(row, 'coverage_ratio'),
    display: formatRatio(num(row, 'coverage_ratio'), 0),
  }));

  return (
    <ChartCard
      title="Habit coverage"
      hint="per habit"
      tableLabel="table"
      table={
        <DataTable
          caption="Days each habit was recorded, out of the analysis window"
          columns={[
            { key: 'habit', header: 'Habit', render: (row) => formatHabit(str(row, 'habit')) },
            {
              key: 'recorded',
              header: 'Recorded',
              numeric: true,
              render: (row) => String(num(row, 'recorded_days')),
            },
            {
              key: 'unknown',
              header: 'Unknown',
              numeric: true,
              render: (row) => String(num(row, 'unknown_days')),
            },
            {
              key: 'coverage',
              header: 'Coverage',
              numeric: true,
              render: (row) => formatRatio(num(row, 'coverage_ratio'), 1),
            },
          ]}
          rows={perHabit}
        />
      }
      footnote="Coverage counts days you recorded a value. A day you did not log is unknown, not a zero — it is excluded from every habit figure rather than counted against you."
    >
      <BarChart
        rows={bars}
        ariaLabel="Coverage per habit, as a share of days in the analysis window"
        threshold={{ value: COVERAGE_GATE, label: '60% analysis gate' }}
      />
    </ChartCard>
  );
}
