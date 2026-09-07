/** The public landing page: static marketing, two calls to action. */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { Landing } from './Landing';

describe('Landing', () => {
  it('routes "Start tracking" to sign-up and "Sign in" to login', async () => {
    const onStart = vi.fn();
    const onSignIn = vi.fn();
    render(<Landing onStart={onStart} onSignIn={onSignIn} />);

    // "Start tracking" appears in both the nav and the hero — either starts sign-up.
    await userEvent.click(screen.getAllByRole('button', { name: 'Start tracking' })[0]!);
    expect(onStart).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    expect(onSignIn).toHaveBeenCalledTimes(1);
  });

  it('keeps the brand and the evidence-first promise', () => {
    render(<Landing onStart={vi.fn()} onSignIn={vi.fn()} />);

    expect(screen.getByText('Financial Intelligence')).toBeInTheDocument();
    expect(screen.getByText(/Understand your financial behaviour/i)).toBeInTheDocument();
  });
});
