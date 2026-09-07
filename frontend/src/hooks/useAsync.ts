/**
 * The one place loading, error and refetch semantics are defined.
 *
 * Two behaviours worth naming:
 *
 * **A refetch does not clear the data.** `status` becomes `refetching` while
 * the previous value stays available, so the UI dims what it has instead of
 * flashing a skeleton and jumping the layout.
 *
 * **A superseded request cannot win.** Each run gets a token; a response whose
 * token is stale is discarded. Without it, a slow request for a 90-day window
 * can land after a fast one for 30 days and silently show the wrong data.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';

export type AsyncStatus = 'idle' | 'loading' | 'refetching' | 'success' | 'error';

export interface AsyncState<T> {
  data: T | null;
  error: ApiError | null;
  status: AsyncStatus;
  isLoading: boolean;
  isRefetching: boolean;
  refetch: () => void;
}

export function useAsync<T>(
  run: (signal: AbortSignal) => Promise<T>,
  deps: readonly unknown[],
): AsyncState<T> {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [status, setStatus] = useState<AsyncStatus>('idle');
  const [attempt, setAttempt] = useState(0);

  const token = useRef(0);
  const hasData = useRef(false);

  // `run` is typically an inline arrow, so it is a new function every render.
  // Keeping it in a ref lets the effect depend on `deps` alone rather than
  // refiring on every parent re-render.
  const runRef = useRef(run);
  runRef.current = run;

  useEffect(() => {
    const current = ++token.current;
    const controller = new AbortController();

    setStatus(hasData.current ? 'refetching' : 'loading');
    setError(null);

    runRef
      .current(controller.signal)
      .then((result) => {
        if (current !== token.current) return;
        hasData.current = true;
        setData(result);
        setStatus('success');
      })
      .catch((cause: unknown) => {
        if (current !== token.current || controller.signal.aborted) return;
        setError(
          cause instanceof ApiError
            ? cause
            : new ApiError(
                cause instanceof Error ? cause.message : 'Something went wrong.',
                0,
                'UnknownError',
              ),
        );
        setStatus('error');
      });

    return () => controller.abort();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, attempt]);

  const refetch = useCallback(() => setAttempt((value) => value + 1), []);

  return {
    data,
    error,
    status,
    isLoading: status === 'loading',
    isRefetching: status === 'refetching',
    refetch,
  };
}
