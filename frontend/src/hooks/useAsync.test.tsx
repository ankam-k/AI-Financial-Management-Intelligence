import { act, renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ApiError } from '../api/client';
import { useAsync } from './useAsync';

describe('useAsync', () => {
  it('reports loading, then success', async () => {
    const { result } = renderHook(() => useAsync(async () => 'done', []));

    expect(result.current.isLoading).toBe(true);
    await waitFor(() => expect(result.current.status).toBe('success'));
    expect(result.current.data).toBe('done');
    expect(result.current.error).toBeNull();
  });

  it('surfaces an ApiError with its status', async () => {
    const failure = new ApiError('Nope', 422, 'ValidationError');
    const { result } = renderHook(() =>
      useAsync(async () => {
        throw failure;
      }, []),
    );

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error?.kind).toBe('ValidationError');
    expect(result.current.error?.isRetryable).toBe(false);
  });

  it('wraps a non-ApiError so the UI always has a message', async () => {
    const { result } = renderHook(() =>
      useAsync(async () => {
        throw new Error('kaboom');
      }, []),
    );

    await waitFor(() => expect(result.current.status).toBe('error'));
    expect(result.current.error?.message).toBe('kaboom');
  });

  it('keeps the previous data during a refetch', async () => {
    // The reason this matters: a refetch that cleared `data` would swap the
    // dashboard for a skeleton and jump the layout on every window change.
    let value = 'first';
    const { result } = renderHook(() => useAsync(async () => value, []));

    await waitFor(() => expect(result.current.data).toBe('first'));

    value = 'second';
    act(() => result.current.refetch());

    expect(result.current.data).toBe('first');
    expect(result.current.isRefetching).toBe(true);
    await waitFor(() => expect(result.current.data).toBe('second'));
  });

  it('re-runs when a dependency changes', async () => {
    const run = vi.fn(async () => 'x');
    const { rerender } = renderHook(({ days }) => useAsync(run, [days]), {
      initialProps: { days: 30 },
    });

    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
    rerender({ days: 90 });
    await waitFor(() => expect(run).toHaveBeenCalledTimes(2));
  });

  it('does not re-run when the parent re-renders with the same deps', async () => {
    const run = vi.fn(async () => 'x');
    const { rerender } = renderHook(({ days }) => useAsync(run, [days]), {
      initialProps: { days: 30 },
    });

    await waitFor(() => expect(run).toHaveBeenCalledTimes(1));
    rerender({ days: 30 });
    rerender({ days: 30 });

    expect(run).toHaveBeenCalledTimes(1);
  });

  it('discards a superseded response', async () => {
    // A slow 90-day request must not overwrite a fast 30-day one that the user
    // asked for afterwards.
    const resolvers: ((value: string) => void)[] = [];
    const run = () =>
      new Promise<string>((resolve) => {
        resolvers.push(resolve);
      });

    const { result, rerender } = renderHook(({ days }) => useAsync(run, [days]), {
      initialProps: { days: 90 },
    });

    rerender({ days: 30 });
    await waitFor(() => expect(resolvers).toHaveLength(2));

    // The second (current) request lands first, then the stale one.
    await act(async () => {
      resolvers[1]?.('thirty');
    });
    await act(async () => {
      resolvers[0]?.('ninety');
    });

    expect(result.current.data).toBe('thirty');
  });
});
