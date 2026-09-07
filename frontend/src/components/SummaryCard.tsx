/**
 * A stat tile: one number, its label, and optional context.
 *
 * When the story is a single figure, the figure is the chart. A one-bar bar
 * chart or a two-slice pie would say the same thing with more ink.
 */

import type { ReactNode } from 'react';

export type StatusTone = 'good' | 'warning' | 'critical' | 'neutral';

export function StatusChip({ tone, children }: { tone: StatusTone; children: ReactNode }) {
  // A status colour never carries meaning alone — the dot always ships with
  // the word beside it.
  return (
    <span className={`chip chip--${tone}`}>
      <span className="chip__dot" aria-hidden="true" />
      {children}
    </span>
  );
}

export interface SummaryCardProps {
  label: string;
  value: string;
  meta?: ReactNode;
  chip?: { tone: StatusTone; text: string };
  muted?: boolean;
}

export function SummaryCard({ label, value, meta, chip, muted = false }: SummaryCardProps) {
  return (
    <section className={`card ${muted ? 'stat--muted' : ''}`.trim()}>
      <div className="card__header">
        <h3 className="card__title">{label}</h3>
        {chip ? <StatusChip tone={chip.tone}>{chip.text}</StatusChip> : null}
      </div>
      <p className="stat__value">{value}</p>
      {meta ? <p className="stat__meta">{meta}</p> : null}
    </section>
  );
}
