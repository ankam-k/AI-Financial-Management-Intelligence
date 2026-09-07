/**
 * Loading, error and empty.
 *
 * Empty is not an error and not a bug — a new user with three days of data is
 * the product working as designed (PDR-030). It says what is missing and what
 * would unlock the analysis, in the same register the backend's data
 * sufficiency notices use.
 */

import type { ReactNode } from 'react';
import type { ApiError } from '../api/client';

export function SkeletonCard({ height = 180 }: { height?: number }) {
  return (
    <div className="card" aria-hidden="true">
      <div className="skeleton" style={{ width: '40%', height: 12 }} />
      <div className="skeleton" style={{ width: '100%', height, marginTop: 16 }} />
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: ApiError; onRetry?: () => void }) {
  return (
    <div className="state state--error" role="alert">
      <p className="state__title">Could not load your dashboard</p>
      <p className="state__detail">{error.message}</p>
      {error.isRetryable && onRetry ? (
        <button type="button" className="state__action" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({
  title,
  detail,
  children,
}: {
  title: string;
  detail?: string;
  children?: ReactNode;
}) {
  return (
    <div className="state">
      <p className="state__title">{title}</p>
      {detail ? <p className="state__detail">{detail}</p> : null}
      {children}
    </div>
  );
}

/** The in-card empty state, sized so a missing chart does not collapse a row. */
export function ChartEmpty({ children }: { children: ReactNode }) {
  return <div className="chart__empty">{children}</div>;
}
