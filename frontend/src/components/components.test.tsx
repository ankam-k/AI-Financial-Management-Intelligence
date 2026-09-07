import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { BudgetProgress } from './BudgetProgress';
import { EventTimeline } from './EventTimeline';
import { HabitCoverageCard, HabitSummary } from './HabitCard';
import { InsightCard } from './InsightCard';
import { CategoryBreakdownCard, SpendingTrendCard } from './SpendingPanels';
import * as fixtures from '../test/fixtures';

describe('BudgetProgress', () => {
  it('shows the backend figures without recomputing them', () => {
    render(<BudgetProgress insight={fixtures.budgetUtilisation} />);

    expect(screen.getByText('41.0%')).toBeInTheDocument();
    expect(screen.getByText('₹16,420.00 spent')).toBeInTheDocument();
    expect(screen.getByText('₹40,000.00 budget')).toBeInTheDocument();
    expect(screen.getByText(/₹23,580.00 remaining/)).toBeInTheDocument();
  });

  it('exposes the meter to assistive technology', () => {
    render(<BudgetProgress insight={fixtures.budgetUtilisation} />);

    expect(screen.getByRole('meter', { name: 'Budget used' })).toHaveAttribute(
      'aria-valuenow',
      '41',
    );
  });

  it('labels the status with a word, never colour alone', () => {
    render(<BudgetProgress insight={fixtures.budgetUtilisation} />);

    expect(screen.getByText('Within budget')).toBeInTheDocument();
  });

  it('says no budget is set rather than estimating one', () => {
    render(<BudgetProgress insight={null} />);

    expect(screen.getByText(/No monthly budget set/)).toBeInTheDocument();
    expect(screen.getByText(/a budget you did not choose is not a budget/i)).toBeInTheDocument();
  });

  it('reports an overspend as an amount over, not a negative remainder', () => {
    const over = {
      ...fixtures.budgetUtilisation,
      metrics: {
        ...fixtures.budgetUtilisation.metrics,
        status: 'OVER_BUDGET',
        remaining_paise: -200_000,
        utilization_ratio: 1.05,
      },
    };
    render(<BudgetProgress insight={over} />);

    expect(screen.getByText('Over budget')).toBeInTheDocument();
    expect(screen.getByText(/₹2,000.00 over/)).toBeInTheDocument();
  });
});

describe('SpendingTrendCard', () => {
  it('renders a labelled chart', () => {
    render(<SpendingTrendCard trend={fixtures.dailyTrend} />);

    expect(
      screen.getByRole('img', { name: /daily spending across the analysis window/i }),
    ).toBeInTheDocument();
  });

  it('offers a table view so no value is hover-only', async () => {
    render(<SpendingTrendCard trend={fixtures.dailyTrend} />);

    await userEvent.click(screen.getByRole('button', { name: /show daily table/i }));

    const table = screen.getByRole('table');
    expect(within(table).getByText('₹900.00')).toBeInTheDocument();
    expect(within(table).getByText('2026-07-27')).toBeInTheDocument();
  });

  it('says days with no spending are zero, not skipped', () => {
    render(<SpendingTrendCard trend={fixtures.dailyTrend} />);

    expect(screen.getByText(/shown as zero, not skipped/)).toBeInTheDocument();
  });

  it('shows an empty state rather than an empty axis', () => {
    render(<SpendingTrendCard trend={null} />);

    expect(screen.getByText(/No spending recorded in this window/)).toBeInTheDocument();
  });
});

describe('CategoryBreakdownCard', () => {
  it('folds the tail so the donut never exceeds six segments', () => {
    render(<CategoryBreakdownCard breakdown={fixtures.categoryBreakdown} />);

    // Eight categories in; five coloured slices plus one "Other" arc out.
    // Past six segments a donut stops being readable at a glance.
    expect(screen.getByText('3 smaller categories')).toBeInTheDocument();
  });

  it('labels every segment with its value beside the chart', () => {
    // This is the relief the palette's light-mode contrast warning requires:
    // three slots sit below 3:1, so identity never rests on colour alone.
    render(<CategoryBreakdownCard breakdown={fixtures.categoryBreakdown} />);

    expect(screen.getByText('Food & dining')).toBeInTheDocument();
    expect(screen.getByText('₹8,200.00')).toBeInTheDocument();
  });

  it('lists every category in the table view, including the folded tail', async () => {
    render(<CategoryBreakdownCard breakdown={fixtures.categoryBreakdown} />);

    await userEvent.click(screen.getByRole('button', { name: /show all categories/i }));

    const table = screen.getByRole('table');
    expect(within(table).getByText('Personal care')).toBeInTheDocument();
    expect(within(table).getByText('₹100.00')).toBeInTheDocument();
  });

  it('explains why transfers and income are missing', () => {
    render(<CategoryBreakdownCard breakdown={fixtures.categoryBreakdown} />);

    expect(screen.getByText(/Transfers and income are excluded/)).toBeInTheDocument();
  });
});

