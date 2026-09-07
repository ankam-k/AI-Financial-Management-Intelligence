/**
 * The unauthenticated entry: sign in, create an account, or explore the demo.
 *
 * This is the whole app when there is no session. Registration logs the user
 * straight in (the backend issues the cookie on 201), so there is no separate
 * "now log in" step. The demo is a *separate account* reached without a
 * password — clicking "Explore the demo" never touches, and never becomes, a
 * real account (§9). The button only appears when the deployment has demo mode
 * on, which a quick status check tells us.
 *
 * Passwords are entered by the person, into the app's own form, over the same
 * origin — the client posts them once and keeps nothing.
 */

import { useCallback, useMemo, useState } from 'react';
import { getDemoStatus } from '../api/endpoints';
import { Field, FormStatus, TextInput } from '../components/forms/Fields';
import { useAsync } from '../hooks/useAsync';
import { useAuth } from '../hooks/useAuth';
import { useMutation } from '../hooks/useMutation';

type Mode = 'login' | 'register';

export interface AuthProps {
  /** Which tab to open on first render (from the Landing call to action). */
  initialMode?: Mode;
  /** Return to the public Landing page, when reached from it. */
  onBack?: () => void;
}

export function Auth({ initialMode = 'login', onBack }: AuthProps = {}) {
  const { login, register, enterDemo } = useAuth();
  const [mode, setMode] = useState<Mode>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [fieldError, setFieldError] = useState<string | null>(null);

  const submit = useMutation(
    useCallback(
      (m: Mode, e: string, p: string, name: string) =>
        m === 'login' ? login(e, p) : register(e, p, name.trim() || undefined),
      [login, register],
    ),
  );
  const demo = useMutation(useCallback(() => enterDemo(), [enterDemo]));

  // Show the demo entry only where the deployment allows it.
  const demoStatus = useAsync(useCallback((signal) => getDemoStatus(signal), []), []);
  const demoEnabled = demoStatus.data?.enabled ?? false;

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setFieldError(null);
    if (!email.trim()) {
      setFieldError('Enter your email.');
      return;
    }
    if (mode === 'register' && password.length < 8) {
      setFieldError('Use a password of at least 8 characters.');
      return;
    }
    if (!password) {
      setFieldError('Enter your password.');
      return;
    }
    await submit.mutate(mode, email.trim(), password, displayName);
  };

  const switchTo = (next: Mode) => {
    setMode(next);
    setFieldError(null);
    submit.reset();
  };

  const heading = useMemo(
    () => (mode === 'login' ? 'Welcome back' : 'Create your account'),
    [mode],
  );

  return (
    <main id="main" className="auth">
      <div className="auth__card">
        {onBack ? (
          <button
            type="button"
            className="btn btn--ghost btn--small"
            onClick={onBack}
            style={{ marginBottom: 14 }}
          >
            ← Back
          </button>
        ) : null}
        <div className="auth__brand">
          <p className="brand__name">Financial Intelligence</p>
          <p className="brand__tagline">
            Understand the patterns in your financial behaviour — with the evidence behind each one.
          </p>
        </div>

        <div className="auth__tabs control-group" role="group" aria-label="Sign in or register">
          <button type="button" aria-pressed={mode === 'login'} onClick={() => switchTo('login')}>
            Sign in
          </button>
          <button
            type="button"
            aria-pressed={mode === 'register'}
            onClick={() => switchTo('register')}
          >
            Create account
          </button>
        </div>

        <h1 className="auth__heading">{heading}</h1>

        <form className="form" onSubmit={onSubmit} noValidate>
          <Field label="Email">
            {(id, describedBy) => (
              <TextInput
                id={id}
                describedBy={describedBy}
                value={email}
                onChange={setEmail}
                type="email"
                placeholder="you@example.com"
              />
            )}
          </Field>

          <Field
            label="Password"
            hint={mode === 'register' ? 'At least 8 characters.' : undefined}
          >
            {(id, describedBy) => (
              <TextInput
                id={id}
                describedBy={describedBy}
                value={password}
                onChange={setPassword}
                type="password"
                placeholder="Your password"
              />
            )}
          </Field>

          {mode === 'register' ? (
            <Field label="Display name (optional)" hint="What we call you. Defaults to your email name.">
              {(id, describedBy) => (
                <TextInput
                  id={id}
                  describedBy={describedBy}
                  value={displayName}
                  onChange={setDisplayName}
                  maxLength={100}
                  placeholder="e.g. Pranay"
                />
              )}
            </Field>
          ) : null}

          <div className="form__actions">
            <button type="submit" className="btn btn--primary" disabled={submit.isSubmitting}>
              {submit.isSubmitting
                ? mode === 'login'
                  ? 'Signing in…'
                  : 'Creating…'
                : mode === 'login'
                  ? 'Log in'
                  : 'Sign up'}
            </button>
            <FormStatus error={fieldError ?? (submit.status === 'error' ? submit.error?.message : null)} />
          </div>
        </form>

        {demoEnabled ? (
          <div className="auth__demo">
            <p className="auth__divider"><span>or</span></p>
            <button
              type="button"
              className="btn btn--ghost auth__demo-btn"
              onClick={() => demo.mutate()}
              disabled={demo.isSubmitting}
            >
              {demo.isSubmitting ? 'Loading the demo…' : 'Explore the demo'}
            </button>
            <p className="field__hint auth__demo-hint">
              A sample financial profile with nine months of data — separate from any real account,
              nothing to sign up for.
            </p>
            <FormStatus error={demo.status === 'error' ? demo.error?.message : null} />
          </div>
        ) : null}
      </div>
    </main>
  );
}
