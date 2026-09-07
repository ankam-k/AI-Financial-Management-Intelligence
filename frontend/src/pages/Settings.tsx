/**
 * Profile and data controls.
 *
 * The monthly budget is entered in rupees and stored as integer paise, the same
 * drift-free conversion the expense form uses (constraint 2). Clearing it sends
 * an explicit `null`, because "no budget" is a choice the backend honours by not
 * estimating one. Wiping data is destructive and confirmed before it runs.
 */

import { useCallback, useState } from 'react';
import { getProfile, updateProfile, wipeData } from '../api/endpoints';
import type {
  Category,
  FocusArea,
  HabitField,
  HouseholdContext,
  IncomePattern,
  LifeStage,
  Personalisation,
  Profile,
  WorkContextPref,
} from '../api/types';
import { Card } from '../components/Card';
import {
  CheckboxChips,
  ChoiceChips,
  Field,
  FormStatus,
  TextInput,
} from '../components/forms/Fields';
import { ErrorState, SkeletonCard } from '../components/StateViews';
import { useAsync } from '../hooks/useAsync';
import { useMutation } from '../hooks/useMutation';
import { CATEGORY_OPTIONS } from '../lib/enums';
import { formatPaise } from '../lib/format';
import { MoneyParseError, rupeesToPaise } from '../lib/money';
import {
  FOCUS_AREA_OPTIONS,
  HABIT_OPTIONS,
  HOUSEHOLD_CONTEXT_OPTIONS,
  INCOME_PATTERN_OPTIONS,
  LIFE_STAGE_OPTIONS,
  WORK_CONTEXT_OPTIONS,
} from '../lib/preferences';

const TRACKABLE_CATEGORIES = CATEGORY_OPTIONS.filter(
  (option) => !['TRANSFERS', 'INCOME', 'UNCATEGORIZED', 'FEES_CHARGES'].includes(option.value),
);

export function Settings() {
  const profile = useAsync(useCallback((signal) => getProfile(signal), []), []);

  return (
    <>
      <header className="topbar">
        <div>
          <h1 className="topbar__title">Settings</h1>
          <p className="topbar__subtitle">Your profile, budget, and data.</p>
        </div>
      </header>

      {profile.error ? (
        <div className="card">
          <ErrorState error={profile.error} onRetry={profile.refetch} />
        </div>
      ) : profile.isLoading || !profile.data ? (
        <SkeletonCard height={220} />
      ) : (
        <div className="grid">
          <div className="span-6">
            <ProfileForm
              initialName={profile.data.display_name}
              initialBudgetPaise={profile.data.monthly_budget_paise}
              onSaved={profile.refetch}
            />
          </div>
          <div className="span-6">
            <DangerZone onWiped={profile.refetch} />
          </div>
          <div className="span-12">
            <PersonalisationForm profile={profile.data} onSaved={profile.refetch} />
          </div>
        </div>
      )}
    </>
  );
}

function ProfileForm({
  initialName,
  initialBudgetPaise,
  onSaved,
}: {
  initialName: string;
  initialBudgetPaise: number | null;
  onSaved: () => void;
}) {
  const [name, setName] = useState(initialName);
  const [budget, setBudget] = useState(
    initialBudgetPaise === null ? '' : (initialBudgetPaise / 100).toFixed(2),
  );
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const save = useMutation(updateProfile);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFieldError(null);
    setConfirmation(null);

    if (!name.trim()) {
      setFieldError('A display name is required.');
      return;
    }

    let budgetPaise: number | null = null;
    if (budget.trim() !== '') {
      try {
        budgetPaise = rupeesToPaise(budget);
      } catch (cause) {
        setFieldError(cause instanceof MoneyParseError ? cause.message : 'Enter a valid budget.');
        return;
      }
      if (budgetPaise <= 0) {
        setFieldError('A budget must be greater than zero, or left blank to clear it.');
        return;
      }
    }

    const done = await save.mutate({
      display_name: name.trim(),
      monthly_budget_paise: budgetPaise,
    });
    if (done) {
      setConfirmation(
        budgetPaise === null
          ? 'Saved. No monthly budget is set.'
          : `Saved. Monthly budget ${formatPaise(budgetPaise)}.`,
      );
      onSaved();
    }
  };

  return (
    <Card title="Profile">
      <form className="form" onSubmit={submit} noValidate>
        <Field label="Display name" error={fieldError ?? undefined}>
          {(id, describedBy) => (
            <TextInput id={id} describedBy={describedBy} value={name} onChange={setName} maxLength={100} />
          )}
        </Field>

        <Field
          label="Monthly budget (₹)"
          hint="Leave blank for no budget — nothing is estimated from your average spending."
        >
          {(id, describedBy) => (
            <TextInput
              id={id}
              describedBy={describedBy}
              value={budget}
              onChange={setBudget}
              inputMode="decimal"
              placeholder="No budget"
            />
          )}
        </Field>

        <div className="form__actions">
          <button type="submit" className="btn btn--primary" disabled={save.isSubmitting}>
            {save.isSubmitting ? 'Saving…' : 'Save profile'}
          </button>
          <FormStatus error={save.status === 'error' ? save.error?.message : null} success={confirmation} />
        </div>
      </form>
    </Card>
  );
}

