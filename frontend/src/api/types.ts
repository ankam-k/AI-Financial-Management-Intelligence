/**
 * Response shapes, mirroring the backend schemas.
 *
 * `metrics` is deliberately typed as an index signature rather than a union of
 * fifteen exact shapes. The engine owns those shapes; restating them here
 * would create a second definition to keep in sync, and a mismatch would be a
 * TypeScript error rather than the missing-data case it actually is. Reading
 * is narrowed at the point of use instead (see `lib/metrics.ts`).
 */

export type MetricValue =
  | string
  | number
  | boolean
  | null
  | MetricValue[]
  | { [key: string]: MetricValue };

export type Metrics = Record<string, MetricValue>;

export interface Window {
  start: string;
  end: string;
  days: number;
}

export interface Evidence {
  kind: 'EXPENSE' | 'CHECK_IN' | 'LIFE_EVENT' | 'AGGREGATE';
  label: string;
  ref_id: string | null;
  payload: Metrics;
}

export type InsightTier = 'T1' | 'T2' | 'T3';

export type InsightType =
  | 'SPENDING_TOTAL'
  | 'SPENDING_BY_CATEGORY'
  | 'SPENDING_MONTHLY_COMPARISON'
  | 'SPENDING_WEEKLY_COMPARISON'
  | 'SPENDING_DAILY_TREND'
  | 'BUDGET_UTILIZATION'
  | 'HABIT_COMPLETION'
  | 'HABIT_STREAK'
  | 'HABIT_SLEEP_AVERAGE'
  | 'HABIT_EXERCISE_FREQUENCY'
  | 'HABIT_MISSED_DAYS'
  | 'EVENT_SUMMARY'
  | 'EVENT_IMPACT'
  | 'BEHAVIOR_RELATIONSHIP'
  | 'DATA_SUFFICIENCY';

export interface Insight {
  id: string;
  type: InsightType;
  tier: InsightTier;
  title_key: string;
  subject: string | null;
  window: Window;
  metrics: Metrics;
  evidence: Evidence[];
  confidence: number | null;
  created_at: string;
}

export interface AnalysisRun {
  engine_version: string;
  generated_at: string;
  window: Window;
  gates: Record<string, number>;
  hypotheses_tested: number;
  relationships_emitted: number;
  relationships_suppressed: number;
  insight_count: number;
  notice_count: number;
  inputs: { expenses: number; check_ins: number; events: number };
  currency: string;
}

export interface AnalysisResult {
  run: AnalysisRun;
  insights: Insight[];
  notices: Insight[];
}

export interface ValidationFailure {
  validator: string;
  detail: string;
}

export interface Narration {
  insight_id: string;
  insight_type: InsightType;
  tier: InsightTier;
  observation: string;
  evidence: string;
  interpretation: string;
  confidence: string;
  confidence_value: number | null;
  suggestion: string | null;
  source: 'LLM' | 'TEMPLATE';
  model: string | null;
  validation_failures: ValidationFailure[];
  fallback_reason: string | null;
}

export interface NarrationStats {
  total: number;
  generated: number;
  templated: number;
  generation_attempted: number;
  rejected_by_validation: number;
  provider: string;
  model: string;
}

export interface NarratedAnalysis {
  run: AnalysisRun;
  narration: NarrationStats;
  narrations: Narration[];
}

/* ── Personalisation vocabularies (V1.2) ──────────────────────────────────
 *
 * Closed sets mirroring `app/domain/preferences.py`. They shape the UI — which
 * cards lead, which categories a check-in surfaces first — and never reach the
 * analysis engine. The habit keys are the check-in model's field names
 * (`CheckIn.HABIT_FIELDS`), so `tracked_habits` lines up with what the engine
 * actually measures.
 */

export type LifeStage = 'STUDENT' | 'EARLY_CAREER' | 'ESTABLISHED' | 'FAMILY';

export type IncomePattern =
  | 'SALARIED_FIXED'
  | 'SALARIED_VARIABLE'
  | 'SELF_EMPLOYED'
  | 'IRREGULAR';

export type WorkContextPref = 'OFFICE' | 'REMOTE' | 'HYBRID' | 'FIELD';

export type HouseholdContext = 'LIVING_ALONE' | 'WITH_FAMILY' | 'WITH_PARTNER' | 'SHARED';

export type FocusArea =
  | 'UNDERSTAND_SPENDING'
  | 'BUILD_HEALTHY_HABITS'
  | 'REDUCE_STRESS_SPENDING'
  | 'SAVE_MORE';

/** The six habit keys, as stored in `tracked_habits`. */
export type HabitField =
  | 'sleep_minutes'
  | 'exercise'
  | 'home_cooked_meals'
  | 'stress_level'
  | 'alcohol'
  | 'work_mode';

export interface Profile {
  id: string;
  display_name: string;
  timezone: string;
  currency: string;
  monthly_budget_paise: number | null;
  /** V1.2: false until the user finishes (or skips) onboarding. */
  onboarding_completed: boolean;
  life_stage: LifeStage | null;
  income_pattern: IncomePattern | null;
  work_context: WorkContextPref | null;
  household_context: HouseholdContext | null;
  focus_areas: FocusArea[];
  tracked_categories: Category[];
  tracked_habits: HabitField[];
  created_at: string;
  updated_at: string;
}

