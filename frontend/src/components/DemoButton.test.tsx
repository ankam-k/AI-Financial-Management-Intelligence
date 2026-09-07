import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { DemoButton } from './DemoButton';

function stubSeed(options: { fail?: boolean } = {}) {
  const calls: string[] = [];
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL) => {
      calls.push(typeof input === 'string' ? input : input.toString());
      if (options.fail) {
        return new Response(JSON.stringify({ detail: 'Demo mode is disabled.' }), {
          status: 422,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      return new Response(JSON.stringify({ is_empty: false }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }),
  );
  return calls;
}

describe('DemoButton', () => {
  it('confirms before replacing data', async () => {
    const calls = stubSeed();
    render(<DemoButton onLoaded={() => {}} />);

    await userEvent.click(screen.getByRole('button', { name: 'Load demo data' }));

    expect(screen.getByText(/replaces everything currently recorded/)).toBeInTheDocument();
    expect(calls).toEqual([]);
  });

  it('seeds once confirmed and tells the page to refetch', async () => {
    const calls = stubSeed();
    const onLoaded = vi.fn();
    render(<DemoButton onLoaded={onLoaded} />);

    await userEvent.click(screen.getByRole('button', { name: 'Load demo data' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, load it' }));

    await waitFor(() => expect(onLoaded).toHaveBeenCalledOnce());
    expect(calls.some((url) => url.includes('/api/demo/seed'))).toBe(true);
  });

  it('can be cancelled', async () => {
    const calls = stubSeed();
    render(<DemoButton onLoaded={() => {}} />);

    await userEvent.click(screen.getByRole('button', { name: 'Load demo data' }));
    await userEvent.click(screen.getByRole('button', { name: 'Cancel' }));

    expect(screen.getByRole('button', { name: 'Load demo data' })).toBeInTheDocument();
    expect(calls).toEqual([]);
  });

  it('surfaces the reason when demo mode is off on the server', async () => {
    stubSeed({ fail: true });
    render(<DemoButton onLoaded={() => {}} />);

    await userEvent.click(screen.getByRole('button', { name: 'Load demo data' }));
    await userEvent.click(screen.getByRole('button', { name: 'Yes, load it' }));

    await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(/disabled/));
  });
});
