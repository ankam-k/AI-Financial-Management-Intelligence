/**
 * One turn: the question, then the answer or the reason there isn't one.
 *
 * A refusal is rendered as an answer, not an error. "I won't recommend a fund"
 * and "I have no data for that" are correct outcomes of a well-formed
 * question, and styling them as failures would tell the user the product is
 * broken when it is working exactly as designed.
 */

import type { ChatTurn } from '../../hooks/useChat';
import type { RefusalReason } from '../../api/types';
import { Markdown } from './Markdown';
import { RejectedGeneration } from '../RejectedGeneration';

const REFUSAL_LABEL: Record<RefusalReason, string> = {
  PROHIBITED_TOPIC: 'Outside what this assistant does',
  NOT_ANSWERABLE_FROM_ANALYSIS: 'No finding behind this',
  INSUFFICIENT_DATA: 'Not enough recorded data',
  UNCLEAR: "Didn't catch that",
};

export function MessageBubble({ turn, onRetry }: { turn: ChatTurn; onRetry: () => void }) {
  const response = turn.response;

  return (
    <li className="turn">
      <div className="turn__question">
        <p>{turn.question}</p>
      </div>

      {turn.status === 'pending' ? (
        <div className="turn__answer" aria-live="polite">
          <span className="typing" aria-label="Thinking">
            <span />
            <span />
            <span />
          </span>
        </div>
      ) : turn.status === 'failed' ? (
        <div className="turn__answer turn__answer--failed" role="alert">
          <p>{turn.error?.message ?? 'Something went wrong.'}</p>
          <button type="button" className="state__action" onClick={onRetry}>
            Try again
          </button>
        </div>
      ) : response ? (
        <div className="turn__answer">
          {response.status === 'REFUSED' && response.refusal_reason ? (
            <p className="turn__refusal-label">{REFUSAL_LABEL[response.refusal_reason]}</p>
          ) : null}

          <Markdown text={response.answer} />

          <div className="turn__meta">
            <span>
              {response.source === 'LLM'
                ? `Written by ${response.model}`
                : 'Written from a template'}
            </span>
            {response.citations.length > 0 ? (
              <span>
                {' · '}
                Based on{' '}
                {response.citations
                  .map((citation) => citation.insight_type.replace(/_/g, ' ').toLowerCase())
                  .join(', ')}
              </span>
            ) : null}
          </div>

          <RejectedGeneration failures={response.validation_failures} className="turn__meta" />
        </div>
      ) : null}
    </li>
  );
}
