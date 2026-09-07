/**
 * "No reliable pattern yet" as a first-class answer, never a bare zero.
 *
 * When the engine surfaces no behavioural relationship, the reason is always in
 * the data it returned: too little history, a habit logged too rarely to test,
 * or hypotheses that all failed the effect-size or FDR gate. This reads those
 * reasons out of the `notices` and the `run` and states them — it never invents
 * one (constraint 5, PDR-030).
 */

import type { AnalysisRun, Insight } from '../api/types';
import { formatHabit, formatRatio, pluralise } from '../lib/format';
import { str } from '../lib/metrics';
import { Card } from './Card';

const GATE_LABEL: Record<string, string> = {
  G1_HISTORY: 'not enough history',
  G2_GROUP_SIZE: 'too few comparable weeks',
  G3_COVERAGE: 'logged too rarely to test',
  G4_EFFECT_SIZE: 'the difference was too small to be meaningful',
  G5_FDR: 'it did not survive multiple-comparison correction',
};

function noticeReason(notice: Insight): string {
  const gate = str(notice.metrics, 'failed_gate');
  const subject = str(notice.metrics, 'subject') || notice.subject || '';
  const label = GATE_LABEL[gate] ?? 'a data-sufficiency gate was not met';
  const subjectLabel = subject ? formatHabit(subject) : 'a habit';

  const current = notice.metrics['current_value'];
  const required = notice.metrics['required_value'];
  if (typeof current === 'number' && typeof required === 'number') {
    return `${subjectLabel}: ${label} (${formatRatio(current)} logged, needs ${formatRatio(
      required,
    )}).`;
  }
  return `${subjectLabel}: ${label}.`;
}

export function NoInsight({
  run,
  notices,
}: {
  run: AnalysisRun;
  notices: Insight[];
}) {
  const sufficiency = notices.filter((notice) => notice.type === 'DATA_SUFFICIENCY');

  return (
    <Card title="No behavioural relationship yet">
      <p className="insight__section-body">
        No reliable pattern yet — we need more recorded data before we can responsibly show a
        behavioural relationship. Here is exactly what the engine reported for this window:
      </p>

      {sufficiency.length > 0 ? (
        <ul style={{ margin: '12px 0 0', paddingLeft: 18 }}>
          {sufficiency.map((notice) => (
            <li key={notice.id} className="insight__section-body" style={{ marginBottom: 4 }}>
              {noticeReason(notice)}
            </li>
          ))}
        </ul>
      ) : (
        <p className="insight__section-body" style={{ marginTop: 12 }}>
          {run.hypotheses_tested > 0
            ? `${pluralise(
                run.hypotheses_tested,
                'association',
              )} were tested and ${run.relationships_suppressed} were suppressed — none cleared the effect-size and false-discovery gates, so none is shown.`
            : 'There was not yet enough overlapping habit and spending data to test any association.'}
        </p>
      )}

      <p className="stat__meta" style={{ marginTop: 14 }}>
        A missing insight is the product working as designed: it will not guess. Association, when
        one does surface, is never presented as cause.
      </p>
    </Card>
  );
}
