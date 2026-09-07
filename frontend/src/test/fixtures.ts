/**
 * API fixtures, shaped exactly like real backend responses.
 *
 * Copied from live output rather than invented, so a test that passes here is
 * evidence the dashboard reads the contract the backend actually serves.
 */

import type {
  AnalysisResult,
  AuthUser,
  CheckInRead,
  ExpenseRead,
  Insight,
  LifeEventRead,
  LLMStatus,
  NarratedAnalysis,
  Narration,
  Profile,
} from '../api/types';

export const profile: Profile = {
  id: 'a1b2c3',
  display_name: 'Pranay',
  timezone: 'Asia/Kolkata',
  currency: 'INR',
  monthly_budget_paise: 4_000_000,
  onboarding_completed: true,
  life_stage: 'EARLY_CAREER',
  income_pattern: 'SALARIED_FIXED',
  work_context: 'HYBRID',
  household_context: 'LIVING_ALONE',
  focus_areas: ['UNDERSTAND_SPENDING'],
  tracked_categories: ['FOOD_DINING', 'TRANSPORT'],
  tracked_habits: ['sleep_minutes', 'exercise'],
  created_at: '2026-07-28T00:00:00',
  updated_at: '2026-07-28T00:00:00',
};

export const authUser: AuthUser = {
  id: 'a1b2c3',
  email: 'user-a@afi.test',
  display_name: 'Pranay',
  is_demo: false,
  created_at: '2026-07-28T00:00:00',
};

const window = { start: '2026-04-30', end: '2026-07-28', days: 90 };

function insight(partial: Partial<Insight> & Pick<Insight, 'id' | 'type' | 'tier' | 'metrics'>): Insight {
  return {
    title_key: partial.type,
    subject: null,
    window,
    evidence: [{ kind: 'AGGREGATE', label: 'total', ref_id: null, payload: {} }],
    confidence: null,
    created_at: '2026-07-28T09:00:00+05:30',
    ...partial,
  };
}

export const spendingTotal = insight({
  id: 'total-1',
  type: 'SPENDING_TOTAL',
  tier: 'T1',
  metrics: {
    total_paise: 1_642_000,
    expense_count: 12,
    window_days: 90,
    active_days: 12,
    average_per_day_paise: 18_244,
    average_per_active_day_paise: 136_833,
    average_per_expense_paise: 136_833,
    median_expense_paise: 136_000,
    largest_expense_paise: 615_000,
    by_payment_method: { UPI: 1_642_000 },
    excluded_non_spending_paise: 0,
    excluded_non_spending_count: 0,
    excluded_categories: ['INCOME', 'TRANSFERS'],
    currency: 'INR',
  },
});

export const categoryBreakdown = insight({
  id: 'cat-1',
  type: 'SPENDING_BY_CATEGORY',
  tier: 'T1',
  subject: 'FOOD_DINING',
  metrics: {
    total_paise: 1_642_000,
    category_count: 8,
    top_category: 'FOOD_DINING',
    top_category_paise: 820_000,
    top_category_share_ratio: 0.4994,
    currency: 'INR',
    categories: [
      { category: 'FOOD_DINING', total_paise: 820_000, expense_count: 5, share_ratio: 0.4994 },
      { category: 'TRANSPORT', total_paise: 320_000, expense_count: 2, share_ratio: 0.1949 },
      { category: 'GROCERIES', total_paise: 210_000, expense_count: 2, share_ratio: 0.1279 },
      { category: 'SHOPPING', total_paise: 140_000, expense_count: 1, share_ratio: 0.0853 },
      { category: 'UTILITIES', total_paise: 80_000, expense_count: 1, share_ratio: 0.0487 },
      { category: 'ENTERTAINMENT', total_paise: 42_000, expense_count: 1, share_ratio: 0.0256 },
      { category: 'SUBSCRIPTIONS', total_paise: 20_000, expense_count: 1, share_ratio: 0.0122 },
      { category: 'PERSONAL_CARE', total_paise: 10_000, expense_count: 1, share_ratio: 0.0061 },
    ],
  },
});

