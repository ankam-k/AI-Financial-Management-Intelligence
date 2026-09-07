/** The card shell every panel shares, and the chart variant with a table view. */

import { useId, useState, type ReactNode } from 'react';

export interface CardProps {
  title?: string;
  hint?: string;
  footnote?: ReactNode;
  className?: string;
  children: ReactNode;
}

export function Card({ title, hint, footnote, className = '', children }: CardProps) {
  return (
    <section className={`card ${className}`.trim()} aria-label={title}>
      {title || hint ? (
        <header className="card__header">
          {title ? <h3 className="card__title">{title}</h3> : <span />}
          {hint ? <span className="card__hint">{hint}</span> : null}
        </header>
      ) : null}
      <div className="card__body">{children}</div>
      {footnote ? <p className="card__footnote">{footnote}</p> : null}
    </section>
  );
}

export interface ChartCardProps extends CardProps {
  /**
   * The chart's data as a table. Every chart has one: a tooltip may enhance a
   * value but must never be the only way to read it, and colour alone must
   * never carry meaning.
   */
  table?: ReactNode;
  tableLabel?: string;
}

export function ChartCard({
  title,
  hint,
  footnote,
  className = '',
  table,
  tableLabel = 'table',
  children,
}: ChartCardProps) {
  const [showTable, setShowTable] = useState(false);
  const regionId = useId();

  return (
    <section className={`card ${className}`.trim()} aria-label={title}>
      <header className="card__header">
        {title ? <h3 className="card__title">{title}</h3> : <span />}
        <span className="card__hint">
          {hint ? <span style={{ marginRight: 8 }}>{hint}</span> : null}
          {table ? (
            <button
              type="button"
              className="table-toggle"
              aria-expanded={showTable}
              aria-controls={regionId}
              onClick={() => setShowTable((open) => !open)}
            >
              {showTable ? 'Show chart' : `Show ${tableLabel}`}
            </button>
          ) : null}
        </span>
      </header>
      <div className="card__body" id={regionId}>
        {showTable && table ? table : children}
      </div>
      {footnote ? <p className="card__footnote">{footnote}</p> : null}
    </section>
  );
}
