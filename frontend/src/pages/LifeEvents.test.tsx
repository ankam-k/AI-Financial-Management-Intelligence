/** The life-event form: title required, end date not before start, neutral tone. */

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { LifeEvents } from './LifeEvents';
import { stubServer } from '../test/server';

beforeEach(() => localStorage.clear());

function postBody(server: ReturnType<typeof stubServer>) {
  return server.requests.find((r) => r.method === 'POST' && r.url.includes('/api/life-events'))?.body;
}

async function ready() {
  await waitFor(() => expect(screen.getByText('Annotate an event')).toBeInTheDocument());
}

describe('life event form', () => {
  it('requires a title', async () => {
    const server = stubServer({ lifeEvents: [] });
    render(<LifeEvents />);
    await ready();

    await userEvent.click(screen.getByRole('button', { name: 'Annotate event' }));

    expect(screen.getByText(/Give the event a title/)).toBeInTheDocument();
    expect(postBody(server)).toBeUndefined();
  });

  it('rejects an end date before the start date', async () => {
    const server = stubServer({ lifeEvents: [] });
    render(<LifeEvents />);
    await ready();

    await userEvent.type(screen.getByLabelText('Title'), 'Goa trip');
    fireEvent.change(screen.getByLabelText('Start date'), { target: { value: '2026-07-10' } });
    fireEvent.change(screen.getByLabelText(/End date/), { target: { value: '2026-07-05' } });
    await userEvent.click(screen.getByRole('button', { name: 'Annotate event' }));

    expect(screen.getByText(/end date cannot be before the start date/)).toBeInTheDocument();
    expect(postBody(server)).toBeUndefined();
  });

  it('sends a valid event', async () => {
    const server = stubServer({ lifeEvents: [] });
    render(<LifeEvents />);
    await ready();

    await userEvent.type(screen.getByLabelText('Title'), 'Goa trip');
    await userEvent.click(screen.getByRole('button', { name: 'Annotate event' }));

    await waitFor(() => expect(postBody(server)).toBeTruthy());
    expect(postBody(server)).toMatchObject({ title: 'Goa trip', event_type: 'TRAVEL' });
  });

  it('frames events as context, not cause', async () => {
    stubServer({ lifeEvents: [] });
    render(<LifeEvents />);
    await ready();

    expect(screen.getByText(/never described as causing your spending/)).toBeInTheDocument();
  });
});