export const dailyTrend = insight({
  id: 'trend-1',
  type: 'SPENDING_DAILY_TREND',
  tier: 'T1',
  metrics: {
    window_days: 5,
    first_half_paise: 60_000,
    second_half_paise: 140_000,
    difference_paise: 80_000,
    relative_change: 1.3333,
    direction: 'INCREASED',
    stable_band: 0.05,
    busiest_day: '2026-07-27',
    busiest_day_paise: 90_000,
    zero_spend_days: 1,
    currency: 'INR',
    series: [
      { date: '2026-07-24', total_paise: 20_000 },
      { date: '2026-07-25', total_paise: 40_000 },
      { date: '2026-07-26', total_paise: 0 },
      { date: '2026-07-27', total_paise: 90_000 },
      { date: '2026-07-28', total_paise: 50_000 },
    ],
  },
});

export const budgetUtilisation = insight({
  id: 'budget-1',
  type: 'BUDGET_UTILIZATION',
  tier: 'T1',
  subject: '2026-07',
  metrics: {
    month: '2026-07',
    budget_paise: 4_000_000,
    spent_paise: 1_642_000,
    remaining_paise: 2_358_000,
    utilization_ratio: 0.4105,
    status: 'WITHIN_BUDGET',
    near_limit_threshold: 0.8,
    days_elapsed: 28,
    days_in_month: 31,
    month_start: '2026-07-01',
    as_of: '2026-07-28',
    covers_full_month_to_date: true,
    currency: 'INR',
  },
});

export const habitCompletion = insight({
  id: 'habits-1',
  type: 'HABIT_COMPLETION',
  tier: 'T1',
  metrics: {
    window_days: 90,
    logged_days: 29,
    unlogged_days: 61,
    completion_ratio: 0.3222,
    average_habit_coverage_ratio: 0.1074,
    per_habit: [
      { habit: 'sleep_minutes', recorded_days: 29, unknown_days: 61, coverage_ratio: 0.3222 },
      { habit: 'exercise', recorded_days: 29, unknown_days: 61, coverage_ratio: 0.3222 },
      { habit: 'home_cooked_meals', recorded_days: 0, unknown_days: 90, coverage_ratio: 0 },
      { habit: 'stress_level', recorded_days: 0, unknown_days: 90, coverage_ratio: 0 },
      { habit: 'alcohol', recorded_days: 0, unknown_days: 90, coverage_ratio: 0 },
      { habit: 'work_mode', recorded_days: 0, unknown_days: 90, coverage_ratio: 0 },
    ],
  },
});

export const habitStreak = insight({
  id: 'streak-1',
  type: 'HABIT_STREAK',
  tier: 'T1',
  metrics: {
    current_logging_streak: 4,
    longest_logging_streak: 29,
    longest_logging_streak_start: '2026-06-29',
    longest_logging_streak_end: '2026-07-27',
    current_exercise_streak: 0,
    longest_exercise_streak: 7,
    last_logged_date: '2026-07-28',
    window_end: '2026-07-28',
    streak_is_live: true,
    unknown_exercise_days: 61,
  },
});

export const eventSummary = insight({
  id: 'event-1',
  type: 'EVENT_SUMMARY',
  tier: 'T1',
  subject: 'evt-1',
  metrics: {
    event_id: 'evt-1',
    event_type: 'TRAVEL',
    title: 'Goa trip',
    start_date: '2026-07-10',
    end_date: '2026-07-13',
    is_point_event: false,
    event_days_total: 4,
    event_days_in_window: 4,
    total_paise: 685_000,
    expense_count: 3,
    average_per_day_paise: 171_250,
    top_category: 'TRAVEL',
    currency: 'INR',
    by_category: [{ category: 'TRAVEL', total_paise: 685_000 }],
  },
});

