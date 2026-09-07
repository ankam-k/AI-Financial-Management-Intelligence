/**
 * Chat state — in the browser, and only in the browser.
 *
 * The transcript here is a **display artefact**. The server keeps no
 * conversation, and no previous turn is ever sent with a question: each one is
 * answered independently from the analysis window (SRS-7.7, PDR-037🟠). That
 * is why `send` takes a question and nothing else, and why "clear" is a local
 * `setState` rather than a request.
 *
 * Retry re-sends the original question, not a repair of the failed one.
 */

import { useCallback, useRef, useState } from 'react';
import { ApiError } from '../api/client';
import { askChat } from '../api/endpoints';
import type { ChatResponse } from '../api/types';

export type TurnStatus = 'pending' | 'done' | 'failed';

export interface ChatTurn {
  id: string;
  question: string;
  status: TurnStatus;
  response: ChatResponse | null;
  error: ApiError | null;
}

export interface UseChat {
  turns: ChatTurn[];
  isBusy: boolean;
  send: (question: string) => void;
  retry: (turnId: string) => void;
  clear: () => void;
}

export function useChat(days: number, generate: boolean): UseChat {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const counter = useRef(0);

  const run = useCallback(
    (turnId: string, question: string) => {
      setTurns((current) =>
        current.map((turn) =>
          turn.id === turnId ? { ...turn, status: 'pending', error: null } : turn,
        ),
      );

      askChat({ question, days, generate })
        .then((response) =>
          setTurns((current) =>
            current.map((turn) =>
              turn.id === turnId ? { ...turn, status: 'done', response } : turn,
            ),
          ),
        )
        .catch((cause: unknown) =>
          setTurns((current) =>
            current.map((turn) =>
              turn.id === turnId
                ? {
                    ...turn,
                    status: 'failed',
                    error:
                      cause instanceof ApiError
                        ? cause
                        : new ApiError('Something went wrong.', 0, 'UnknownError'),
                  }
                : turn,
            ),
          ),
        );
    },
    [days, generate],
  );

  const send = useCallback(
    (question: string) => {
      const trimmed = question.trim();
      if (!trimmed) return;
      const id = `turn-${++counter.current}`;
      setTurns((current) => [
        ...current,
        { id, question: trimmed, status: 'pending', response: null, error: null },
      ]);
      run(id, trimmed);
    },
    [run],
  );

  const retry = useCallback(
    (turnId: string) => {
      const turn = turns.find((item) => item.id === turnId);
      if (turn) run(turnId, turn.question);
    },
    [run, turns],
  );

  const clear = useCallback(() => setTurns([]), []);

  return {
    turns,
    isBusy: turns.some((turn) => turn.status === 'pending'),
    send,
    retry,
    clear,
  };
}
