/**
 * "Delete all data" is destructive, so it must never fire on a single click —
 * it asks for an explicit confirmation first.
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { Settings } from './Settings';
import { stubServer } from '../test/server';

beforeEach(() => localStorage.clear());

function wipeRequests(server: ReturnType<typeof stubServer>) {
  return server.requests.filter(
    (r) => r.method === 'DELETE' && r.url.includes('/api/profile/data'),
  );
}

async function ready() {
  await waitFor(() =>
    expect(screen.getByRole('button', { name: 'Delete all data' })).toBeInTheDocument(),
  );
}

describe('deleting all data requires explicit confirmation', () => {
  it('does not delete on the first click — it asks first', async () => {
    const server = stubServer();
    render(<Settings />);
    await ready();

    await userEvent.click(screen.getByRole('button', { name: 'Delete all data' }));

    // Nothing was deleted; a confirmation is shown instead.
    expect(wipeRequests(server)).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Yes, delete all data' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
  });

  it('deletes only after the explicit confirm', async () => {
    const server = stubServer();
    render(<Settings />);
    await ready();

    await userEvent.click(screen.getByRole('button', { name: 'Delete all data' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, delete all data' }));

    await waitFor(() => expect(wipeRequests(server)).toHaveLength(1));
  });

  it('Cancel backs out without deleting', async () => {
    const server = stubServer();
    render(<Settings />);
    await ready();

    await userEvent.click(screen.getByRole('button', { name: 'Delete all data' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(wipeRequests(server)).toHaveLength(0);
    expect(screen.getByRole('button', { name: 'Delete all data' })).toBeInTheDocument();
  });
});
