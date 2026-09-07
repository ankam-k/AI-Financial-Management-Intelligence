/**
 * First-run onboarding: a signed-in account whose `onboarding_completed` is
 * false is shown the wizard, not the dashboard. It can be skipped or walked
 * through; either way it records the answers and reveals the app. Driven through
 * the real gate (`<AuthProvider><App/></AuthProvider>`).
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../App';
import { AuthProvider } from '../hooks/useAuth';
import * as fixtures from '../test/fixtures';
import { stubServer } from '../test/server';

beforeEach(() => localStorage.clear());

const unonboarded = { ...fixtures.profile, onboarding_completed: false };

const renderApp = () =>
  render(
    <AuthProvider>
      <App />
    </AuthProvider>,
  );

describe('onboarding', () => {
  it('greets a not-yet-onboarded account with the wizard', async () => {
    stubServer({ authUser: fixtures.authUser, profile: unonboarded });
    renderApp();

    expect(await screen.findByRole('button', { name: 'Skip for now' })).toBeInTheDocument();
    // Not the app yet.
    expect(screen.queryByText('Total spent')).not.toBeInTheDocument();
  });

  it('can skip straight into the app', async () => {
    const server = stubServer({ authUser: fixtures.authUser, profile: unonboarded });
    renderApp();

    await userEvent.click(await screen.findByRole('button', { name: 'Skip for now' }));

    await waitFor(() =>
      expect(
        server.requests.some(
          (r) => r.method === 'POST' && r.url.includes('/api/profile/onboarding'),
        ),
      ).toBe(true),
    );
    expect(await screen.findByText('Total spent')).toBeInTheDocument();
  });

  it('walks the steps, records the answers, and reveals the app', async () => {
    const server = stubServer({ authUser: fixtures.authUser, profile: unonboarded });
    renderApp();

    // Welcome → About you
    await userEvent.click(await screen.findByRole('button', { name: 'Next' }));
    await userEvent.click(screen.getByRole('button', { name: 'Student' }));
    // About you → Your goals
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    await userEvent.click(
      screen.getByRole('button', { name: 'Understand where my money goes' }),
    );
    // Your goals → What to track
    await userEvent.click(screen.getByRole('button', { name: 'Next' }));
    await userEvent.click(screen.getByRole('button', { name: 'Exercise' }));
    // Finish
    await userEvent.click(screen.getByRole('button', { name: 'Finish' }));

    await waitFor(() => {
      const submit = server.requests.find(
        (r) => r.method === 'POST' && r.url.includes('/api/profile/onboarding'),
      );
      expect(submit).toBeTruthy();
      expect(submit?.body?.life_stage).toBe('STUDENT');
      expect(submit?.body?.focus_areas).toContain('UNDERSTAND_SPENDING');
      expect(submit?.body?.tracked_habits).toContain('exercise');
    });
    expect(await screen.findByText('Total spent')).toBeInTheDocument();
  });
});
