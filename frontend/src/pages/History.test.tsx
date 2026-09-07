/** History merges the three record types into one filtered, paginated stream. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { stubServer } from '../test/server';
import { History } from './History';

beforeEach(() => localStorage.clear());

describe('History', () => {
  it('merges expenses, check-ins and life events into one stream', async () => {
    stubServer();
    render(<History />);

    expect(await screen.findByText('Blue Tokai')).toBeInTheDocument();
    expect(screen.getByText('Daily check-in')).toBeInTheDocument();
    expect(screen.getByText('Goa trip')).toBeInTheDocument();
  });

  it('filters the stream to a single record type', async () => {
    stubServer();
    render(<History />);

    await screen.findByText('Blue Tokai');
    await userEvent.click(screen.getByRole('button', { name: 'Check-ins' }));

    expect(screen.getByText('Daily check-in')).toBeInTheDocument();
    expect(screen.queryByText('Blue Tokai')).not.toBeInTheDocument();
    expect(screen.queryByText('Goa trip')).not.toBeInTheDocument();
  });

  it('reports an honest empty state when nothing is recorded', async () => {
    stubServer({ expenses: [], checkIns: [], lifeEvents: [] });
    render(<History />);

    await waitFor(() =>
      expect(screen.getByText('Nothing recorded yet')).toBeInTheDocument(),
    );
  });
});
