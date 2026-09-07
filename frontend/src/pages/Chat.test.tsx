/** The chat page: sending, states, retry, clearing — and honesty about memory. */

import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { Chat } from './Chat';
import * as fixtures from '../test/fixtures';
import { stubChat } from '../test/server';

function renderChat() {
  return render(<Chat days={90} generate={false} />);
}

async function ask(question: string) {
  const input = screen.getByRole('textbox', { name: /ask a question/i });
  await userEvent.type(input, question);
  await userEvent.click(screen.getByRole('button', { name: 'Ask' }));
}

beforeEach(() => {
  vi.restoreAllMocks();
});

describe('the empty state', () => {
  it('says what the assistant does and does not do', () => {
    stubChat();
    renderChat();

    expect(screen.getByText('Ask about your money')).toBeInTheDocument();
    expect(screen.getByText(/won't recommend financial products/)).toBeInTheDocument();
  });

  it('says each question is answered on its own', () => {
    // ⭐ The server keeps no conversation. A UI implying memory would set an
    // expectation the backend deliberately does not meet.
    stubChat();
    renderChat();

    expect(screen.getByText(/Nothing you ask is remembered between questions/)).toBeInTheDocument();
  });

  it('offers starter questions from the backend capabilities', async () => {
    stubChat();
    renderChat();

    await waitFor(() =>
      expect(
        screen.getByRole('button', { name: 'How much did I spend this month?' }),
      ).toBeInTheDocument(),
    );
  });

  it('falls back to local examples when capabilities cannot be fetched', async () => {
    stubChat({ capabilitiesFail: true });
    renderChat();

    expect(
      screen.getByRole('button', { name: 'How much did I spend this month?' }),
    ).toBeInTheDocument();
  });

  it('sends a starter question when clicked', async () => {
    const server = stubChat();
    renderChat();

    await userEvent.click(screen.getByRole('button', { name: 'Am I over budget?' }));

    await waitFor(() => expect(server.questions).toContain('Am I over budget?'));
  });
});

describe('asking a question', () => {
  it('shows the question, then the answer', async () => {
    stubChat();
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() =>
      expect(screen.getByText(/You spent .*over the last/)).toBeInTheDocument(),
    );
    expect(screen.getByText('How much did I spend?')).toBeInTheDocument();
  });

  it('shows a loading indicator while waiting', async () => {
    stubChat({ delayMs: 60 });
    renderChat();

    await ask('How much did I spend?');

    expect(screen.getByLabelText('Thinking')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByLabelText('Thinking')).not.toBeInTheDocument());
  });

  it('renders markdown without injecting HTML', async () => {
    stubChat({
      answer: {
        ...fixtures.chatAnswer,
        answer: 'You spent **a lot**.\n\n- one item\n- another item',
      },
    });
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() => expect(screen.getByText('a lot')).toBeInTheDocument());
    expect(screen.getByText('a lot').tagName).toBe('STRONG');
    expect(screen.getAllByRole('listitem').length).toBeGreaterThanOrEqual(2);
  });

  it('never renders raw HTML from a model answer', async () => {
    // The renderer builds React elements; it never touches innerHTML, so a
    // tag in a generated answer is literal text.
    stubChat({
      answer: { ...fixtures.chatAnswer, answer: 'Careful: <img src=x onerror=alert(1)> here.' },
    });
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() => expect(screen.getByText(/onerror=alert\(1\)/)).toBeInTheDocument());
    expect(document.querySelector('img')).toBeNull();
  });

  it('clears the input after sending', async () => {
    stubChat();
    renderChat();

    await ask('How much did I spend?');

    expect(screen.getByRole('textbox', { name: /ask a question/i })).toHaveValue('');
  });

  it('will not send an empty question', async () => {
    const server = stubChat();
    renderChat();

    expect(screen.getByRole('button', { name: 'Ask' })).toBeDisabled();
    expect(server.questions).toEqual([]);
  });

  it('sends the window it was given', async () => {
    const server = stubChat();
    render(<Chat days={30} generate={false} />);

    await ask('How much did I spend?');

    await waitFor(() => expect(server.bodies[0]).toMatchObject({ days: 30 }));
  });

  it('sends no conversation id or history', async () => {
    // ⭐ Single-turn is enforced by there being nothing to send.
    const server = stubChat();
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() => expect(server.bodies).toHaveLength(1));
    expect(Object.keys(server.bodies[0] ?? {}).sort()).toEqual([
      'days',
      'generate',
      'question',
    ]);
  });
});

