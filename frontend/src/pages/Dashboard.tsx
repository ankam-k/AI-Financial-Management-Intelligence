/**
 * The home dashboard.
 *
 * A presentation layer and nothing else. Every figure on this page was
 * computed by `app/analysis/`; every sentence was written by
 * `app/narration/`. This file decides layout, colour and wording of labels —
 * never a number.
 */

import { useMemo } from 'react';
import type { Insight } from '../api/types';
import { AiStatusBanner, type AiAvailability } from '../components/AiStatusBanner';
import { BudgetProgress } from '../components/BudgetProgress';
import { DataHealth } from '../components/DataHealth';
import { EventTimeline } from '../components/EventTimeline';
import { HabitCoverageCard, HabitSummary } from '../components/HabitCard';
import { InsightCard } from '../components/InsightCard';
import { NoInsight } from '../components/NoInsight';
import {
  CategoryBreakdownCard,
  PeriodComparisonCard,
  SpendingTrendCard,
} from '../components/SpendingPanels';
import { EmptyState, ErrorState, SkeletonCard } from '../components/StateViews';
import { SummaryCard } from '../components/SummaryCard';
import { useDashboardData } from '../hooks/useDashboardData';
import { formatDayLong, formatPaise, pluralise } from '../lib/format';
import { num, pick, pickAll } from '../lib/metrics';

/** Correlational findings first — prose helps most where a number alone would mislead. */
const TIER_ORDER: Record<string, number> = { T3: 0, T2: 1, T1: 2 };

export interface DashboardProps {
  days: number;
  generate: boolean;
  /** Optional so tests can render the page without wiring the status fetch. */
  availability?: AiAvailability;
  onOpenInsights?: () => void;
}

