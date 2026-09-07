/**
 * The session gate: no cookie → the login screen; sign in / register / explore
 * demo → the app; sign out → back to the login screen. Exercised through the
 * real composition (`<AuthProvider><App/></AuthProvider>`), so the assertions
 * are about what a user actually sees, not the context in isolation.
 */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from '../App';
import { AuthProvider } from '../hooks/useAuth';
import * as fixtures from '../test/fixtures';
import { stubServer } from '../test/server';

beforeEach(() => localStorage.clear());

const renderApp = () =>
  render(
    <AuthProvider>
      <App />
    </AuthProvider>,
  );

/** No session opens on the public Landing page; the auth screen is one click in. */
const gotoLogin = async () => {
  await userEvent.click(await screen.findByRole('button', { name: 'Sign in' }));
};

describe('the login gate', () => {
  it('shows the sign-in screen when there is no session', async () => {
    stubServer({ authUser: null });
    renderApp();
    await gotoLogin();

    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
    expect(screen.queryByText('Total spent')).not.toBeInTheDocument();
  });

  it('offers a create-account tab with a display-name field', async () => {
    stubServer({ authUser: null });
    renderApp();
    await gotoLogin();

    await userEvent.click(await screen.findByRole('button', { name: 'Create account' }));

    expect(screen.getByText('Display name (optional)')).toBeInTheDocument();
  });

  it('signs in and reveals the app', async () => {
    stubServer({ authUser: null });
    renderApp();
    await gotoLogin();

    await userEvent.type(await screen.findByLabelText('Email'), 'user-a@afi.test');
    await userEvent.type(screen.getByLabelText('Password'), 'test-password');
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByText('Total spent')).toBeInTheDocument();
  });

  it('surfaces a rejected sign-in without leaving the screen', async () => {
    stubServer({
      authUser: null,
      status: 401,
      errorBody: { detail: 'Invalid email or password.', error: 'AuthError' },
    });
    renderApp();
    await gotoLogin();

    await userEvent.type(await screen.findByLabelText('Email'), 'user-a@afi.test');
    await userEvent.type(screen.getByLabelText('Password'), 'wrong-password');
    await userEvent.click(screen.getByRole('button', { name: 'Log in' }));

    expect(await screen.findByText('Invalid email or password.')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });

  it('signs out back to the login screen', async () => {
    stubServer(); // authed by default
    renderApp();

    await userEvent.click(await screen.findByRole('button', { name: 'Sign out' }));

    // Sign-out drops to the public Landing page; the login screen is one click in.
    await gotoLogin();
    expect(await screen.findByRole('heading', { name: 'Welcome back' })).toBeInTheDocument();
  });
});

describe('the demo entry', () => {
  it('appears only when demo mode is on', async () => {
    stubServer({ authUser: null }); // demo status defaults to disabled
    renderApp();
    await gotoLogin();

    await screen.findByRole('heading', { name: 'Welcome back' });
    expect(screen.queryByRole('button', { name: 'Explore the demo' })).not.toBeInTheDocument();
  });

  it('enters the demo from the login screen', async () => {
    stubServer({ authUser: null, demoStatus: { enabled: true } });
    renderApp();
    await gotoLogin();

    await userEvent.click(await screen.findByRole('button', { name: 'Explore the demo' }));

    expect(await screen.findByText('Total spent')).toBeInTheDocument();
  });

  it('marks a demo session with a badge and a banner', async () => {
    stubServer({ authUser: { ...fixtures.authUser, is_demo: true } });
    renderApp();

    expect(await screen.findByText('Demo')).toBeInTheDocument();
    expect(screen.getByText(/exploring a sample profile/i)).toBeInTheDocument();
  });
});