export const eventImpact = insight({
  id: 'impact-1',
  type: 'EVENT_IMPACT',
  tier: 'T2',
  metrics: {
    event_days: 4,
    ordinary_days: 86,
    during_total_paise: 685_000,
    outside_total_paise: 957_000,
    during_daily_paise: 171_250,
    outside_daily_paise: 11_128,
    difference_daily_paise: 160_122,
    relative_difference: 14.3891,
    direction: 'HIGHER',
    during_expense_count: 3,
    outside_expense_count: 9,
    event_count: 1,
    is_statistical_test: false,
    currency: 'INR',
  },
});

export const relationship = insight({
  id: 'rel-1',
  type: 'BEHAVIOR_RELATIONSHIP',
  tier: 'T3',
  subject: 'exercise:FOOD_DINING',
  confidence: 0.999,
  metrics: {
    habit: 'exercise',
    category: 'FOOD_DINING',
    higher_group: 'group_b',
    difference_paise: 201_000,
    relative_difference: 0.4939,
    stability_status: 'TENTATIVE',
    claim_type: 'ASSOCIATION',
    currency: 'INR',
    group_a: { label: 'weeks with exercise', n: 8, median_paise: 407_000, total_paise: 3_256_000 },
    group_b: { label: 'weeks without exercise', n: 8, median_paise: 608_000, total_paise: 4_864_000 },
    statistics: {
      test: 'mann_whitney_u',
      statistic: 0,
      p_value: 0.000939,
      q_value: 0.000939,
      hypotheses_tested: 28,
    },
    observations: { included: 16, excluded_unknown: 0, coverage_ratio: 1 },
  },
});

export const sufficiencyNotice = insight({
  id: 'notice-1',
  type: 'DATA_SUFFICIENCY',
  tier: 'T1',
  subject: 'exercise',
  metrics: {
    failed_gate: 'G3_COVERAGE',
    current_value: 0.4167,
    required_value: 0.6,
    subject: 'exercise',
  },
});

export const analysis: AnalysisResult = {
  run: {
    engine_version: '1.0.0',
    generated_at: '2026-07-28T09:00:00+05:30',
    window,
    gates: { min_history_weeks: 8, min_group_size: 6, fdr_q: 0.1 },
    hypotheses_tested: 28,
    relationships_emitted: 1,
    relationships_suppressed: 83,
    insight_count: 9,
    notice_count: 1,
    inputs: { expenses: 12, check_ins: 29, events: 1 },
    currency: 'INR',
  },
  insights: [
    spendingTotal,
    categoryBreakdown,
    dailyTrend,
    budgetUtilisation,
    habitCompletion,
    habitStreak,
    eventSummary,
    eventImpact,
    relationship,
  ],
  notices: [sufficiencyNotice],
};

function narration(partial: Partial<Narration> & Pick<Narration, 'insight_id' | 'insight_type' | 'tier'>): Narration {
  return {
    observation: 'Something was observed in your data.',
    evidence: 'The supporting figures sit behind this claim.',
    interpretation: 'This is what the pattern means, within the stated limits.',
    confidence: 'This is exact arithmetic over what you recorded.',
    confidence_value: null,
    suggestion: null,
    source: 'TEMPLATE',
    model: null,
    validation_failures: [],
    fallback_reason: null,
    ...partial,
  };
}

export const relationshipNarration = narration({
  insight_id: 'rel-1',
  insight_type: 'BEHAVIOR_RELATIONSHIP',
  tier: 'T3',
  observation: 'Food & dining spending was higher in weeks without exercise.',
  evidence: 'Weeks without exercise: ₹6,080.00 a week across 8 weeks.',
  interpretation: 'This is an association between exercise and food spending, not a cause.',
  confidence: 'Confidence 99.9%. It was one of 28 associations tested in this run.',
  confidence_value: 0.999,
  suggestion: 'You may find it worth watching food spending in weeks where exercise changes.',
});

