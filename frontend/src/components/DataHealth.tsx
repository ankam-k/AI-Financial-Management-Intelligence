/**
 * Insight readiness — whether the recorded data can support an analysis yet.
 *
 * Every judgement here is a COMPARISON of a backend-provided value against a
 * backend-provided gate threshold, never a statistic computed in React. The
 * history length and input counts come from `run`; the per-habit coverage comes
 * from the `HABIT_COMPLETION` insight; the thresholds come from `run.gates`.
 * The panel decides colour and wording for facts the engine already produced —
 * it invents no score of its own (PDR-030, constraint 4/6).
 */

import type { AnalysisRun, Insight } from '../api/types';
import { formatHabit, formatRatio, pluralise } from '../lib/format';
import { num, rows, str } from '../lib/metrics';
import { Card } from './Card';
import { StatusChip } from './SummaryCard';

/**
 * The coverage gate. Read from `run.gates` when the engine publishes it;
 * otherwise the value the sufficiency notices themselves report (0.6). Never a
 * figure invented here.
 */
function coverageGate(run: AnalysisRun): number {
  const published = run.gates['min_coverage_ratio'];
  return typeof published === 'number' ? published : 0.6;
}

interface Check {
  label: string;
  met: boolean;
  detail: string;
}

export function DataHealth({
  run,
  completion,
}: {
  run: AnalysisRun;
  completion: Insight | null;
}) {
  const minWeeks = run.gates['min_history_weeks'];
  const windowWeeks = Math.floor(run.window.days / 7);
  const gate = coverageGate(run);

  const checks: Check[] = [];

  if (typeof minWeeks === 'number') {
    checks.push({
      label: 'History length',
      met: windowWeeks >= minWeeks,
      detail: `${pluralise(windowWeeks, 'week')} in this window · needs ${pluralise(
        minWeeks,
        'week',
      )}`,
    });
  }

  checks.push({
    label: 'Recorded expenses',
    met: run.inputs.expenses > 0,
    detail: run.inputs.expenses > 0
      ? `${pluralise(run.inputs.expenses, 'expense')} recorded`
      : 'None recorded yet',
  });

  const perHabit = completion ? rows(completion.metrics, 'per_habit') : [];
  const habitsAtGate = perHabit.filter((row) => num(row, 'coverage_ratio') >= gate);

  const allMet = checks.every((check) => check.met) && habitsAtGate.length > 0;

  return (
    <Card
      title="Insight readiness"
      hint={allMet ? 'ready' : 'building up'}
      footnote={`Behavioural associations need at least ${
        typeof minWeeks === 'number' ? pluralise(minWeeks, 'complete week') : 'enough weeks'
      } of history and each habit logged on at least ${formatRatio(
        gate,
        0,
      )} of days. These are the engine's own gates, not thresholds set here.`}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12 }}>
        <StatusChip tone={allMet ? 'good' : 'warning'}>
          {allMet ? 'Ready for analysis' : 'Not enough data yet'}
        </StatusChip>
      </div>

      <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'grid', gap: 8 }}>
        {checks.map((check) => (
          <li
            key={check.label}
            style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}
          >
            <span>
              <span aria-hidden="true" style={{ marginRight: 6 }}>
                {check.met ? '✓' : '○'}
              </span>
              {check.label}
              <span className="visually-hidden">{check.met ? ' — met' : ' — not met'}</span>
            </span>
            <span className="stat__meta" style={{ margin: 0, textAlign: 'right' }}>
              {check.detail}
            </span>
          </li>
        ))}
      </ul>

      {perHabit.length > 0 ? (
        <>
          <p className="insight__section-label" style={{ marginTop: 16 }}>
            Habit coverage vs the {formatRatio(gate, 0)} gate
          </p>
          <ul style={{ listStyle: 'none', margin: '6px 0 0', padding: 0, display: 'grid', gap: 6 }}>
            {perHabit.map((row) => {
              const ratio = num(row, 'coverage_ratio');
              const met = ratio >= gate;
              return (
                <li
                  key={str(row, 'habit')}
                  style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}
                >
                  <span style={{ color: 'var(--text-secondary)' }}>
                    <span aria-hidden="true" style={{ marginRight: 6 }}>
                      {met ? '✓' : '○'}
                    </span>
                    {formatHabit(str(row, 'habit'))}
                  </span>
                  <span className="legend__value">{formatRatio(ratio, 0)}</span>
                </li>
              );
            })}
          </ul>
          {habitsAtGate.length === 0 ? (
            <p className="stat__meta" style={{ marginTop: 12 }}>
              Log any one habit more consistently to clear the gate and unlock its associations.
              A day you did not log is unknown, not a zero — it is excluded, not counted against you.
            </p>
          ) : null}
        </>
      ) : null}
    </Card>
  );
}
