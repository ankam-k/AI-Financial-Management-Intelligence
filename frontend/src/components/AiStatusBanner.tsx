/**
 * AI availability, stated calmly.
 *
 * The analysis engine is the source of truth; the model only rewrites its prose
 * (constraint 4/7). So when no model is configured or reachable, this is not an
 * error — it is a supported, fully-valid mode. The banner says so in a neutral
 * register and never with an alarm colour, so the app does not look broken to a
 * user who simply has no local model.
 *
 * Availability is read from `getLLMStatus` when it answers usefully, and
 * inferred from the narration provider (`'none'`) otherwise.
 */

import type { LLMStatus } from '../api/types';

export interface AiAvailability {
  available: boolean;
  /** A short human note, e.g. the provider/model or the reason it is off. */
  detail?: string;
}

/**
 * Reconcile the optional status endpoint with the always-present narration
 * provider. The endpoint wins when it answered; the provider is the fallback.
 */
export function resolveAiAvailability(
  status: LLMStatus | null,
  narrationProvider: string,
): AiAvailability {
  if (status) {
    return { available: status.available, detail: status.detail || `${status.provider} · ${status.model}` };
  }
  return { available: narrationProvider !== 'none' };
}

export function AiStatusBanner({ availability }: { availability: AiAvailability }) {
  if (availability.available) return null;

  return (
    <div className="ai-banner" role="status">
      <span className="ai-banner__badge" aria-hidden="true">
        AI
      </span>
      <p className="ai-banner__text">
        <strong>AI explanations are optional and currently unavailable.</strong> The analysis and
        insights are fully valid — explanations are shown from templates instead. The analysis
        engine is the source of truth; the model only rewrites its prose.
        {availability.detail ? (
          <span className="ai-banner__detail"> {availability.detail}</span>
        ) : null}
      </p>
    </div>
  );
}
