/**
 * A behavioural relationship (tier T3), elevated.
 *
 * This is the claim the whole engine exists to make responsibly, so the card
 * carries more than prose: the habit↔category pair, the observed direction and
 * magnitude, the period and sample size, the plain-language explanation the
 * narrator wrote, and — behind a toggle — the full evidence.
 *
 * Two labels are load-bearing. The confidence figure is titled "Statistical
 * confidence", never "AI confidence": it is evidence strength from a hypothesis
 * test, not the model's certainty about a sentence. And the claim is marked
 * "Association, not causation" in the card itself, because a percentage beside a
 * sentence reads as certainty about the sentence unless it is told otherwise
 * (constraint 5).
 */

import { useId, useState } from 'react';
import type { Insight, Metrics, MetricValue, Narration } from '../api/types';
import { formatCategory, formatHabit, formatPaise, formatRatio, pluralise } from '../lib/format';
import { num, str } from '../lib/metrics';
import { EvidencePanel } from './EvidencePanel';

function group(metrics: Metrics, key: string): Metrics | null {
  const value: MetricValue | undefined = metrics[key];
  if (typeof value === 'object' && value !== null && !Array.isArray(value)) return value;
  return null;
}

export function RelationshipCard({
  insight,
  narration,
  onOpenEvidence,
}: {
  insight: Insight;
  narration: Narration | undefined;
  /** When provided, offers a full-page evidence drill-down in addition to the
   *  inline expander. */
  onOpenEvidence?: (insight: Insight) => void;
}) {
  const [showEvidence, setShowEvidence] = useState(false);
  const regionId = useId();

  const metrics = insight.metrics;
  const habit = formatHabit(str(metrics, 'habit'));
  const category = formatCategory(str(metrics, 'category'));
  const observations = group(metrics, 'observations');
  const included = observations ? num(observations, 'included') : 0;
  const confidence = insight.confidence;

  return (
    <article className="card insight" aria-label={narration?.observation ?? `${habit} and ${category}`}>
      <div className="insight__top">
        <span className="chip chip--neutral" title="A statistical association, not a cause">
          <span className="chip__dot" aria-hidden="true" />
          Association
        </span>
        <span className="card__hint">
          {habit} ↔ {category}
        </span>
      </div>

      <h3 className="insight__observation">
        {narration?.observation ?? `${habit} is associated with ${category} spending.`}
      </h3>

      <div className="insight__section">
        <p className="insight__section-label">What we observed</p>
        <p className="insight__section-body">
          {formatPaise(num(metrics, 'difference_paise'))} per week difference
          {typeof metrics['relative_difference'] === 'number'
            ? ` (${formatRatio(num(metrics, 'relative_difference'))})`
            : ''}
          , across {pluralise(included, 'observation')}.
        </p>
      </div>

      {narration ? (
        <div className="insight__section">
          <p className="insight__section-label">What it means</p>
          <p className="insight__section-body">{narration.interpretation}</p>
        </div>
      ) : null}

      <div className="insight__confidence">
        {confidence !== null ? (
          <div
            className="confidence-meter"
            role="meter"
            aria-valuenow={Math.round(confidence * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Statistical confidence"
          >
            <div className="confidence-meter__fill" style={{ width: `${confidence * 100}%` }} />
          </div>
        ) : null}
        <p className="insight__confidence-text">
          <strong>Statistical confidence</strong>
          {confidence !== null ? ` ${formatRatio(confidence)}` : ''} — evidence strength from a
          hypothesis test, not the model's certainty. This is an association, not causation.
        </p>
      </div>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginTop: 12 }}>
        <button
          type="button"
          className="table-toggle"
          aria-expanded={showEvidence}
          aria-controls={regionId}
          onClick={() => setShowEvidence((open) => !open)}
        >
          {showEvidence ? 'Hide evidence' : 'Show evidence — why did the system tell me this?'}
        </button>
        {onOpenEvidence ? (
          <button type="button" className="table-toggle" onClick={() => onOpenEvidence(insight)}>
            Open full evidence →
          </button>
        ) : null}
      </div>

      {showEvidence ? <EvidencePanel insight={insight} regionId={regionId} /> : null}
    </article>
  );
}
