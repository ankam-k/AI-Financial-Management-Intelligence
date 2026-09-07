/** The shell: navigation, the filter row, and the theme toggle. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import App from './App';
import { AuthProvider } from './hooks/useAuth';
import { stubServer } from './test/server';

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

/** The app under its session provider — the real composition `main.tsx` mounts. */
const renderApp = () => render(
  <AuthProvider>
    <App />
  </AuthProvider>,
);

describe('navigation', () => {
  it('opens on the dashboard', async () => {
    stubServer();
    renderApp();

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Overview' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('switches to the chat view', async () => {
    stubServer();
    renderApp();

    await userEvent.click(await screen.findByRole('button', { name: 'Explore' }));

    expect(screen.getByText('Ask about your money')).toBeInTheDocument();
    expect(screen.queryByText('Total spent')).not.toBeInTheDocument();
  });

  it('names the sections for assistive technology', async () => {
    stubServer();
    renderApp();

    expect(await screen.findByRole('navigation', { name: 'Sections' })).toBeInTheDocument();
  });
});

describe('window filter', () => {
  it('refetches with the chosen window and keeps the old data meanwhile', async () => {
    const server = stubServer();
    renderApp();

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    const before = server.calls.length;

    await userEvent.click(screen.getByRole('button', { name: '30 days' }));

    await waitFor(() => expect(server.calls.length).toBeGreaterThan(before));
    expect(server.calls.some((url) => url.includes('days=30'))).toBe(true);
    // The previous render stays on screen instead of flashing a skeleton.
    expect(screen.getByText('Total spent')).toBeInTheDocument();
  });

  it('marks the active window for assistive technology', async () => {
    stubServer();
    renderApp();

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: '90 days' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('asks the backend to generate prose only when requested', async () => {
    const server = stubServer();
    renderApp();

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    expect(server.calls.some((url) => url.includes('generate=false'))).toBe(true);

    await userEvent.click(screen.getByRole('button', { name: 'AI-written' }));

    await waitFor(() =>
      expect(server.calls.some((url) => url.includes('generate=true'))).toBe(true),
    );
  });

  it('scopes both views, so they cannot contradict each other', async () => {
    const server = stubServer();
    renderApp();

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: '30 days' }));
    await userEvent.click(screen.getByRole('button', { name: 'Explore' }));
    await userEvent.click(screen.getByRole('button', { name: /How much did I spend/i }));

    await waitFor(() => {
      const chatCall = server.calls.find((url) => url.includes('/api/chat') && !url.includes('capabilities'));
      expect(chatCall).toBeTruthy();
    });
  });
});

describe('theme', () => {
  it('stamps an explicit choice on the document', async () => {
    stubServer();
    renderApp();

    await userEvent.click(await screen.findByRole('button', { name: 'Dark' }));

    expect(document.documentElement).toHaveAttribute('data-theme', 'dark');
  });

  it('returns to the OS setting on Auto', async () => {
    stubServer();
    renderApp();

    await userEvent.click(await screen.findByRole('button', { name: 'Dark' }));
    await userEvent.click(screen.getByRole('button', { name: 'Auto' }));

    expect(document.documentElement).not.toHaveAttribute('data-theme');
  });
});

describe('accessibility', () => {
  it('provides a skip link to the content', async () => {
    stubServer();
    renderApp();

    expect(await screen.findByRole('link', { name: /skip to content/i })).toHaveAttribute(
      'href',
      '#main',
    );
  });

  it('groups the filters with accessible names', async () => {
    stubServer();
    renderApp();

    expect(await screen.findByRole('group', { name: 'Analysis window' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'Colour theme' })).toBeInTheDocument();
  });
});
