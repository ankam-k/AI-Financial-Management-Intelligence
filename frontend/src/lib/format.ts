/**
 * Presentation formatting. **Not calculation.**
 *
 * The line this module holds: turning `412050` into `"₹4,120.50"` is
 * rendering an integer the backend already computed. Deriving a new financial
 * figure — a sum, a difference, a percentage of something — is analytics, and
 * belongs in `app/analysis/`. Nothing here does the second thing.
 *
 * The division by 100 is the paise→rupee unit conversion the backend
 * documents; it produces no new fact.
 */

const PAISE_PER_RUPEE = 100;

const rupeeFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const compactFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
});

/** `412050` → `"₹4,120.50"`. */
export function formatPaise(paise: number): string {
  return rupeeFormatter.format(paise / PAISE_PER_RUPEE);
}

/** `412050` → `"₹4,121"`. For axis ticks and dense labels. */
export function formatPaiseCompact(paise: number): string {
  return compactFormatter.format(paise / PAISE_PER_RUPEE);
}

/** `0.4939` → `"49.4%"`. The ratio comes from the backend; this only renders it. */
export function formatRatio(ratio: number, places = 1): string {
  return `${(ratio * 100).toFixed(places)}%`;
}

/** `"2026-06-21"` → `"21 Jun"`. */
export function formatDayShort(iso: string): string {
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat('en-IN', { day: 'numeric', month: 'short' }).format(date);
}

/** `"2026-06-21"` → `"21 Jun 2026"`. */
export function formatDayLong(iso: string): string {
  const date = new Date(`${iso}T00:00:00`);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat('en-IN', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(date);
}

/** `"2026-06"` → `"June 2026"`. */
export function formatMonth(key: string): string {
  const [year, month] = key.split('-');
  if (!year || !month) return key;
  const date = new Date(Number(year), Number(month) - 1, 1);
  if (Number.isNaN(date.getTime())) return key;
  return new Intl.DateTimeFormat('en-IN', { month: 'long', year: 'numeric' }).format(date);
}

/** `FOOD_DINING` → `Food & dining`. Labels only; the enum stays canonical. */
const CATEGORY_LABELS: Record<string, string> = {
  FOOD_DINING: 'Food & dining',
  GROCERIES: 'Groceries',
  TRANSPORT: 'Transport',
  SHOPPING: 'Shopping',
  ENTERTAINMENT: 'Entertainment',
  UTILITIES: 'Utilities',
  RENT_HOUSING: 'Rent & housing',
  HEALTH_FITNESS: 'Health & fitness',
  EDUCATION: 'Education',
  TRAVEL: 'Travel',
  PERSONAL_CARE: 'Personal care',
  SUBSCRIPTIONS: 'Subscriptions',
  TRANSFERS: 'Transfers',
  INCOME: 'Income',
  FEES_CHARGES: 'Fees & charges',
  UNCATEGORIZED: 'Uncategorised',
};

export function formatCategory(key: string): string {
  return CATEGORY_LABELS[key] ?? key.replace(/_/g, ' ').toLowerCase();
}

const HABIT_LABELS: Record<string, string> = {
  sleep_minutes: 'Sleep',
  exercise: 'Exercise',
  home_cooked_meals: 'Home-cooked meals',
  stress_level: 'Stress level',
  alcohol: 'Alcohol',
  work_mode: 'Work mode',
};

export function formatHabit(key: string): string {
  return HABIT_LABELS[key] ?? key.replace(/_/g, ' ');
}

export function formatEventType(key: string): string {
  return key.charAt(0) + key.slice(1).toLowerCase().replace(/_/g, ' ');
}

/** `3` → `"3 days"`, `1` → `"1 day"`. */
export function pluralise(count: number, singular: string, plural = `${singular}s`): string {
  return `${count} ${count === 1 ? singular : plural}`;
}
