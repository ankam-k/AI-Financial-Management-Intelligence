/**
 * Enum option lists for the data-entry selects.
 *
 * The canonical values live in the backend schema; these are the ordered
 * `{ value, label }` pairs a `<select>` needs, with human labels reusing the
 * same register as `format.ts`. Kept apart from `format.ts` because that module
 * is about rendering a value someone already chose, and this is about offering
 * the choices.
 */

import type { Category, EventType, PaymentMethod, WorkMode } from '../api/types';
import { formatCategory } from './format';

export interface Option<T extends string> {
  value: T;
  label: string;
}

const CATEGORY_VALUES: Category[] = [
  'FOOD_DINING',
  'GROCERIES',
  'TRANSPORT',
  'SHOPPING',
  'ENTERTAINMENT',
  'UTILITIES',
  'RENT_HOUSING',
  'HEALTH_FITNESS',
  'EDUCATION',
  'TRAVEL',
  'PERSONAL_CARE',
  'SUBSCRIPTIONS',
  'TRANSFERS',
  'INCOME',
  'FEES_CHARGES',
  'UNCATEGORIZED',
];

export const CATEGORY_OPTIONS: Option<Category>[] = CATEGORY_VALUES.map((value) => ({
  value,
  label: formatCategory(value),
}));

export const PAYMENT_METHOD_OPTIONS: Option<PaymentMethod>[] = [
  { value: 'UPI', label: 'UPI' },
  { value: 'CASH', label: 'Cash' },
  { value: 'DEBIT_CARD', label: 'Debit card' },
  { value: 'CREDIT_CARD', label: 'Credit card' },
  { value: 'BANK', label: 'Bank transfer' },
  { value: 'WALLET', label: 'Wallet' },
];

export const WORK_MODE_OPTIONS: Option<WorkMode>[] = [
  { value: 'OFFICE', label: 'Office' },
  { value: 'REMOTE', label: 'Remote' },
  { value: 'LEAVE', label: 'Leave' },
];

export const EVENT_TYPE_OPTIONS: Option<EventType>[] = [
  { value: 'TRAVEL', label: 'Travel' },
  { value: 'ILLNESS', label: 'Illness' },
  { value: 'JOB_CHANGE', label: 'Job change' },
  { value: 'RELOCATION', label: 'Relocation' },
  { value: 'FESTIVAL', label: 'Festival' },
  { value: 'FAMILY_EVENT', label: 'Family event' },
  { value: 'OTHER', label: 'Other' },
];

export const PAYMENT_METHOD_LABELS: Record<string, string> = Object.fromEntries(
  PAYMENT_METHOD_OPTIONS.map((option) => [option.value, option.label]),
);

export const WORK_MODE_LABELS: Record<string, string> = Object.fromEntries(
  WORK_MODE_OPTIONS.map((option) => [option.value, option.label]),
);

/** `"2026-08-13"` for an `<input type="date">` default, in local time. */
export function todayIso(): string {
  const now = new Date();
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}

/** `n` days before today, ISO. Used for the check-in backfill floor. */
export function isoDaysAgo(days: number): string {
  const now = new Date();
  now.setDate(now.getDate() - days);
  const offset = now.getTimezoneOffset() * 60_000;
  return new Date(now.getTime() - offset).toISOString().slice(0, 10);
}