/** The authenticated account, from `/api/auth/*`. No secrets. */
export interface AuthUser {
  id: string;
  email: string | null;
  display_name: string;
  is_demo: boolean;
  created_at: string;
}

/**
 * The onboarding payload and the personalisation half of a profile update.
 * Every field optional: a skipped step, or a partial edit, is expressible.
 */
export interface Personalisation {
  life_stage?: LifeStage | null;
  income_pattern?: IncomePattern | null;
  work_context?: WorkContextPref | null;
  household_context?: HouseholdContext | null;
  focus_areas?: FocusArea[];
  tracked_categories?: Category[];
  tracked_habits?: HabitField[];
}

export interface Citation {
  insight_id: string;
  insight_type: InsightType;
  tier: InsightTier;
}

export type AnswerStatus = 'ANSWERED' | 'REFUSED';

export type RefusalReason =
  | 'PROHIBITED_TOPIC'
  | 'NOT_ANSWERABLE_FROM_ANALYSIS'
  | 'INSUFFICIENT_DATA'
  | 'UNCLEAR';

export interface ChatResponse {
  question: string;
  status: AnswerStatus;
  answer: string;
  intent: string | null;
  refusal_reason: RefusalReason | null;
  source: 'LLM' | 'TEMPLATE';
  model: string | null;
  citations: Citation[];
  validation_failures: ValidationFailure[];
  fallback_reason: string | null;
  context_summary: Record<string, unknown>;
  window: Window;
}

export interface ChatCapabilities {
  examples: string[];
  intents: string[];
  max_question_chars: number;
  single_turn: boolean;
  note: string;
}

export interface DemoStatus {
  enabled: boolean;
  profile: string | null;
  expenses: number;
  check_ins: number;
  events: number;
  monthly_budget_paise: number | null;
  earliest: string | null;
  latest: string | null;
  is_empty: boolean;
}

export interface LLMStatus {
  provider: string;
  model: string;
  available: boolean;
  detail: string;
  narration_mode: 'GENERATED' | 'TEMPLATE';
}

/* ── Data-entry resources ─────────────────────────────────────────────────
 *
 * The write shapes (`*Create`, `*Update`) mirror the backend's Pydantic
 * schemas exactly. The read shapes add the server-owned fields — id, display
 * strings, timestamps — that a form never sends but a list always shows.
 */

export type Category =
  | 'FOOD_DINING'
  | 'GROCERIES'
  | 'TRANSPORT'
  | 'SHOPPING'
  | 'ENTERTAINMENT'
  | 'UTILITIES'
  | 'RENT_HOUSING'
  | 'HEALTH_FITNESS'
  | 'EDUCATION'
  | 'TRAVEL'
  | 'PERSONAL_CARE'
  | 'SUBSCRIPTIONS'
  | 'TRANSFERS'
  | 'INCOME'
  | 'FEES_CHARGES'
  | 'UNCATEGORIZED';

export type PaymentMethod = 'UPI' | 'CASH' | 'DEBIT_CARD' | 'CREDIT_CARD' | 'BANK' | 'WALLET';

export type WorkMode = 'OFFICE' | 'REMOTE' | 'LEAVE';

export type EventType =
  | 'TRAVEL'
  | 'ILLNESS'
  | 'JOB_CHANGE'
  | 'RELOCATION'
  | 'FESTIVAL'
  | 'FAMILY_EVENT'
  | 'OTHER';

export interface ExpenseCreate {
  expense_date: string;
  amount_paise: number;
  category: Category;
  payment_method: PaymentMethod;
  merchant?: string | null;
  notes?: string | null;
}

export interface ExpenseRead extends ExpenseCreate {
  id: string;
  amount_display: string;
  currency: string;
  created_at: string;
  updated_at: string;
}

/**
 * The three-state habit record.
 *
 * A field left off the object means "leave unchanged" (a PATCH), an explicit
 * `null` means "unknown / not logged", and a `false`/`0` is a recorded
 * negative. The distinction is the whole point of the schema; the forms above
 * it never collapse the first two into the third.
 */
export interface CheckInCreate {
  log_date: string;
  sleep_hours?: number | null;
  exercise?: boolean | null;
  home_cooked_meals?: number | null;
  stress_level?: number | null;
  alcohol?: boolean | null;
  work_mode?: WorkMode | null;
}

export interface CheckInRead {
  log_date: string;
  sleep_hours: number | null;
  exercise: boolean | null;
  home_cooked_meals: number | null;
  stress_level: number | null;
  alcohol: boolean | null;
  work_mode: WorkMode | null;
  created_at: string;
  updated_at: string;
}

export interface LifeEventCreate {
  event_type: EventType;
  title: string;
  start_date: string;
  end_date?: string | null;
  notes?: string | null;
}

export interface LifeEventRead extends LifeEventCreate {
  id: string;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdate extends Personalisation {
  display_name?: string;
  timezone?: string;
  monthly_budget_paise?: number | null;
}
