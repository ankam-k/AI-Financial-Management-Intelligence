/**
 * Form primitives.
 *
 * Every field ties a real `<label>` to its control by id, so a screen reader
 * announces the two together and a click on the label focuses the input. The
 * error is rendered with `role="alert"` so a validation failure is announced,
 * not just shown. These are deliberately thin: the pages own the state, these
 * own only the accessible markup.
 */

import { useId, type ReactNode } from 'react';
import type { Option } from '../../lib/enums';

export function Field({
  label,
  hint,
  error,
  children,
}: {
  label: string;
  hint?: ReactNode;
  error?: string;
  children: (id: string, describedBy: string | undefined) => ReactNode;
}) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = [hint ? hintId : null, error ? errorId : null].filter(Boolean).join(' ') || undefined;

  return (
    <div className="field">
      <label className="field__label" htmlFor={id}>
        {label}
      </label>
      {children(id, describedBy)}
      {hint ? (
        <p className="field__hint" id={hintId}>
          {hint}
        </p>
      ) : null}
      {error ? (
        <p className="field__error" id={errorId} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function TextInput({
  id,
  describedBy,
  value,
  onChange,
  type = 'text',
  placeholder,
  inputMode,
  maxLength,
  min,
  max,
}: {
  id: string;
  describedBy?: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  placeholder?: string;
  inputMode?: 'text' | 'decimal' | 'numeric';
  maxLength?: number;
  min?: string;
  max?: string;
}) {
  return (
    <input
      id={id}
      className="field__input"
      type={type}
      value={value}
      placeholder={placeholder}
      inputMode={inputMode}
      maxLength={maxLength}
      min={min}
      max={max}
      aria-describedby={describedBy}
      onChange={(event) => onChange(event.target.value)}
    />
  );
}

export function SelectInput<T extends string>({
  id,
  describedBy,
  value,
  options,
  onChange,
}: {
  id: string;
  describedBy?: string;
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
}) {
  return (
    <select
      id={id}
      className="field__input"
      value={value}
      aria-describedby={describedBy}
      onChange={(event) => onChange(event.target.value as T)}
    >
      {options.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  );
}

/**
 * A three-state control: a segmented group where one option is always
 * "Unknown / not logged", visually and semantically distinct from a "No".
 * Selecting "Unknown" is the default and means the field is not sent (or sent
 * as null) — never coerced into a recorded negative. The options carry real
 * values (`true`/`false`/`0`…); `null` is Unknown.
 */
export function TristateGroup<T extends string | number | boolean>({
  legend,
  hint,
  value,
  options,
  onChange,
}: {
  legend: string;
  hint?: ReactNode;
  value: T | null;
  options: { value: T; label: string }[];
  onChange: (value: T | null) => void;
}) {
  return (
    <fieldset className="field tristate">
      <legend className="field__label">{legend}</legend>
      <div className="tristate__options">
        {options.map((option) => (
          <button
            key={String(option.value)}
            type="button"
            className="tristate__option"
            aria-pressed={value === option.value}
            onClick={() => onChange(option.value)}
          >
            {option.label}
          </button>
        ))}
        <button
          type="button"
          className="tristate__option tristate__option--unknown"
          aria-pressed={value === null}
          onClick={() => onChange(null)}
        >
          Unknown
        </button>
      </div>
      {hint ? <p className="field__hint">{hint}</p> : null}
    </fieldset>
  );
}

/**
 * A single-choice chip group — one selectable value, or none.
 *
 * A `<fieldset>` of toggle buttons rather than a `<select>`, so every option is
 * visible at once (onboarding is about seeing the choices, not hunting a
 * dropdown). Clicking the selected chip again clears it back to "no answer",
 * which is a valid state: these preferences are optional.
 */
export function ChoiceChips<T extends string>({
  legend,
  hint,
  value,
  options,
  onChange,
}: {
  legend: string;
  hint?: ReactNode;
  value: T | null;
  options: Option<T>[];
  onChange: (value: T | null) => void;
}) {
  return (
    <fieldset className="field chips-field">
      <legend className="field__label">{legend}</legend>
      <div className="choice-chips">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className="choice-chip"
            aria-pressed={value === option.value}
            onClick={() => onChange(value === option.value ? null : option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {hint ? <p className="field__hint">{hint}</p> : null}
    </fieldset>
  );
}

/**
 * A multi-select chip group — any subset of the options.
 *
 * Used for goals and tracking preferences, where a user picks several. Each
 * chip is a toggle button carrying `aria-pressed`, so the selection is
 * announced, not just coloured.
 */
export function CheckboxChips<T extends string>({
  legend,
  hint,
  values,
  options,
  onChange,
}: {
  legend: string;
  hint?: ReactNode;
  values: T[];
  options: Option<T>[];
  onChange: (values: T[]) => void;
}) {
  const toggle = (value: T) =>
    onChange(values.includes(value) ? values.filter((v) => v !== value) : [...values, value]);

  return (
    <fieldset className="field chips-field">
      <legend className="field__label">{legend}</legend>
      <div className="choice-chips">
        {options.map((option) => (
          <button
            key={option.value}
            type="button"
            className="choice-chip"
            aria-pressed={values.includes(option.value)}
            onClick={() => toggle(option.value)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {hint ? <p className="field__hint">{hint}</p> : null}
    </fieldset>
  );
}

/** A submit row with the button in its submitting state, plus a form-level error. */
export function FormStatus({
  error,
  success,
}: {
  error?: string | null;
  success?: string | null;
}) {
  if (error) {
    return (
      <p className="form__error" role="alert">
        {error}
      </p>
    );
  }
  if (success) {
    return (
      <p className="form__success" role="status">
        {success}
      </p>
    );
  }
  return null;
}
