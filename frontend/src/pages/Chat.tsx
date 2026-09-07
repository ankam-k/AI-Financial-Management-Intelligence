/**
 * The chat page.
 *
 * The transcript is local and the server is stateless, so this page is honest
 * about it: the empty state says each question is answered on its own, and
 * "Clear" is a local reset rather than a request. A UI that implied memory
 * would set an expectation the backend deliberately does not meet
 * (SRS-7.7, PDR-037🟠).
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getChatCapabilities } from '../api/endpoints';
import { MessageBubble } from '../components/chat/MessageBubble';
import { useAsync } from '../hooks/useAsync';
import { useChat } from '../hooks/useChat';

const FALLBACK_EXAMPLES = [
  'How much did I spend this month?',
  'Which category did I spend the most on?',
  'Am I over budget?',
  'How has my gym routine affected my spending?',
];

export function Chat({ days, generate }: { days: number; generate: boolean }) {
  const { turns, isBusy, send, retry, clear } = useChat(days, generate);
  const [draft, setDraft] = useState('');
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Starter questions come from the backend's routing rules, so they cannot
  // drift into suggesting something the intent map would refuse.
  const capabilities = useAsync(
    useCallback((signal: AbortSignal) => getChatCapabilities(signal), []),
    [],
  );
  const examples = capabilities.data?.examples ?? FALLBACK_EXAMPLES;

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [turns]);

  const submit = (question: string) => {
    send(question);
    setDraft('');
    inputRef.current?.focus();
  };

  return (
    <div className="chat">
      {turns.length === 0 ? (
        <div className="chat__intro">
          <h2 className="chat__intro-title">Ask about your money</h2>
          <p className="chat__intro-detail">
            I answer from the analysis that has already run over your recorded data — I
            don't recompute anything, and I won't recommend financial products.
          </p>
          <p className="chat__intro-detail chat__intro-detail--quiet">
            Each question is answered on its own. Nothing you ask is remembered between
            questions.
          </p>
          <ul className="chat__suggestions">
            {examples.map((example) => (
              <li key={example}>
                <button type="button" onClick={() => submit(example)}>
                  {example}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <ol className="chat__log">
          {turns.map((turn) => (
            <MessageBubble key={turn.id} turn={turn} onRetry={() => retry(turn.id)} />
          ))}
        </ol>
      )}

      <div ref={endRef} />

      <form
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          submit(draft);
        }}
      >
        <label className="visually-hidden" htmlFor="chat-input">
          Ask a question about your spending
        </label>
        <textarea
          id="chat-input"
          ref={inputRef}
          className="composer__input"
          rows={1}
          value={draft}
          placeholder="Ask about your spending, habits or events…"
          maxLength={capabilities.data?.max_question_chars ?? 500}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              submit(draft);
            }
          }}
        />
        <div className="composer__actions">
          {turns.length > 0 ? (
            <button type="button" className="composer__clear" onClick={clear}>
              Clear
            </button>
          ) : null}
          <button type="submit" className="composer__send" disabled={!draft.trim() || isBusy}>
            {isBusy ? 'Thinking…' : 'Ask'}
          </button>
        </div>
      </form>
    </div>
  );
}