function PersonalisationForm({ profile, onSaved }: { profile: Profile; onSaved: () => void }) {
  const [lifeStage, setLifeStage] = useState<LifeStage | null>(profile.life_stage);
  const [incomePattern, setIncomePattern] = useState<IncomePattern | null>(profile.income_pattern);
  const [workContext, setWorkContext] = useState<WorkContextPref | null>(profile.work_context);
  const [household, setHousehold] = useState<HouseholdContext | null>(profile.household_context);
  const [focusAreas, setFocusAreas] = useState<FocusArea[]>(profile.focus_areas);
  const [categories, setCategories] = useState<Category[]>(profile.tracked_categories);
  const [habits, setHabits] = useState<HabitField[]>(profile.tracked_habits);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const save = useMutation(updateProfile);

  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setConfirmation(null);
    const body: Personalisation = {
      // A cleared single choice is sent as null so it is actually cleared, not
      // left at its previous value. Lists are always sent whole.
      life_stage: lifeStage,
      income_pattern: incomePattern,
      work_context: workContext,
      household_context: household,
      focus_areas: focusAreas,
      tracked_categories: categories,
      tracked_habits: habits,
    };
    const done = await save.mutate(body);
    if (done) {
      setConfirmation('Saved. These shape what the app shows you — never how your data is analysed.');
      onSaved();
    }
  };

  return (
    <Card title="Personalisation">
      <p className="insight__section-body">
        Who you are and what you want to track. This changes which cards lead and which fields your
        check-in surfaces first — it never reaches the analysis engine or changes a single threshold.
      </p>
      <form className="form" onSubmit={submit} noValidate style={{ marginTop: 14 }}>
        <div className="grid">
          <div className="span-6">
            <ChoiceChips legend="Life stage" value={lifeStage} options={LIFE_STAGE_OPTIONS} onChange={setLifeStage} />
          </div>
          <div className="span-6">
            <ChoiceChips
              legend="How your income arrives"
              value={incomePattern}
              options={INCOME_PATTERN_OPTIONS}
              onChange={setIncomePattern}
            />
          </div>
          <div className="span-6">
            <ChoiceChips legend="Usual work setting" value={workContext} options={WORK_CONTEXT_OPTIONS} onChange={setWorkContext} />
          </div>
          <div className="span-6">
            <ChoiceChips
              legend="Living situation"
              value={household}
              options={HOUSEHOLD_CONTEXT_OPTIONS}
              onChange={setHousehold}
            />
          </div>
        </div>

        <CheckboxChips legend="Your goals" values={focusAreas} options={FOCUS_AREA_OPTIONS} onChange={setFocusAreas} />
        <CheckboxChips
          legend="Spending categories to track"
          values={categories}
          options={TRACKABLE_CATEGORIES}
          onChange={setCategories}
        />
        <CheckboxChips
          legend="Daily habits to track"
          hint="A day you don’t log stays Unknown — never counted as a zero."
          values={habits}
          options={HABIT_OPTIONS}
          onChange={setHabits}
        />

        <div className="form__actions">
          <button type="submit" className="btn btn--primary" disabled={save.isSubmitting}>
            {save.isSubmitting ? 'Saving…' : 'Save personalisation'}
          </button>
          <FormStatus error={save.status === 'error' ? save.error?.message : null} success={confirmation} />
        </div>
      </form>
    </Card>
  );
}

function DangerZone({ onWiped }: { onWiped: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [confirmation, setConfirmation] = useState<string | null>(null);
  const wipe = useMutation(wipeData);

  const run = async () => {
    const done = await wipe.mutate();
    if (done !== null) {
      setConfirming(false);
      setConfirmation('All expenses, check-ins and events were deleted. Your profile is kept.');
      onWiped();
    }
  };

  return (
    <Card title="Data">
      <p className="insight__section-body">
        Delete every expense, check-in and life event. Your profile and budget are kept. This cannot
        be undone.
      </p>
      <div className="form__actions" style={{ marginTop: 14 }}>
        {confirming ? (
          <>
            <button type="button" className="btn btn--danger" onClick={run} disabled={wipe.isSubmitting}>
              {wipe.isSubmitting ? 'Deleting…' : 'Yes, delete all data'}
            </button>
            <button type="button" className="btn btn--ghost" onClick={() => setConfirming(false)}>
              Cancel
            </button>
          </>
        ) : (
          <button type="button" className="btn btn--ghost" onClick={() => setConfirming(true)}>
            Delete all data
          </button>
        )}
        <FormStatus error={wipe.status === 'error' ? wipe.error?.message : null} success={confirmation} />
      </div>
    </Card>
  );
}
