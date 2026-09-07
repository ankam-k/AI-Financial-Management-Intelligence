/**
 * The HTTP boundary.
 *
 * One place that knows about fetch, status codes and the backend's error
 * envelope. Everything above it receives typed data or an `ApiError` and never
 * touches a Response object.
 */

/** The backend's domain-error envelope (`app/api/errors.py`). */
interface ErrorEnvelope {
  detail?: string;
  error?: string;
}

export class ApiError extends Error {
  readonly status: number;
  /** Machine name from the backend: `NotFoundError`, `ValidationError`, … */
  readonly kind: string;

  constructor(message: string, status: number, kind: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.kind = kind;
  }

  /** True when retrying the same request could plausibly succeed. */
  get isRetryable(): boolean {
    return this.status === 0 || this.status >= 500;
  }
}

const BASE = import.meta.env.VITE_API_BASE ?? '';

/**
 * A single place to react to "the session is gone" (HTTP 401).
 *
 * The auth layer registers a handler here; when any request comes back 401 —
 * an expired token, a cleared cookie, a deleted account — the app resets to the
 * login screen instead of leaving a half-authenticated view showing stale data.
 * It is a module-level seam, not a context, so the low-level client can signal
 * it without importing React.
 */
type UnauthorizedHandler = () => void;
let unauthorizedHandler: UnauthorizedHandler | null = null;

export function setUnauthorizedHandler(handler: UnauthorizedHandler | null): void {
  unauthorizedHandler = handler;
}

function notifyUnauthorized(): void {
  if (unauthorizedHandler) unauthorizedHandler();
}

function toQuery(params: Record<string, string | number | boolean | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined) search.set(key, String(value));
  }
  const query = search.toString();
  return query ? `?${query}` : '';
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${BASE}${path}`, {
      headers: { Accept: 'application/json' },
      // Send the HttpOnly session cookie with every request. Same-origin behind
      // the nginx proxy in production and the Vite proxy in dev, but explicit so
      // the app never depends on the default varying by deployment.
      credentials: 'include',
      ...init,
    });
  } catch (cause) {
    // A network-level failure has no status. Status 0 marks it as retryable
    // and distinguishes "the server never answered" from "the server said no".
    throw new ApiError(
      'Could not reach the API. Is the backend running on port 8000?',
      0,
      'NetworkError',
    );
  }

  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    let envelope: ErrorEnvelope = {};
    try {
      envelope = (await response.json()) as ErrorEnvelope;
    } catch {
      /* A non-JSON error body is still an error; fall through to the default. */
    }
    throw new ApiError(
      envelope.detail ?? `Request failed with status ${response.status}`,
      response.status,
      envelope.error ?? 'HttpError',
    );
  }

  return (await response.json()) as T;
}

export function apiGet<T>(
  path: string,
  params: Record<string, string | number | boolean | undefined> = {},
  init: RequestInit = {},
): Promise<T> {
  return request<T>(`${path}${toQuery(params)}`, init);
}

export function apiPost<T>(path: string, body: unknown, init: RequestInit = {}): Promise<T> {
  // `init` first, so a caller's `signal` survives but cannot replace the
  // method or the body this function exists to set.
  return request<T>(path, {
    ...init,
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/**
 * A POST whose response carries no body — e.g. logout answers 204. Mirrors
 * `apiPost` but never tries to parse an empty body as JSON.
 */
export async function apiPostNoContent(path: string, init: RequestInit = {}): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { credentials: 'include', ...init, method: 'POST' });
  } catch {
    throw new ApiError(
      'Could not reach the API. Is the backend running on port 8000?',
      0,
      'NetworkError',
    );
  }
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    let envelope: ErrorEnvelope = {};
    try {
      envelope = (await response.json()) as ErrorEnvelope;
    } catch {
      /* A non-JSON error body is still an error. */
    }
    throw new ApiError(
      envelope.detail ?? `Request failed with status ${response.status}`,
      response.status,
      envelope.error ?? 'HttpError',
    );
  }
  // 204 No Content: nothing to read.
}

/** A partial update. Mirrors `apiPost`, differing only in the verb. */
export function apiPatch<T>(path: string, body: unknown, init: RequestInit = {}): Promise<T> {
  return request<T>(path, {
    ...init,
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/**
 * A delete. The backend answers 204 with no body, so this resolves to `void`
 * rather than trying to parse an empty response as JSON.
 */
export async function apiDelete(path: string, init: RequestInit = {}): Promise<void> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, { credentials: 'include', ...init, method: 'DELETE' });
  } catch {
    throw new ApiError(
      'Could not reach the API. Is the backend running on port 8000?',
      0,
      'NetworkError',
    );
  }
  if (!response.ok) {
    if (response.status === 401) notifyUnauthorized();
    let envelope: ErrorEnvelope = {};
    try {
      envelope = (await response.json()) as ErrorEnvelope;
    } catch {
      /* A non-JSON error body is still an error. */
    }
    throw new ApiError(
      envelope.detail ?? `Request failed with status ${response.status}`,
      response.status,
      envelope.error ?? 'HttpError',
    );
  }
  // 204 No Content: nothing to read.
}
