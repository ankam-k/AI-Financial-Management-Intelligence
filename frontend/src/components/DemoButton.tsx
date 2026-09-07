/**
 * Load the demo dataset from the empty state.
 *
 * The point is an interview, not convenience: an empty dashboard is a correct
 * response to an empty database, and it is also the least useful thing to look
 * at. One click puts nine months of data behind it — the same dataset the CLI
 * loads, from the same generator, with the same fixed seed.
 *
 * It is destructive, so it says so before doing it. When demo mode is off on
 * the server the button is absent rather than broken.
 */

import { useState } from 'react';
import { ApiError } from '../api/client';
import { seedDemo } from '../api/endpoints';

export function DemoButton({ onLoaded }: { onLoaded: () => void }) {
  const [state, setState] = useState<'idle' | 'confirm' | 'loading' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const load = () => {
    setState('loading');
    seedDemo()
      .then(() => {
        setState('idle');
        onLoaded();
      })
      .catch((cause: unknown) => {
        setState('error');
        setMessage(
          cause instanceof ApiError ? cause.message : 'Could not load the demo data.',
        );
      });
  };

  if (state === 'error') {
    return (
      <p className="state__detail" role="alert">
        {message}
      </p>
    );
  }

  if (state === 'confirm') {
    return (
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        <span className="state__detail" style={{ width: '100%' }}>
          This replaces everything currently recorded.
        </span>
        <button type="button" className="state__action" onClick={load}>
          Yes, load it
        </button>
        <button type="button" className="state__action" onClick={() => setState('idle')}>
          Cancel
        </button>
      </div>
    );
  }

  return (
    <button
      type="button"
      className="state__action"
      disabled={state === 'loading'}
      onClick={() => setState('confirm')}
    >
      {state === 'loading' ? 'Loading…' : 'Load demo data'}
    </button>
  );
}
