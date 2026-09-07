/**
 * "A generated version was rejected" — the same disclosure in two places.
 *
 * When a model wrote prose and a validator caught it inventing a figure, the
 * fallback to a template is not something to hide: the reader is entitled to
 * know a check fired and which one. The InsightCard and the chat MessageBubble
 * both owe that disclosure, so the markup lives here once rather than drifting
 * apart in two copies.
 */

import type { ValidationFailure } from '../api/types';

export function RejectedGeneration({
  failures,
  className = 'card__footnote',
}: {
  failures: ValidationFailure[];
  className?: string;
}) {
  if (failures.length === 0) return null;

  return (
    <details className={className} style={{ marginTop: 10 }}>
      <summary style={{ cursor: 'pointer' }}>
        A generated version was rejected ({failures.length} check
        {failures.length === 1 ? '' : 's'})
      </summary>
      <ul style={{ margin: '6px 0 0', paddingLeft: 18 }}>
        {failures.map((failure, index) => (
          <li key={index}>
            <strong>{failure.validator}</strong>: {failure.detail}
          </li>
        ))}
      </ul>
    </details>
  );
}
