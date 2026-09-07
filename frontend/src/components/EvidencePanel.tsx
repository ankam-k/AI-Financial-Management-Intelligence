/**
 * The evidence behind a behavioural relationship.
 *
 * This is the differentiator: a user should be able to answer "why did the
 * system tell me this?" without trusting the AI. So it renders what the engine
 * actually compared — the two groups, their medians, the number of
 * observations, the period — reading straight from the insight's `metrics` and
 * `evidence[]`. Raw p- and q-values are real but secondary; they sit behind a
 * "Technical details" disclosure rather than leading, because a p-value up front
 * reads as the point when the effect size and the comparison are the point.
 *
 * Nothing here is computed. Every figure is a value the engine produced; this
 * decides only which ones to show and in what order.
 */

import type { Evidence, Insight, Metrics, MetricValue } from '../api/types';
import { formatDayLong, formatPaise, formatRatio, pluralise } from '../lib/format';
import { num, str } from '../lib/metrics';

function group(metrics: Metrics, key: string): Metrics | null {
  const value: MetricValue | undefined = metrics[key];
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) return value;
  return null;
}

function EvidenceRow({ item }: { item: Evidence }) {
  return (
    <li className="evidence__ref">
      <span className="evidence__ref-kind">{item.kind.replace(/_/g, ' ').toLowerCase()}</span>
      <span>{item.label}</span>
    </li>
  );
}

export function EvidencePanel({ insight, regionId }: { insight: Insight; regionId?: string }) {
  const metrics = insight.metrics;
  const groupA = group(metrics, 'group_a');
  const groupB = group(metrics, 'group_b');
  const stats = group(metrics, 'statistics');
  const observations = group(metrics, 'observations');

  const included = observations ? num(observations, 'included') : 0;
  const excluded = observations ? num(observations, 'excluded_unknown') : 0;
  const window = insight.window;

  const refs = insight.evidence.filter((item) => item.kind !== 'AGGREGATE');

  return (
    <div className="evidence" id={regionId}>
      <section className="evidence__section">
        <p className="insight__section-label">What was analysed</p>
        <p className="insight__section-body">
          {pluralise(included, 'observation')} over {formatDayLong(window.start)} –{' '}
          {formatDayLong(window.end)}
          {excluded > 0
            ? `. ${pluralise(excluded, 'day')} were excluded as unknown — not logged, so not counted either way.`
            : '.'}
        </p>
      </section>

      {groupA && groupB ? (
        <section className="evidence__section">
          <p className="insight__section-label">The comparison</p>
          <div className="evidence__groups">
            {[groupA, groupB].map((g, index) => (
              <div className="evidence__group" key={index}>
                <p className="evidence__group-label">{str(g, 'label')}</p>
                <p className="evidence__group-value">{formatPaise(num(g, 'median_paise'))}</p>
                <p className="stat__meta" style={{ margin: 0 }}>
                  median · {pluralise(num(g, 'n'), 'week')}
                </p>
              </div>
            ))}
          </div>
          <p className="stat__meta" style={{ marginTop: 8 }}>
            A difference of {formatPaise(num(metrics, 'difference_paise'))} per week
            {typeof metrics['relative_difference'] === 'number'
              ? ` (${formatRatio(num(metrics, 'relative_difference'))})`
              : ''}
            . Medians, not means, so a single unusual week cannot drive the result.
          </p>
        </section>
      ) : null}

      <section className="evidence__section">
        <p className="insight__section-label">Why it passed the gates</p>
        <p className="insight__section-body">
          This association cleared the engine's effect-size floor and survived
          Benjamini–Hochberg false-discovery correction across{' '}
          {stats ? pluralise(num(stats, 'hypotheses_tested'), 'hypothesis', 'hypotheses') : 'the run'}.
          Relationships that failed either gate were suppressed and are not shown.
        </p>
      </section>

      {refs.length > 0 ? (
        <section className="evidence__section">
          <p className="insight__section-label">Supporting records</p>
          <ul className="evidence__refs">
            {refs.map((item, index) => (
              <EvidenceRow item={item} key={item.ref_id ?? index} />
            ))}
          </ul>
        </section>
      ) : null}

      <section className="evidence__section">
        <p className="insight__section-label">Limitations</p>
        <p className="insight__section-body">
          This is an <strong>association, not causation</strong>. The two groups differ in more than
          the one habit measured, the sample is small, and a relationship in your recorded weeks may
          not hold in future ones. A life event is context around spending, never its cause.
        </p>
      </section>

      {stats ? (
        <details className="evidence__technical">
          <summary style={{ cursor: 'pointer' }}>Technical details</summary>
          <ul style={{ margin: '8px 0 0', paddingLeft: 18 }}>
            <li>Test: {str(stats, 'test').replace(/_/g, ' ')}</li>
            <li>p-value: {num(stats, 'p_value').toPrecision(2)}</li>
            <li>q-value (BH-FDR): {num(stats, 'q_value').toPrecision(2)}</li>
            <li>Hypotheses tested in run: {num(stats, 'hypotheses_tested')}</li>
          </ul>
        </details>
      ) : null}
    </div>
  );
}
