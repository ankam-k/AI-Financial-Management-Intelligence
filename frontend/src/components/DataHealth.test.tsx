/** Data health reflects backend coverage against backend gate thresholds. */

import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DataHealth } from './DataHealth';
import * as fixtures from '../test/fixtures';

describe('DataHealth', () => {
  it('reports not-ready when every habit sits below the coverage gate', () => {
    render(<DataHealth run={fixtures.analysis.run} completion={fixtures.habitCompletion} />);

    // Fixture coverage tops out at 32.2% sleep, all below the 60% gate.
    expect(screen.getByText('Not enough data yet')).toBeInTheDocument();
    expect(screen.getAllByText('32%').length).toBeGreaterThan(0);
  });

  it('states the gate it is comparing against, read from the run', () => {
    render(<DataHealth run={fixtures.analysis.run} completion={fixtures.habitCompletion} />);

    expect(screen.getByText(/8 complete weeks/)).toBeInTheDocument();
    expect(screen.getByText(/Recorded expenses/)).toBeInTheDocument();
  });
});
