/**
 * The evidence drill-down, as a full page.
 *
 * Reached from a behavioural relationship on the Insights page: it answers "why
 * did the system tell me this?" on its own screen, reusing `EvidencePanel` —
 * the same comparison, gates, supporting records and technical detail shown
 * inline, given room to breathe. It computes nothing; every figure is one the
 * engine produced.
 */

import type { Insight } from '../api/types';
import { EvidencePanel } from '../components/EvidencePanel';
import { formatCategory, formatHabit } from '../lib/format';
import { str } from '../lib/metrics';

export function Evidence({
  insight,
  onBack,
}: {
  insight: Insight | null;
  onBack: () => void;
}) {
  const habit = insight ? formatHabit(str(insight.metrics, 'habit')) : '';
  const category = insight ? formatCategory(str(insight.metrics, 'category')) : '';

  return (
    <>
      <header className="topbar">
        <div>
          <button
            type="button"
            className="btn btn--ghost btn--small"
            onClick={onBack}
            style={{ marginBottom: 10 }}
          >
            ← Back to Insights
          </button>
          <h1 className="topbar__title">Evidence</h1>
          <p className="topbar__subtitle">
            The observations and statistical result behind a validated insight — the finding, the
            records that support it, and a plain reminder that this is an association, not a cause.
          </p>
        </div>
      </header>

      {insight ? (
        <article className="card insight">
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
            {habit} is associated with {category} spending.
          </h3>
          <EvidencePanel insight={insight} />
        </article>
      ) : (
        <div className="card">
          <div className="state">
            <p className="state__title">No insight selected</p>
            <p className="state__detail">
              Evidence pages open from a validated insight. Choose one on the Insights page to
              inspect the records and the statistical result behind it.
            </p>
            <button type="button" className="state__action" onClick={onBack}>
              Go to Insights
            </button>
          </div>
        </div>
      )}
    </>
  );
}
