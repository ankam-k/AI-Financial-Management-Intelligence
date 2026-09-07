/**
 * The daily check-in — fast, and honest about the difference between "No" and
 * "not logged".
 *
 * The three-state rule is the whole point (constraint 3). Each habit offers an
 * explicit **Unknown / not logged** choice that is distinct from a recorded
 * negative, and every control defaults to Unknown. When the form is submitted:
 *
 *   • a habit left Unknown is **omitted** from a create (and sent as `null` on
 *     an edit) — it is never turned into a `false` or a `0`;
 *   • an explicit "No" / "None" is sent as `false` / `0`, a recorded fact.
 *
 * A day you did not log is not a zero, and the analysis excludes it rather than
 * counting it against you. The copy says so, because this is exactly where a
 * user would otherwise misread it.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { createCheckIn, deleteCheckIn, listCheckIns, updateCheckIn } from '../api/endpoints';
import type { CheckInCreate, CheckInRead, WorkMode } from '../api/types';
import { Card } from '../components/Card';
import { Field, FormStatus, TextInput, TristateGroup } from '../components/forms/Fields';
import { EmptyState, ErrorState, SkeletonCard } from '../components/StateViews';
import { useAsync } from '../hooks/useAsync';
import { useMutation } from '../hooks/useMutation';
import { WORK_MODE_LABELS, WORK_MODE_OPTIONS, isoDaysAgo, todayIso } from '../lib/enums';
import { formatDayLong } from '../lib/format';

const MEAL_OPTIONS = [0, 1, 2, 3].map((n) => ({ value: n, label: String(n) }));
const STRESS_OPTIONS = [1, 2, 3, 4, 5].map((n) => ({ value: n, label: String(n) }));
const YES_NO = [
  { value: true, label: 'Yes' },
  { value: false, label: 'No' },
];

interface FormState {
  sleep: string;
  exercise: boolean | null;
  meals: number | null;
  stress: number | null;
  alcohol: boolean | null;
  work: WorkMode | null;
}

const BLANK: FormState = {
  sleep: '',
  exercise: null,
  meals: null,
  stress: null,
  alcohol: null,
  work: null,
};

function fromCheckIn(entry: CheckInRead): FormState {
  return {
    sleep: entry.sleep_hours === null ? '' : String(entry.sleep_hours),
    exercise: entry.exercise,
    meals: entry.home_cooked_meals,
    stress: entry.stress_level,
    alcohol: entry.alcohol,
    work: entry.work_mode,
  };
}

/** Blank sleep is Unknown (null); anything else is the parsed number. */
function sleepOf(state: FormState): number | null {
  return state.sleep.trim() === '' ? null : Number(state.sleep);
}