describe('HabitSummary', () => {
  it('shows completion and both streaks', () => {
    render(
      <HabitSummary completion={fixtures.habitCompletion} streak={fixtures.habitStreak} />,
    );

    expect(screen.getByText('32.2%')).toBeInTheDocument();
    expect(screen.getByText('4 days')).toBeInTheDocument();
    expect(screen.getByText('29 days')).toBeInTheDocument();
  });
});

describe('HabitCoverageCard', () => {
  it('draws the analysis gate so a missing insight is explained', () => {
    render(<HabitCoverageCard completion={fixtures.habitCompletion} />);

    expect(screen.getByText('60% analysis gate')).toBeInTheDocument();
  });

  it('states that an unlogged day is unknown, not a zero', () => {
    render(<HabitCoverageCard completion={fixtures.habitCompletion} />);

    expect(screen.getByText(/unknown, not a zero/)).toBeInTheDocument();
  });

  it('separates recorded from unknown days in the table', async () => {
    render(<HabitCoverageCard completion={fixtures.habitCompletion} />);

    await userEvent.click(screen.getByRole('button', { name: /show table/i }));

    const table = screen.getByRole('table');
    expect(within(table).getByText('Unknown')).toBeInTheDocument();
    expect(within(table).getByText('Home-cooked meals')).toBeInTheDocument();
  });
});

describe('EventTimeline', () => {
  it('lists events with their own totals', () => {
    render(<EventTimeline events={[fixtures.eventSummary]} impact={fixtures.eventImpact} />);

    expect(screen.getByText('Goa trip')).toBeInTheDocument();
    expect(screen.getByText('₹6,850.00')).toBeInTheDocument();
  });

  it('compares per day, and says so', () => {
    render(<EventTimeline events={[fixtures.eventSummary]} impact={fixtures.eventImpact} />);

    expect(screen.getByText('During events')).toBeInTheDocument();
    expect(screen.getByText(/per day, not per total/)).toBeInTheDocument();
    expect(screen.getByText(/descriptive split, not a statistical test/)).toBeInTheDocument();
  });

  it('invites an annotation when there are no events', () => {
    render(<EventTimeline events={[]} impact={null} />);

    expect(screen.getByText('No life events in this window')).toBeInTheDocument();
  });
});

describe('InsightCard', () => {
  it('renders all five sections', () => {
    render(<InsightCard narration={fixtures.relationshipNarration} />);

    expect(screen.getByText(/Food & dining spending was higher/)).toBeInTheDocument();
    expect(screen.getByText('Evidence')).toBeInTheDocument();
    expect(screen.getByText('Interpretation')).toBeInTheDocument();
    expect(screen.getByText(/Confidence 99.9%/)).toBeInTheDocument();
    expect(screen.getByText(/worth watching food spending/)).toBeInTheDocument();
  });

  it('marks a correlational claim as an association', () => {
    render(<InsightCard narration={fixtures.relationshipNarration} />);

    expect(screen.getByText('Association')).toBeInTheDocument();
  });

  it('exposes confidence as a meter', () => {
    render(<InsightCard narration={fixtures.relationshipNarration} />);

    expect(screen.getByRole('meter', { name: 'Confidence' })).toHaveAttribute(
      'aria-valuenow',
      '100',
    );
  });

  it('shows no confidence meter for an arithmetic claim', () => {
    render(
      <InsightCard
        narration={{ ...fixtures.relationshipNarration, tier: 'T1', confidence_value: null }}
      />,
    );

    expect(screen.queryByRole('meter')).not.toBeInTheDocument();
    expect(screen.getByText('Measured')).toBeInTheDocument();
  });

  it('says where the words came from', () => {
    render(<InsightCard narration={fixtures.relationshipNarration} />);

    expect(screen.getByText('Written from a template')).toBeInTheDocument();
  });

  it('names the model when the prose was generated', () => {
    render(
      <InsightCard
        narration={{
          ...fixtures.relationshipNarration,
          source: 'LLM',
          model: 'ollama:qwen2.5:7b',
        }}
      />,
    );

    expect(screen.getByText('Generated by ollama:qwen2.5:7b')).toBeInTheDocument();
  });

  it('discloses a rejected generation rather than hiding it', () => {
    render(
      <InsightCard
        narration={{
          ...fixtures.relationshipNarration,
          validation_failures: [
            { validator: 'provenance', detail: "'evidence' contains 1 invented number" },
          ],
          fallback_reason: 'Generation rejected by 1 validator check(s).',
        }}
      />,
    );

    expect(screen.getByText(/A generated version was rejected \(1 check\)/)).toBeInTheDocument();
    expect(screen.getByText(/invented number/)).toBeInTheDocument();
  });
});