export function Dashboard({
  days,
  generate,
  availability = { available: true },
  onOpenInsights,
}: DashboardProps) {
  const { data, error, isLoading, isRefetching, refetch } = useDashboardData(days, generate);

  const insights: Insight[] = data?.analysis.insights ?? [];
  const notices: Insight[] = data?.analysis.notices ?? [];

  const total = pick(insights, 'SPENDING_TOTAL');
  const breakdown = pick(insights, 'SPENDING_BY_CATEGORY');
  const trend = pick(insights, 'SPENDING_DAILY_TREND');
  const monthly = pick(insights, 'SPENDING_MONTHLY_COMPARISON');
  const budget = pick(insights, 'BUDGET_UTILIZATION');
  const completion = pick(insights, 'HABIT_COMPLETION');
  const streak = pick(insights, 'HABIT_STREAK');
  const events = pickAll(insights, 'EVENT_SUMMARY');
  const impact = pick(insights, 'EVENT_IMPACT');

  /** Narrations worth surfacing as cards: findings and notices, not every total. */
  const insightCards = useMemo(() => {
    if (!data) return [];
    const interesting = new Set([
      'BEHAVIOR_RELATIONSHIP',
      'EVENT_IMPACT',
      'SPENDING_MONTHLY_COMPARISON',
      'SPENDING_WEEKLY_COMPARISON',
      'DATA_SUFFICIENCY',
    ]);
    return data.narration.narrations
      .filter((item) => interesting.has(item.insight_type))
      .sort((a, b) => (TIER_ORDER[a.tier] ?? 9) - (TIER_ORDER[b.tier] ?? 9));
  }, [data]);

  const hasAnyData =
    data !== null &&
    (data.analysis.run.inputs.expenses > 0 ||
      data.analysis.run.inputs.check_ins > 0 ||
      data.analysis.run.inputs.events > 0);

  return (
    <>
        <header className="topbar">
          <div>
            <h1 className="topbar__title">
              {data ? `${data.profile.display_name}'s finances` : 'Your finances'}
            </h1>
            <p className="topbar__subtitle">
              {data
                ? `${formatDayLong(data.analysis.run.window.start)} – ${formatDayLong(
                    data.analysis.run.window.end,
                  )}`
                : 'Loading your analysis window…'}
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
              <div className="span-3">
                <SkeletonCard height={60} />
              </div>
              <div className="span-3">
                <SkeletonCard height={60} />
              </div>
              <div className="span-3">
                <SkeletonCard height={60} />
              </div>
              <div className="span-3">
                <SkeletonCard height={60} />
              </div>
              <div className="span-8">
                <SkeletonCard height={220} />
              </div>
              <div className="span-4">
                <SkeletonCard height={220} />
              </div>
            </div>
          ) : !data ? null : !hasAnyData ? (
            <div className="card">
              <EmptyState
                title="Nothing recorded in this window yet"
                detail="Add an expense, log a daily check-in, or annotate a life event, and the analysis will start describing what it finds. It will not guess in the meantime."
              />
            </div>
          ) : (
            <div className="grid">
              {/* ── Monthly spending ─────────────────────────────────── */}
              <h2 className="section-heading">Spending</h2>

              <div className="span-3">
                <SummaryCard
                  label="Total spent"
                  value={formatPaise(total ? num(total.metrics, 'total_paise') : 0)}
                  meta={
                    total
                      ? `${pluralise(num(total.metrics, 'expense_count'), 'expense')} over ${pluralise(
                          num(total.metrics, 'window_days'),
                          'day',
                        )}`
                      : undefined
                  }
                />
              </div>
              <div className="span-3">
                <SummaryCard
                  label="Typical day"
                  value={formatPaise(total ? num(total.metrics, 'average_per_day_paise') : 0)}
                  meta={
                    total
                      ? `${formatPaise(
                          num(total.metrics, 'average_per_active_day_paise'),
                        )} on days you spent`
                      : undefined
                  }
                />
              </div>
              <div className="span-3">
                <SummaryCard
                  label="Largest expense"
                  value={formatPaise(total ? num(total.metrics, 'largest_expense_paise') : 0)}
                  meta={
                    total
                      ? `Median expense ${formatPaise(num(total.metrics, 'median_expense_paise'))}`
                      : undefined
                  }
                />
              </div>
              <div className="span-3">
                <BudgetProgress insight={budget} />
              </div>

              <div className="span-8">
                <SpendingTrendCard trend={trend} />
              </div>
              <div className="span-4">
                <PeriodComparisonCard comparison={monthly} label="Month" />
              </div>

              <div className="span-12">
                <CategoryBreakdownCard breakdown={breakdown} />
              </div>

              {/* ── Data health ──────────────────────────────────────── */}
              <h2 className="section-heading">Data health</h2>
              <div className="span-12">
                <DataHealth run={data.analysis.run} completion={completion} />
              </div>

              {/* ── Habits ───────────────────────────────────────────── */}
              <h2 className="section-heading">Habits</h2>
              <HabitSummary completion={completion} streak={streak} />
              <div className="span-12">
                <HabitCoverageCard completion={completion} />
              </div>

              {/* ── Events ───────────────────────────────────────────── */}
              <h2 className="section-heading">Life events</h2>
              <div className="span-12">
                <EventTimeline events={events} impact={impact} />
              </div>

              {/* ── AI insights ──────────────────────────────────────── */}
              <h2 className="section-heading">
                Insights
                {data.narration.narration.provider === 'none' ? (
                  <span
                    style={{
                      textTransform: 'none',
                      letterSpacing: 0,
                      fontWeight: 400,
                      marginLeft: 8,
                    }}
                  >
                    — written from templates; no model is configured
                  </span>
                ) : null}
              </h2>

              {insightCards.length === 0 ? (
                <div className="span-12">
                  <NoInsight run={data.analysis.run} notices={notices} />
                </div>
              ) : (
                <>
                  {insightCards.map((narration) => (
                    <div className="span-6" key={narration.insight_id}>
                      <InsightCard narration={narration} />
                    </div>
                  ))}
                  {onOpenInsights ? (
                    <div className="span-12" style={{ textAlign: 'center' }}>
                      <button type="button" className="btn btn--ghost" onClick={onOpenInsights}>
                        See all insights and evidence
                      </button>
                    </div>
                  ) : null}
                </>
              )}

              <p className="span-12 card__footnote" style={{ textAlign: 'center' }}>
                Engine {data.analysis.run.engine_version} ·{' '}
                {data.analysis.run.hypotheses_tested} hypotheses tested ·{' '}
                {data.analysis.run.relationships_suppressed} suppressed ·{' '}
                {data.narration.narration.generated} of {data.narration.narration.total} narrations
                model-written
              </p>
            </div>
          )}
        </div>
    </>
  );
}