export function CheckIn() {
  const list = useAsync(useCallback((signal) => listCheckIns(signal), []), []);

  const [date, setDate] = useState(todayIso());
  const [form, setForm] = useState<FormState>(BLANK);
  // True once the user edits a field for the current date. It guards the sync
  // effect below so a form the user is mid-edit on is never overwritten.
  const [dirty, setDirty] = useState(false);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);

  const create = useMutation(createCheckIn);
  const update = useMutation(updateCheckIn);
  const remove = useMutation(deleteCheckIn);

  const existing = useMemo(
    () => (list.data ?? []).find((entry) => entry.log_date === date) ?? null,
    [list.data, date],
  );

  // Populate the form from the stored check-in as soon as it resolves. The list
  // loads asynchronously, so on first paint `existing` is still null even for a
  // day that has data. Without this, edit mode shows a blank/Unknown form over a
  // recorded day and pressing Update would PATCH every habit to null — silently
  // wiping it. Runs on load and whenever the selected day changes; the `dirty`
  // guard keeps it from clobbering an in-progress edit.
  useEffect(() => {
    if (dirty) return;
    setForm(existing ? fromCheckIn(existing) : BLANK);
  }, [existing, dirty]);

  const onPickDate = (next: string) => {
    setDate(next);
    setFieldError(null);
    setConfirmation(null);
    // Leave the form to the sync effect: `existing` recomputes for `next`, and
    // clearing `dirty` lets the effect load that day's stored values.
    setDirty(false);
  };

  const patch = <K extends keyof FormState>(key: K, value: FormState[K]) => {
    setDirty(true);
    setForm((current) => ({ ...current, [key]: value }));
  };

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFieldError(null);
    setConfirmation(null);

    if (!date) {
      setFieldError('Choose a date.');
      return;
    }
    if (date > todayIso()) {
      setFieldError('You cannot log a check-in for a future date.');
      return;
    }
    if (date < isoDaysAgo(30)) {
      setFieldError('Check-ins can be backfilled up to 30 days.');
      return;
    }

    const sleepValue = sleepOf(form);
    if (sleepValue !== null && (Number.isNaN(sleepValue) || sleepValue < 0 || sleepValue > 24)) {
      setFieldError('Sleep must be between 0 and 24 hours, or left blank for Unknown.');
      return;
    }
    const hasAny =
      sleepValue !== null ||
      form.exercise !== null ||
      form.meals !== null ||
      form.stress !== null ||
      form.alcohol !== null ||
      form.work !== null;

    if (!hasAny) {
      setFieldError('Log at least one habit — an empty check-in records nothing.');
      return;
    }

    if (existing) {
      // Editing an existing day: send the full state, mapping Unknown → null so
      // the user can clear a value back to unknown. Still never Unknown → false.
      const body = {
        sleep_hours: sleepValue,
        exercise: form.exercise,
        home_cooked_meals: form.meals,
        stress_level: form.stress,
        alcohol: form.alcohol,
        work_mode: form.work,
      };
      const done = await update.mutate(date, body);
      if (done) {
        setConfirmation(`Updated your check-in for ${formatDayLong(date)}.`);
        // The saved values are now authoritative; let the refetch re-sync.
        setDirty(false);
        list.refetch();
      }
      return;
    }

    // Creating: omit every Unknown field entirely. Only recorded facts are sent.
    const body: CheckInCreate = { log_date: date };
    if (sleepValue !== null) body.sleep_hours = sleepValue;
    if (form.exercise !== null) body.exercise = form.exercise;
    if (form.meals !== null) body.home_cooked_meals = form.meals;
    if (form.stress !== null) body.stress_level = form.stress;
    if (form.alcohol !== null) body.alcohol = form.alcohol;
    if (form.work !== null) body.work_mode = form.work;

    const done = await create.mutate(body);
    if (done) {
      setConfirmation(`Logged your check-in for ${formatDayLong(date)}.`);
      setForm(BLANK);
      setDirty(false);
      list.refetch();
    }
  };

  const onDelete = async (entry: CheckInRead) => {
    const done = await remove.mutate(entry.log_date);
    if (done !== null) {
      setConfirmation('Check-in deleted.');
      // Re-sync from the (now absent) day rather than pinning a stale form.
      if (entry.log_date === date) setDirty(false);
      list.refetch();
    }
  };

  // Cap what we render to the 50 most recent (the API returns them newest-first
  // and unpaginated). A user with hundreds of days should not paint them all.
  const RECENT_LIMIT = 50;
  const entries = list.data ?? [];
  const recent = entries.slice(0, RECENT_LIMIT);
  const busy = create.isSubmitting || update.isSubmitting;
  const mutationError =
    (create.status === 'error' && create.error?.message) ||
    (update.status === 'error' && update.error?.message) ||
    null;

  return (
    <div className="grid">
      <header className="topbar span-12">
        <div>
          <h1 className="topbar__title">Daily check-in</h1>
          <p className="topbar__subtitle">
            About fifteen seconds. Log only what you know — an unlogged habit stays unknown, not a
            zero.
          </p>
        </div>
      </header>

      <div className="span-7">
        <Card
          title={existing ? 'Edit this day' : 'Log a day'}
          hint={existing ? 'editing an existing check-in' : undefined}
        >
          <form className="form" onSubmit={submit} noValidate>
            <Field
              label="Date"
              hint="Today by default. Backfill up to 30 days; future dates are blocked."
              error={fieldError ?? undefined}
            >
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={date}
                  onChange={onPickDate}
                  type="date"
                  max={todayIso()}
                  min={isoDaysAgo(30)}
                />
              )}
            </Field>

            <div className="checkin-note" role="note">
              <strong>Unknown is not No.</strong> A day you didn't log is excluded from the analysis;
              a recorded "No" is a fact it can use. Leave anything you're unsure about as Unknown.
            </div>

            <Field label="Sleep (hours)" hint="Leave blank for Unknown / not logged.">
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={form.sleep}
                  onChange={(value) => patch('sleep', value)}
                  inputMode="decimal"
                  placeholder="Unknown"
                />
              )}
            </Field>

            <TristateGroup
              legend="Exercise"
              value={form.exercise}
              options={YES_NO}
              onChange={(value) => patch('exercise', value)}
            />

            <TristateGroup
              legend="Home-cooked meals"
              hint="How many of the day's meals you cooked at home. 0 is a recorded 'none'."
              value={form.meals}
              options={MEAL_OPTIONS}
              onChange={(value) => patch('meals', value)}
            />

            <TristateGroup
              legend="Stress level (1 low – 5 high)"
              value={form.stress}
              options={STRESS_OPTIONS}
              onChange={(value) => patch('stress', value)}
            />

            <TristateGroup
              legend="Alcohol"
              value={form.alcohol}
              options={YES_NO}
              onChange={(value) => patch('alcohol', value)}
            />

            <TristateGroup
              legend="Work mode"
              value={form.work}
              options={WORK_MODE_OPTIONS}
              onChange={(value) => patch('work', value)}
            />

            <div className="form__actions">
              <button
                type="submit"
                className="btn btn--primary"
                disabled={busy || list.isLoading}
              >
                {busy ? 'Saving…' : existing ? 'Update check-in' : 'Save check-in'}
              </button>
              <FormStatus error={mutationError} success={confirmation} />
            </div>
          </form>
        </Card>
      </div>

      <div className="span-5">
        <Card
          title="Recent check-ins"
          hint={
            entries.length
              ? entries.length > RECENT_LIMIT
                ? `${RECENT_LIMIT} of ${entries.length}`
                : `${entries.length} logged`
              : undefined
          }
        >
          {list.error ? (
            <ErrorState error={list.error} onRetry={list.refetch} />
          ) : list.isLoading ? (
            <SkeletonCard height={160} />
          ) : entries.length === 0 ? (
            <EmptyState
              title="No check-ins yet"
              detail="Log a day on the left. A handful of consistent days is what unlocks the habit analysis."
            />
          ) : (
            <ul className="checkin-list">
              {recent.map((entry) => (
                <li key={entry.log_date} className="checkin-list__item">
                  <button
                    type="button"
                    className="checkin-list__edit"
                    onClick={() => onPickDate(entry.log_date)}
                  >
                    {formatDayLong(entry.log_date)}
                  </button>
                  <span className="stat__meta" style={{ margin: 0 }}>
                    {describeEntry(entry)}
                  </span>
                  <button
                    type="button"
                    className="btn btn--ghost btn--small"
                    onClick={() => onDelete(entry)}
                    disabled={remove.isSubmitting}
                    aria-label={`Delete check-in for ${entry.log_date}`}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}

/** A one-line summary of what a check-in recorded, skipping Unknown fields. */
function describeEntry(entry: CheckInRead): string {
  const parts: string[] = [];
  if (entry.sleep_hours !== null) parts.push(`${entry.sleep_hours}h sleep`);
  if (entry.exercise !== null) parts.push(entry.exercise ? 'exercised' : 'no exercise');
  if (entry.home_cooked_meals !== null) parts.push(`${entry.home_cooked_meals} home meals`);
  if (entry.stress_level !== null) parts.push(`stress ${entry.stress_level}`);
  if (entry.alcohol !== null) parts.push(entry.alcohol ? 'alcohol' : 'no alcohol');
  if (entry.work_mode !== null) parts.push(WORK_MODE_LABELS[entry.work_mode] ?? entry.work_mode);
  return parts.length ? parts.join(' · ') : 'nothing recorded';
}
