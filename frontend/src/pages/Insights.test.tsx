/** Insights: relationships as associations, evidence drill-down, no-insight, AI banner. */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import { Insights } from './Insights';
import * as fixtures from '../test/fixtures';
import { stubServer } from '../test/server';

const AVAILABLE = { available: true };

beforeEach(() => localStorage.clear());

describe('behavioural relationships', () => {
  it('labels a T3 finding as an association, never a cause', async () => {
    stubServer();
    render(<Insights days={90} generate={false} availability={AVAILABLE} />);

    await waitFor(() => expect(screen.getByText('Behavioural relationships')).toBeInTheDocument());
    expect(screen.getAllByText('Association').length).toBeGreaterThan(0);
    expect(screen.getByText(/Statistical confidence/)).toBeInTheDocument();
  });

  it('opens the evidence and keeps raw p-values behind technical details', async () => {
    stubServer();
    render(<Insights days={90} generate={false} availability={AVAILABLE} />);

    await waitFor(() => expect(screen.getByText('Behavioural relationships')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /Show evidence/ }));

    expect(screen.getByText('The comparison')).toBeInTheDocument();
    expect(screen.getAllByText(/weeks without exercise/).length).toBeGreaterThan(0);
    // The p-value exists, but only inside the collapsed technical disclosure.
    const summary = screen.getByText('Technical details');
    expect(summary.closest('details')).toBeTruthy();
    expect(screen.getByText(/p-value/).closest('details')).toBe(summary.closest('details'));
  });
});

describe('no insight', () => {
  it('explains why rather than showing a bare zero', async () => {
    const noRelationship = {
      ...fixtures.analysis,
      insights: fixtures.analysis.insights.filter((i) => i.type !== 'BEHAVIOR_RELATIONSHIP'),
    };
    stubServer({
      insights: noRelationship,
      narrations: { ...fixtures.narratedAnalysis, narrations: [] },
    });
    render(<Insights days={90} generate={false} availability={AVAILABLE} />);

    await waitFor(() =>
      expect(screen.getByText('No behavioural relationship yet')).toBeInTheDocument(),
    );
    expect(screen.getByText(/logged too rarely to test/)).toBeInTheDocument();
  });
});

describe('AI availability', () => {
  it('shows a calm banner when the model is unavailable', async () => {
    stubServer();
    render(<Insights days={90} generate={false} availability={{ available: false }} />);

    await waitFor(() =>
      expect(screen.getByText(/AI explanations are optional/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/analysis engine is the source of truth/)).toBeInTheDocument();
  });

  it('shows no banner when the model is available', async () => {
    stubServer();
    render(<Insights days={90} generate={false} availability={AVAILABLE} />);

    await waitFor(() => expect(screen.getByText('Behavioural relationships')).toBeInTheDocument());
    expect(screen.queryByText(/AI explanations are optional/)).not.toBeInTheDocument();
  });
});