export const narratedAnalysis: NarratedAnalysis = {
  run: analysis.run,
  narration: {
    total: 10,
    generated: 0,
    templated: 10,
    generation_attempted: 0,
    rejected_by_validation: 0,
    provider: 'none',
    model: 'none',
  },
  narrations: [
    relationshipNarration,
    narration({
      insight_id: 'impact-1',
      insight_type: 'EVENT_IMPACT',
      tier: 'T2',
      observation: 'Your daily spending during life events was higher than on ordinary days.',
    }),
    narration({
      insight_id: 'notice-1',
      insight_type: 'DATA_SUFFICIENCY',
      tier: 'T1',
      observation: 'No reliable conclusion can be drawn about exercise yet.',
    }),
    narration({ insight_id: 'total-1', insight_type: 'SPENDING_TOTAL', tier: 'T1' }),
  ],
};

export const chatAnswer = {
  question: 'How much did I spend?',
  status: 'ANSWERED' as const,
  answer: 'You spent ₹16,420.00 over the last 90 days across 12 expenses.',
  intent: 'SPENDING_SUMMARY',
  refusal_reason: null,
  source: 'TEMPLATE' as const,
  model: null,
  citations: [
    { insight_id: 'total-1', insight_type: 'SPENDING_TOTAL' as const, tier: 'T1' as const },
  ],
  validation_failures: [],
  fallback_reason: null,
  context_summary: { intent: 'SPENDING_SUMMARY', insight_count: 2 },
  window,
};

export const chatRefusal = {
  ...chatAnswer,
  question: 'Should I invest my savings?',
  status: 'REFUSED' as const,
  answer:
    "I can't help with that one. This assistant describes what you have already recorded.",
  intent: null,
  refusal_reason: 'PROHIBITED_TOPIC' as const,
  citations: [],
};

export const chatCapabilities = {
  examples: [
    'How much did I spend this month?',
    'Which category did I spend the most on?',
    'Am I over budget?',
    'How has my gym routine affected my spending?',
  ],
  intents: ['SPENDING_SUMMARY', 'BUDGET_STATUS', 'HABIT_RELATIONSHIP'],
  max_question_chars: 500,
  single_turn: true,
  note: 'No conversation history is kept on the server.',
};

export const llmStatusAvailable: LLMStatus = {
  provider: 'ollama',
  model: 'qwen2.5:7b',
  available: true,
  detail: 'ollama · qwen2.5:7b',
  narration_mode: 'GENERATED',
};

export const llmStatusUnavailable: LLMStatus = {
  provider: 'none',
  model: 'none',
  available: false,
  detail: 'No local model is configured.',
  narration_mode: 'TEMPLATE',
};

export const expensesList: ExpenseRead[] = [
  {
    id: 'exp-1',
    expense_date: '2026-07-27',
    amount_paise: 45_000,
    category: 'FOOD_DINING',
    payment_method: 'UPI',
    merchant: 'Blue Tokai',
    notes: null,
    amount_display: '₹450.00',
    currency: 'INR',
    created_at: '2026-07-27T10:00:00',
    updated_at: '2026-07-27T10:00:00',
  },
];

export const checkInsList: CheckInRead[] = [
  {
    log_date: '2026-07-28',
    sleep_hours: 7.5,
    exercise: true,
    home_cooked_meals: 2,
    stress_level: 3,
    alcohol: false,
    work_mode: 'REMOTE',
    created_at: '2026-07-28T21:00:00',
    updated_at: '2026-07-28T21:00:00',
  },
];

export const lifeEventsList: LifeEventRead[] = [
  {
    id: 'evt-1',
    event_type: 'TRAVEL',
    title: 'Goa trip',
    start_date: '2026-07-10',
    end_date: '2026-07-13',
    notes: null,
    created_at: '2026-07-01T00:00:00',
    updated_at: '2026-07-01T00:00:00',
  },
];

/** An analysis over a window with nothing in it. */
export const emptyAnalysis: AnalysisResult = {
  run: { ...analysis.run, inputs: { expenses: 0, check_ins: 0, events: 0 }, insight_count: 3 },
  insights: [],
  notices: [],
};

export const emptyNarration: NarratedAnalysis = {
  run: emptyAnalysis.run,
  narration: { ...narratedAnalysis.narration, total: 0, templated: 0 },
  narrations: [],
};
