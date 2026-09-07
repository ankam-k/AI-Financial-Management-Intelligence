/**
 * A stubbed `fetch` that routes by path, so tests exercise the real API client
 * — its query building, its error envelope handling, its network-failure path
 * — rather than a mock of it.
 */

import { vi } from 'vitest';
import * as fixtures from './fixtures';

export interface RouteOverrides {
  profile?: unknown;
  insights?: unknown;
  narrations?: unknown;
  /** The `/api/narrations/status` (LLMStatus) payload. */
  llmStatus?: unknown;
  /** GET list payloads for the data-entry pages. */
  expenses?: unknown;
  checkIns?: unknown;
  lifeEvents?: unknown;
  /**
   * The signed-in account for `/api/auth/*`. Defaults to `fixtures.authUser`;
   * pass `null` to make `/api/auth/me` answer 401 (the logged-out app).
   */
  authUser?: unknown | null;
  /** The `/api/demo/status` payload (controls whether "Explore demo" shows). */
  demoStatus?: unknown;
  status?: number;
  errorBody?: { detail: string; error: string };
  /** Reject at the network level, as an unreachable backend would. */
  networkError?: boolean;
  /** Resolve after this many ms, to observe the loading state. */
  delayMs?: number;
}

export interface CapturedRequest {
  url: string;
  method: string;
  body: Record<string, unknown> | null;
}

export interface StubbedServer {
  /** Every URL requested, in order. */
  calls: string[];
  /** Every request with its method and parsed JSON body. */
  requests: CapturedRequest[];
}

export function stubServer(overrides: RouteOverrides = {}): StubbedServer {
  const calls: string[] = [];
  const requests: CapturedRequest[] = [];

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();
    const method = (init?.method ?? 'GET').toUpperCase();
    let body: Record<string, unknown> | null = null;
    if (init?.body) {
      try {
        body = JSON.parse(String(init.body)) as Record<string, unknown>;
      } catch {
        body = null;
      }
    }
    calls.push(url);
    requests.push({ url, method, body });

    if (overrides.networkError) throw new TypeError('Failed to fetch');
    if (overrides.delayMs) await new Promise((resolve) => setTimeout(resolve, overrides.delayMs));

    if (overrides.status && overrides.status >= 400) {
      return new Response(
        JSON.stringify(overrides.errorBody ?? { detail: 'Boom', error: 'ValidationError' }),
        { status: overrides.status, headers: { 'Content-Type': 'application/json' } },
      );
    }

    // ── Auth routes (V1.2) ────────────────────────────────────────────────
    if (url.includes('/api/auth/me')) {
      const account = 'authUser' in overrides ? overrides.authUser : fixtures.authUser;
      if (account === null) {
        return new Response(
          JSON.stringify({ detail: 'Not authenticated', error: 'AuthError' }),
          { status: 401, headers: { 'Content-Type': 'application/json' } },
        );
      }
      return json(account);
    }
    if (url.includes('/api/auth/logout')) {
      return new Response(null, { status: 204 });
    }
    if (
      url.includes('/api/auth/login') ||
      url.includes('/api/auth/register') ||
      url.includes('/api/auth/demo')
    ) {
      const account =
        'authUser' in overrides && overrides.authUser !== null
          ? overrides.authUser
          : fixtures.authUser;
      return json(account);
    }
    if (url.includes('/api/demo/status')) {
      return json(
        overrides.demoStatus ?? {
          enabled: false,
          profile: null,
          expenses: 0,
          check_ins: 0,
          events: 0,
          monthly_budget_paise: null,
          earliest: null,
          latest: null,
          is_empty: true,
        },
      );
    }
    if (url.includes('/api/profile/onboarding')) {
      return json({ ...(fixtures.profile as object), onboarding_completed: true, ...body });
    }

    // A create echoes the body back with server-owned fields; a delete answers
    // 204 with no content.
    if (method === 'DELETE') {
      return new Response(null, { status: 204 });
    }
    if (method === 'POST' || method === 'PATCH') {
      if (url.includes('/api/expenses')) {
        return json({ id: 'exp-new', amount_display: '', currency: 'INR', created_at: '', updated_at: '', ...body });
      }
      if (url.includes('/api/check-ins')) {
        return json({ created_at: '', updated_at: '', ...body }, 201);
      }
      if (url.includes('/api/life-events')) {
        return json({ id: 'evt-new', created_at: '', updated_at: '', ...body }, 201);
      }
      if (url.includes('/api/profile')) {
        return json({ ...fixtures.profile, ...body });
      }
    }

    const payload = url.includes('/api/chat/capabilities')
      ? fixtures.chatCapabilities
      : url.includes('/api/chat')
        ? fixtures.chatAnswer
        : url.includes('/api/narrations/status')
          ? (overrides.llmStatus ?? fixtures.llmStatusAvailable)
          : url.includes('/api/profile')
            ? (overrides.profile ?? fixtures.profile)
            : url.includes('/api/narrations')
              ? (overrides.narrations ?? fixtures.narratedAnalysis)
              : url.includes('/api/expenses')
                ? (overrides.expenses ?? fixtures.expensesList)
                : url.includes('/api/check-ins')
                  ? (overrides.checkIns ?? fixtures.checkInsList)
                  : url.includes('/api/life-events')
                    ? (overrides.lifeEvents ?? fixtures.lifeEventsList)
                    : (overrides.insights ?? fixtures.analysis);

    return json(payload);
  });

  vi.stubGlobal('fetch', fetchMock);
  return { calls, requests };
}

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

export interface ChatOverrides {
  answer?: unknown;
  capabilitiesFail?: boolean;
  networkError?: boolean;
  delayMs?: number;
}

export interface StubbedChat {
  /** Every question actually sent, in order. */
  questions: string[];
  /** Every request body, so a test can assert what was NOT sent. */
  bodies: Record<string, unknown>[];
  /** Stop failing, for retry tests. */
  recover: () => void;
}

export function stubChat(overrides: ChatOverrides = {}): StubbedChat {
  const questions: string[] = [];
  const bodies: Record<string, unknown>[] = [];
  let failing = overrides.networkError ?? false;

  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input.toString();

    if (url.includes('/api/chat/capabilities')) {
      if (overrides.capabilitiesFail) throw new TypeError('Failed to fetch');
      return new Response(JSON.stringify(fixtures.chatCapabilities), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const body = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : {};
    bodies.push(body);
    questions.push(String(body.question ?? ''));

    if (failing) throw new TypeError('Failed to fetch');
    if (overrides.delayMs) await new Promise((resolve) => setTimeout(resolve, overrides.delayMs));

    const answer = overrides.answer ?? fixtures.chatAnswer;
    return new Response(JSON.stringify({ ...(answer as object), question: body.question }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    });
  });

  vi.stubGlobal('fetch', fetchMock);
  return {
    questions,
    bodies,
    recover: () => {
      failing = false;
    },
  };
}
