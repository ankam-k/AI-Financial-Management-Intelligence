/** The expense form: validation, exact paise, and the error state. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { Expenses } from './Expenses';
import { stubServer } from '../test/server';

beforeEach(() => localStorage.clear());

function postBody(server: ReturnType<typeof stubServer>) {
  return server.requests.find((r) => r.method === 'POST' && r.url.includes('/api/expenses'))?.body;
}

describe('add expense form', () => {
  it('rejects an amount of zero without calling the server', async () => {
    const server = stubServer();
    render(<Expenses />);
    await waitFor(() => expect(screen.getByLabelText(/Amount/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/Amount/), '0');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    expect(screen.getByText(/greater than zero/)).toBeInTheDocument();
    expect(postBody(server)).toBeUndefined();
  });

  it('sends the amount as exact integer paise', async () => {
    const server = stubServer();
    render(<Expenses />);
    await waitFor(() => expect(screen.getByLabelText(/Amount/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/Amount/), '450.50');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    await waitFor(() => expect(postBody(server)).toBeTruthy());
    expect(postBody(server)).toMatchObject({ amount_paise: 45_050, category: 'FOOD_DINING' });
  });

  it('surfaces a backend validation error', async () => {
    stubServer({
      status: 422,
      errorBody: { detail: 'amount_paise must be greater than 0', error: 'ValidationError' },
    });
    render(<Expenses />);
    await waitFor(() => expect(screen.getByLabelText(/Amount/)).toBeInTheDocument());

    await userEvent.type(screen.getByLabelText(/Amount/), '450');
    await userEvent.click(screen.getByRole('button', { name: 'Add expense' }));

    await waitFor(() => expect(screen.getAllByText(/must be greater than 0/).length).toBeGreaterThan(0));
  });
});
