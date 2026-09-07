/**
 * First-run onboarding.
 *
 * Four short steps — welcome, who you are, what you want to understand, what to
 * track — that end by recording the answers and flipping `onboarding_completed`.
 * Every answer is optional: onboarding *sets expectations and personalises the
 * UI*, it never gates the product, so "Skip" is a first-class button and an
 * empty submission is valid. None of these answers reaches the analysis engine —
 * they only change which cards lead and which habits a check-in surfaces first.
 */

import { useCallback, useMemo, useState } from 'react';
import { submitOnboarding } from '../api/endpoints';
import type {
  Category,
  FocusArea,
  HabitField,
  HouseholdContext,
  IncomePattern,
  LifeStage,
  Personalisation,
  WorkContextPref,
} from '../api/types';
import { CheckboxChips, ChoiceChips, FormStatus } from '../components/forms/Fields';
import { useAuth } from '../hooks/useAuth';
import { useMutation } from '../hooks/useMutation';
import { CATEGORY_OPTIONS } from '../lib/enums';
import {
  FOCUS_AREA_OPTIONS,
  HABIT_OPTIONS,
  HOUSEHOLD_CONTEXT_OPTIONS,
  INCOME_PATTERN_OPTIONS,
  LIFE_STAGE_OPTIONS,
  WORK_CONTEXT_OPTIONS,
} from '../lib/preferences';

/** Categories worth *tracking* — day-to-day spending, not transfers or income. */
const TRACKABLE_CATEGORIES = CATEGORY_OPTIONS.filter(
  (option) => !['TRANSFERS', 'INCOME', 'UNCATEGORIZED', 'FEES_CHARGES'].includes(option.value),
);

const STEPS = ['Welcome', 'About you', 'Your goals', 'What to track'] as const;

export function Onboarding() {
  const { user, setProfile } = useAuth();
  const [step, setStep] = useState(0);

  const [lifeStage, setLifeStage] = useState<LifeStage | null>(null);
  const [incomePattern, setIncomePattern] = useState<IncomePattern | null>(null);
  const [workContext, setWorkContext] = useState<WorkContextPref | null>(null);
  const [household, setHousehold] = useState<HouseholdContext | null>(null);
  const [focusAreas, setFocusAreas] = useState<FocusArea[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [habits, setHabits] = useState<HabitField[]>([]);

  const save = useMutation(useCallback((body: Personalisation) => submitOnboarding(body), []));

  const payload = useMemo<Personalisation>(() => {
    const body: Personalisation = {
      focus_areas: focusAreas,
      tracked_categories: categories,
      tracked_habits: habits,
    };
    if (lifeStage) body.life_stage = lifeStage;
    if (incomePattern) body.income_pattern = incomePattern;
    if (workContext) body.work_context = workContext;
    if (household) body.household_context = household;
    return body;
  }, [lifeStage, incomePattern, workContext, household, focusAreas, categories, habits]);

  const finish = async (body: Personalisation) => {
    const profile = await save.mutate(body);
    if (profile) setProfile(profile);
  };

  const isLast = step === STEPS.length - 1;
  const next = () => (isLast ? finish(payload) : setStep((s) => s + 1));
  const back = () => setStep((s) => Math.max(0, s - 1));

  return (
    <main id="main" className="onboarding">
      <div className="onboarding__card">
        <ol className="onboarding__progress" aria-label="Onboarding steps">
          {STEPS.map((label, index) => (
            <li
              key={label}
              className="onboarding__step-dot"
              aria-current={index === step ? 'step' : undefined}
              data-done={index < step ? 'true' : undefined}
            >
              <span className="visually-hidden">{label}</span>
            </li>
          ))}
        </ol>

        {step === 0 ? (
          <section className="onboarding__panel">
            <h1 className="onboarding__title">
              Welcome{user?.display_name ? `, ${user.display_name}` : ''}.
            </h1>
            <p className="onboarding__lead">
              A couple of quick questions so the dashboard speaks to your situation. This only shapes
              what you see — it never changes how your data is analysed, and you can skip any of it.
            </p>
            <ul className="onboarding__list">
              <li>Your account starts empty — nothing is assumed about you.</li>
              <li>You record expenses, daily check-ins and life events yourself.</li>
              <li>Insights appear only once there is enough of your own history to be sure.</li>
            </ul>
          </section>
        ) : step === 1 ? (
          <section className="onboarding__panel">
            <h1 className="onboarding__title">A little about you</h1>
            <p className="onboarding__lead">Coarse context, not a survey. Pick what fits, or skip.</p>
            <ChoiceChips
              legend="Life stage"
              value={lifeStage}
              options={LIFE_STAGE_OPTIONS}
              onChange={setLifeStage}
            />
            <ChoiceChips
              legend="How your income arrives"
              value={incomePattern}
              options={INCOME_PATTERN_OPTIONS}
              onChange={setIncomePattern}
            />
            <ChoiceChips
              legend="Usual work setting"
              value={workContext}
              options={WORK_CONTEXT_OPTIONS}
              onChange={setWorkContext}
            />
            <ChoiceChips
              legend="Living situation"
              value={household}
              options={HOUSEHOLD_CONTEXT_OPTIONS}
              onChange={setHousehold}
            />
          </section>
        ) : step === 2 ? (
          <section className="onboarding__panel">
            <h1 className="onboarding__title">What would you like to understand?</h1>
            <p className="onboarding__lead">Choose any that apply. This decides which cards lead.</p>
            <CheckboxChips
              legend="Your goals"
              values={focusAreas}
              options={FOCUS_AREA_OPTIONS}
              onChange={setFocusAreas}
            />
          </section>
        ) : (
          <section className="onboarding__panel">
            <h1 className="onboarding__title">What do you want to track?</h1>
            <p className="onboarding__lead">
              Your picks surface first on the entry forms. You can always record anything else too —
              a preference is what you want to <em>watch</em>, never a limit.
            </p>
            <CheckboxChips
              legend="Spending categories"
              values={categories}
              options={TRACKABLE_CATEGORIES}
              onChange={setCategories}
            />
            <CheckboxChips
              legend="Daily habits"
              hint="A day you don't log stays Unknown — never counted as a zero."
              values={habits}
              options={HABIT_OPTIONS}
              onChange={setHabits}
            />
          </section>
        )}

        <div className="onboarding__actions">
          {step > 0 ? (
            <button type="button" className="btn btn--ghost" onClick={back} disabled={save.isSubmitting}>
              Back
            </button>
          ) : (
            <span />
          )}

          <div className="onboarding__actions-right">
            <button
              type="button"
              className="btn btn--ghost"
              onClick={() => finish({ focus_areas: [], tracked_categories: [], tracked_habits: [] })}
              disabled={save.isSubmitting}
            >
              Skip for now
            </button>
            <button type="button" className="btn btn--primary" onClick={next} disabled={save.isSubmitting}>
              {isLast ? (save.isSubmitting ? 'Finishing…' : 'Finish') : 'Next'}
            </button>
          </div>
        </div>
        <FormStatus error={save.status === 'error' ? save.error?.message : null} />
      </div>
    </main>
  );
}
