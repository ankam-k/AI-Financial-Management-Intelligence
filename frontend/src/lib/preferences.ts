/**
 * Human labels and ordered option lists for the V1.2 personalisation
 * vocabularies.
 *
 * The canonical values live in the backend (`app/domain/preferences.py`); these
 * are the `{ value, label }` pairs onboarding and Settings render, plus label
 * maps for read-only display. Kept apart from `enums.ts` only because these
 * describe *who the user is and what they want to track* — personalisation that
 * shapes the UI — rather than the enums a data-entry form must offer.
 *
 * None of these ever reaches the analysis engine; they change which cards lead
 * and which fields a check-in surfaces first, nothing more.
 */

import type {
  FocusArea,
  HabitField,
  HouseholdContext,
  IncomePattern,
  LifeStage,
  WorkContextPref,
} from '../api/types';
import type { Option } from './enums';

export const LIFE_STAGE_OPTIONS: Option<LifeStage>[] = [
  { value: 'STUDENT', label: 'Student' },
  { value: 'EARLY_CAREER', label: 'Working professional' },
  { value: 'ESTABLISHED', label: 'Established / senior' },
  { value: 'FAMILY', label: 'Family / household manager' },
];

export const INCOME_PATTERN_OPTIONS: Option<IncomePattern>[] = [
  { value: 'SALARIED_FIXED', label: 'Fixed monthly salary' },
  { value: 'SALARIED_VARIABLE', label: 'Salary + variable pay' },
  { value: 'SELF_EMPLOYED', label: 'Self-employed / business' },
  { value: 'IRREGULAR', label: 'Irregular / allowance' },
];

export const WORK_CONTEXT_OPTIONS: Option<WorkContextPref>[] = [
  { value: 'OFFICE', label: 'Office' },
  { value: 'REMOTE', label: 'Remote' },
  { value: 'HYBRID', label: 'Hybrid' },
  { value: 'FIELD', label: 'On the field' },
];

export const HOUSEHOLD_CONTEXT_OPTIONS: Option<HouseholdContext>[] = [
  { value: 'LIVING_ALONE', label: 'Living alone' },
  { value: 'WITH_FAMILY', label: 'With family' },
  { value: 'WITH_PARTNER', label: 'With a partner' },
  { value: 'SHARED', label: 'Shared / flatmates' },
];

export const FOCUS_AREA_OPTIONS: Option<FocusArea>[] = [
  { value: 'UNDERSTAND_SPENDING', label: 'Understand where my money goes' },
  { value: 'BUILD_HEALTHY_HABITS', label: 'See how habits relate to spending' },
  { value: 'REDUCE_STRESS_SPENDING', label: 'Notice stress-driven spending' },
  { value: 'SAVE_MORE', label: 'Spend more deliberately' },
];

/** The six trackable habits, labelled. Values are the check-in field names. */
export const HABIT_OPTIONS: Option<HabitField>[] = [
  { value: 'sleep_minutes', label: 'Sleep' },
  { value: 'exercise', label: 'Exercise' },
  { value: 'home_cooked_meals', label: 'Home-cooked meals' },
  { value: 'stress_level', label: 'Stress' },
  { value: 'alcohol', label: 'Alcohol' },
  { value: 'work_mode', label: 'Work mode' },
];

function labelMap<T extends string>(options: Option<T>[]): Record<string, string> {
  return Object.fromEntries(options.map((option) => [option.value, option.label]));
}

export const LIFE_STAGE_LABELS = labelMap(LIFE_STAGE_OPTIONS);
export const INCOME_PATTERN_LABELS = labelMap(INCOME_PATTERN_OPTIONS);
export const WORK_CONTEXT_LABELS = labelMap(WORK_CONTEXT_OPTIONS);
export const HOUSEHOLD_CONTEXT_LABELS = labelMap(HOUSEHOLD_CONTEXT_OPTIONS);
export const FOCUS_AREA_LABELS = labelMap(FOCUS_AREA_OPTIONS);
export const HABIT_LABELS = labelMap(HABIT_OPTIONS);
