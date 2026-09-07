/** Dashboard integration: real API client, stubbed transport. */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import * as fixtures from '../test/fixtures';
import { stubServer } from '../test/server';
import { Dashboard } from './Dashboard';

beforeEach(() => {
  localStorage.clear();
  document.documentElement.removeAttribute('data-theme');
});

describe('loading', () => {
  it('shows a busy region before data arrives', async () => {
    stubServer({ delayMs: 50 });
    render(<Dashboard days={90} generate={false} />);

    expect(document.querySelector('[aria-busy="true"]')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
  });
});

describe('successful render', () => {
  beforeEach(() => stubServer());

  it('greets the profile and states the window', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText("Pranay's finances")).toBeInTheDocument());
    expect(screen.getByText(/30 Apr 2026/)).toBeInTheDocument();
  });

  it('shows the monthly spending summary from the backend', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    expect(screen.getByText('₹16,420.00')).toBeInTheDocument();
    expect(screen.getByText('12 expenses over 90 days')).toBeInTheDocument();
  });

  it('shows budget usage', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Budget usage')).toBeInTheDocument());
    expect(screen.getByText('41.0%')).toBeInTheDocument();
  });

  it('renders every chart', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Spending trend')).toBeInTheDocument());
    expect(screen.getByRole('img', { name: /daily spending/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /share of spending by category/i })).toBeInTheDocument();
    expect(screen.getByRole('img', { name: /coverage per habit/i })).toBeInTheDocument();
  });

  it('renders the habit summary', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Check-in completion')).toBeInTheDocument());
    expect(screen.getByText('Current streak')).toBeInTheDocument();
    expect(screen.getByText('Longest streak')).toBeInTheDocument();
  });

  it('renders the event timeline', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Goa trip')).toBeInTheDocument());
  });

  it('renders insight cards for findings and notices', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() =>
      expect(screen.getByText(/Food & dining spending was higher/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/No reliable conclusion can be drawn/)).toBeInTheDocument();
  });

  it('does not turn every total into an insight card', async () => {
    // Insight cards are for findings. A card restating the total the tile
    // above already shows is noise.
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
    expect(screen.queryByText('Something was observed in your data.')).not.toBeInTheDocument();
  });

  it('reports the run provenance in the footer', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText(/Engine 1.0.0/)).toBeInTheDocument());
    expect(screen.getByText(/83 suppressed/)).toBeInTheDocument();
  });

  it('says when no model wrote the prose', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() =>
      expect(screen.getByText(/no model is configured/)).toBeInTheDocument(),
    );
  });
});



describe('error handling', () => {
  it('explains an unreachable backend and offers a retry', async () => {
    stubServer({ networkError: true });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText(/Is the backend running on port 8000/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('surfaces the backend error message', async () => {
    stubServer({
      status: 422,
      errorBody: { detail: "'start_date' cannot be after 'end_date'", error: 'ValidationError' },
    });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByText(/cannot be after/)).toBeInTheDocument();
  });

  it('offers no retry for an error retrying cannot fix', async () => {
    stubServer({ status: 422 });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.queryByRole('button', { name: 'Try again' })).not.toBeInTheDocument();
  });

  it('recovers when a retry succeeds', async () => {
    stubServer({ networkError: true });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());

    stubServer();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    await waitFor(() => expect(screen.getByText('Total spent')).toBeInTheDocument());
  });
});

describe('empty state', () => {
  it('invites data rather than showing zeroed charts', async () => {
    stubServer({ insights: fixtures.emptyAnalysis, narrations: fixtures.emptyNarration });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() =>
      expect(screen.getByText('Nothing recorded in this window yet')).toBeInTheDocument(),
    );
    expect(screen.getByText(/It will not guess in the meantime/)).toBeInTheDocument();
    expect(screen.queryByText('Spending trend')).not.toBeInTheDocument();
  });

  it('says what would unlock an analysis when there are no findings', async () => {
    stubServer({
      insights: { ...fixtures.analysis, notices: [] },
      narrations: { ...fixtures.narratedAnalysis, narrations: [] },
    });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() =>
      expect(screen.getByText('No behavioural relationship yet')).toBeInTheDocument(),
    );
    expect(screen.getByText(/none cleared the effect-size/)).toBeInTheDocument();
  });

  it('points at the notices when the engine explained itself', async () => {
    stubServer({ narrations: { ...fixtures.narratedAnalysis, narrations: [] } });
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() =>
      expect(screen.getByText('No behavioural relationship yet')).toBeInTheDocument(),
    );
    expect(screen.getByText(/logged too rarely to test/)).toBeInTheDocument();
  });
});

describe('accessibility', () => {
  beforeEach(() => stubServer());



  it('gives every chart an accessible description', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Spending trend')).toBeInTheDocument());
    for (const chart of screen.getAllByRole('img')) {
      expect(chart).toHaveAccessibleName();
    }
  });

  it('reaches every chart value without hovering', async () => {
    render(<Dashboard days={90} generate={false} />);

    await waitFor(() => expect(screen.getByText('Spending trend')).toBeInTheDocument());
    await userEvent.click(screen.getByRole('button', { name: /show daily table/i }));

    const table = screen.getByRole('table');
    expect(within(table).getByRole('columnheader', { name: 'Date' })).toBeInTheDocument();
  });
});
