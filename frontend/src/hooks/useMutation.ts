/**
 * The write-side counterpart to `useAsync`.
 *
 * A form needs the same four states a read does — idle, submitting, error,
 * success — but triggered by an event rather than a dependency change, and it
 * must never leave a half-open request behind when the component unmounts. This
 * is the one place that logic lives, so a page's submit handler stays a call to
 * `mutate` and a read of `status`.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { ApiError } from '../api/client';

export type MutationStatus = 'idle' | 'submitting' | 'success' | 'error';

export interface MutationState<Args extends unknown[], Result> {
  status: MutationStatus;
  error: ApiError | null;
  isSubmitting: boolean;
  /** Runs the mutation; resolves to the result, or `null` if it failed. */
  mutate: (...args: Args) => Promise<Result | null>;
  reset: () => void;
}

export function useMutation<Args extends unknown[], Result>(
  run: (...args: Args) => Promise<Result>,
): MutationState<Args, Result> {
  const [status, setStatus] = useState<MutationStatus>('idle');
  const [error, setError] = useState<ApiError | null>(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const runRef = useRef(run);
  runRef.current = run;

  const mutate = useCallback(async (...args: Args): Promise<Result | null> => {
    setStatus('submitting');
    setError(null);
    try {
      const result = await runRef.current(...args);
      if (mounted.current) setStatus('success');
      return result;
    } catch (cause: unknown) {
      if (mounted.current) {
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
      }
      return null;
    }
  }, []);

  const reset = useCallback(() => {
    setStatus('idle');
    setError(null);
  }, []);

  return { status, error, isSubmitting: status === 'submitting', mutate, reset };
}