describe('refusals', () => {
  it('renders a refusal as an answer, not an error', async () => {
    stubChat({ answer: fixtures.chatRefusal });
    renderChat();

    await ask('Should I invest my savings?');

    await waitFor(() =>
      expect(screen.getByText('Outside what this assistant does')).toBeInTheDocument(),
    );
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });

  it('labels a data-shortage refusal differently from a boundary', async () => {
    stubChat({
      answer: { ...fixtures.chatRefusal, refusal_reason: 'INSUFFICIENT_DATA' },
    });
    renderChat();

    await ask('What happened during my trip?');

    await waitFor(() =>
      expect(screen.getByText('Not enough recorded data')).toBeInTheDocument(),
    );
  });
});

describe('provenance', () => {
  it('says where the words came from', async () => {
    stubChat();
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() =>
      expect(screen.getByText(/Written from a template/)).toBeInTheDocument(),
    );
  });

  it('names the insights the answer used', async () => {
    stubChat();
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() => expect(screen.getByText(/spending total/)).toBeInTheDocument());
  });

  it('discloses a rejected generation', async () => {
    stubChat({
      answer: {
        ...fixtures.chatAnswer,
        validation_failures: [{ validator: 'provenance', detail: 'invented a number' }],
      },
    });
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() =>
      expect(screen.getByText(/A generated version was rejected/)).toBeInTheDocument(),
    );
  });
});

describe('failure and retry', () => {
  it('shows an error with a retry when the request fails', async () => {
    stubChat({ networkError: true });
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());
    expect(screen.getByRole('button', { name: 'Try again' })).toBeInTheDocument();
  });

  it('re-sends the original question on retry', async () => {
    const server = stubChat({ networkError: true });
    renderChat();

    await ask('How much did I spend?');
    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument());

    server.recover();
    await userEvent.click(screen.getByRole('button', { name: 'Try again' }));

    await waitFor(() =>
      expect(screen.getByText(/You spent .*over the last/)).toBeInTheDocument(),
    );
    expect(server.questions).toEqual(['How much did I spend?', 'How much did I spend?']);
  });
});

describe('clearing', () => {
  it('offers no clear button until there is something to clear', () => {
    stubChat();
    renderChat();

    expect(screen.queryByRole('button', { name: 'Clear' })).not.toBeInTheDocument();
  });

  it('empties the transcript without calling the server', async () => {
    const server = stubChat();
    renderChat();

    await ask('How much did I spend?');
    await waitFor(() => expect(screen.getByText('How much did I spend?')).toBeInTheDocument());

    const before = server.questions.length;
    await userEvent.click(screen.getByRole('button', { name: 'Clear' }));

    expect(screen.queryByText('How much did I spend?')).not.toBeInTheDocument();
    expect(screen.getByText('Ask about your money')).toBeInTheDocument();
    expect(server.questions).toHaveLength(before);
  });
});

describe('accessibility', () => {
  it('labels the input', () => {
    stubChat();
    renderChat();

    expect(screen.getByRole('textbox', { name: /ask a question/i })).toBeInTheDocument();
  });

  it('announces the answer region politely', async () => {
    stubChat({ delayMs: 40 });
    renderChat();

    await ask('How much did I spend?');

    expect(document.querySelector('[aria-live="polite"]')).toBeInTheDocument();
  });

  it('keeps the transcript an ordered list', async () => {
    stubChat();
    renderChat();

    await ask('How much did I spend?');

    await waitFor(() => expect(screen.getByRole('list')).toBeInTheDocument());
    const log = screen.getByRole('list');
    expect(within(log).getAllByRole('listitem')).toHaveLength(1);
  });
});
