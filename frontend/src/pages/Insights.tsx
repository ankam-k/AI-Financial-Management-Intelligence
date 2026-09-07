/**
 * The dedicated insights view.
 *
 * It groups what the engine found, and puts the behavioural relationships (tier
 * T3) first and largest, because they are the claims that most need their
 * evidence attached (constraint 3). Each relationship is a `RelationshipCard`
 * with an evidence drill-down; when none surface, `NoInsight` explains why from
 * the notices and run rather than showing a bare zero (constraint 5).
 *
 * A presentation layer: every figure and sentence came from the backend.
 */

import type { Insight } from '../api/types';
import type { AiAvailability } from '../components/AiStatusBanner';
import { AiStatusBanner } from '../components/AiStatusBanner';
import { InsightCard } from '../components/InsightCard';
import { NoInsight } from '../components/NoInsight';
import { RelationshipCard } from '../components/RelationshipCard';
import { EmptyState, ErrorState, SkeletonCard } from '../components/StateViews';
import { useDashboardData } from '../hooks/useDashboardData';
import { pickAll } from '../lib/metrics';

const SUMMARY_TYPES = new Set([
  'SPENDING_MONTHLY_COMPARISON',
  'SPENDING_WEEKLY_COMPARISON',
  'HABIT_COMPLETION',
  'HABIT_STREAK',
]);

export function Insights({
  days,
  generate,
  availability,
  onOpenEvidence,
}: {
  days: number;
  generate: boolean;
  availability: AiAvailability;
  /** Open the full-page evidence drill-down for one relationship. */
  onOpenEvidence?: (insight: Insight) => void;
}) {
  const { data, error, isLoading, isRefetching, refetch } = useDashboardData(days, generate);

  const relationships = data ? pickAll(data.analysis.insights, 'BEHAVIOR_RELATIONSHIP') : [];
  const eventNarrations =
    data?.narration.narrations.filter((n) => n.insight_type === 'EVENT_IMPACT') ?? [];
  const summaryNarrations =
    data?.narration.narrations.filter((n) => SUMMARY_TYPES.has(n.insight_type)) ?? [];

  const hasAnyData =
    data !== null &&
    (data.analysis.run.inputs.expenses > 0 ||
      data.analysis.run.inputs.check_ins > 0 ||
      data.analysis.run.inputs.events > 0);

  return (
    <>
      <header className="topbar">
        <div>
          <h1 className="topbar__title">Insights</h1>
          <p className="topbar__subtitle">
            What the analysis engine found in this window — with the evidence behind each claim.
          </p>
        </div>
      </header>

      <AiStatusBanner availability={availability} />

      <div className={isRefetching ? 'is-refetching' : undefined}>
        {error ? (
          <div className="card">
            <ErrorState error={error} onRetry={refetch} />
          </div>
        ) : isLoading ? (
          <div className="grid" aria-busy="true">
            <div className="span-6">
              <SkeletonCard height={200} />
            </div>
            <div className="span-6">
              <SkeletonCard height={200} />
            </div>
          </div>
        ) : !data ? null : !hasAnyData ? (
          <div className="card">
            <EmptyState
              title="Nothing to analyse yet"
              detail="Record some expenses and a few daily check-ins, and the engine will start reporting what it finds here."
            />
          </div>
        ) : (
          <div className="grid">
            <h2 className="section-heading">Behavioural relationships</h2>
            {relationships.length === 0 ? (
              <div className="span-12">
                <NoInsight run={data.analysis.run} notices={data.analysis.notices} />
              </div>
            ) : (
              relationships.map((insight) => (
                <div className="span-6" key={insight.id}>
                  <RelationshipCard
                    insight={insight}
                    narration={data.narrationFor(insight.id)}
                    onOpenEvidence={onOpenEvidence}
                  />
                </div>
              ))
            )}

            {eventNarrations.length > 0 ? (
              <>
                <h2 className="section-heading">Around your life events</h2>
                {eventNarrations.map((narration) => (
                  <div className="span-6" key={narration.insight_id}>
                    <InsightCard narration={narration} />
                  </div>
                ))}
              </>
            ) : null}

            {summaryNarrations.length > 0 ? (
              <>
                <h2 className="section-heading">Spending &amp; habits</h2>
                {summaryNarrations.map((narration) => (
                  <div className="span-6" key={narration.insight_id}>
                    <InsightCard narration={narration} />
                  </div>
                ))}
              </>
            ) : null}

            <p className="span-12 card__footnote" style={{ textAlign: 'center' }}>
              Engine {data.analysis.run.engine_version} · {data.analysis.run.hypotheses_tested}{' '}
              hypotheses tested · {data.analysis.run.relationships_suppressed} suppressed ·{' '}
              {data.narration.narration.generated} of {data.narration.narration.total} narrations
              model-written
            </p>
          </div>
        )}
      </div>
    </>
  );
}
