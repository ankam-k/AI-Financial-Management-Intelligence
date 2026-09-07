/** The full-page evidence drill-down. */

import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { relationship } from '../test/fixtures';
import { Evidence } from './Evidence';

describe('Evidence', () => {
  it('renders the evidence for a selected relationship', () => {
    render(<Evidence insight={relationship} onBack={vi.fn()} />);

    expect(screen.getByRole('heading', { name: 'Evidence' })).toBeInTheDocument();
    // From EvidencePanel — the comparison and gate sections it always shows.
    expect(screen.getByText('What was analysed')).toBeInTheDocument();
    expect(screen.getByText('Why it passed the gates')).toBeInTheDocument();
  });

  it('shows an honest empty state and a way back when no insight is selected', async () => {
    const onBack = vi.fn();
    render(<Evidence insight={null} onBack={onBack} />);

    expect(screen.getByText('No insight selected')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Go to Insights' }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });
});
