/** Every backend call the dashboard makes, in one place. */

import { apiDelete, apiGet, apiPatch, apiPost, apiPostNoContent } from './client';
import type {
  AnalysisResult,
  AuthUser,
  ChatCapabilities,
  ChatResponse,
  CheckInCreate,
  CheckInRead,
  DemoStatus,
  ExpenseCreate,
  ExpenseRead,
  LifeEventCreate,
  LifeEventRead,
  LLMStatus,
  NarratedAnalysis,
  Personalisation,
  Profile,
  ProfileUpdate,
} from './types';

export interface WindowParams {
  days?: number;
  start_date?: string;
  end_date?: string;
}

/* ── Authentication (V1.2) ────────────────────────────────────────────────
 *
 * The session is an HttpOnly cookie the browser cannot read, so these calls
 * carry no token — the cookie rides along automatically (`credentials:
 * 'include'` in the client). Each returns the account, or throws an `ApiError`
 * the auth layer turns into a screen state.
 */

export const register = (
  body: { email: string; password: string; display_name?: string },
  signal?: AbortSignal,
) => apiPost<AuthUser>('/api/auth/register', body, { signal });

export const login = (body: { email: string; password: string }, signal?: AbortSignal) =>
  apiPost<AuthUser>('/api/auth/login', body, { signal });

export const logout = (signal?: AbortSignal) =>
  apiPostNoContent('/api/auth/logout', { signal });

export const getMe = (signal?: AbortSignal) => apiGet<AuthUser>('/api/auth/me', {}, { signal });

/** Enter the shared, read-to-explore demo account (passwordless). */
export const enterDemo = (signal?: AbortSignal) =>
  apiPost<AuthUser>('/api/auth/demo', {}, { signal });

/** Record onboarding answers and mark the account onboarded. */
export const submitOnboarding = (body: Personalisation, signal?: AbortSignal) =>
  apiPost<Profile>('/api/profile/onboarding', body, { signal });

export const getProfile = (signal?: AbortSignal) =>
  apiGet<Profile>('/api/profile', {}, { signal });

export const getInsights = (params: WindowParams, signal?: AbortSignal) =>
  apiGet<AnalysisResult>('/api/insights', { ...params }, { signal });

/**
 * Narration for the same window.
 *
 * `generate=false` by default: a local 7B model takes roughly 18 seconds per
 * insight, so a dashboard that waited for it would look broken. Template prose
 * is served immediately and identical in substance; the user opts into
 * generation explicitly.
 */
export const getNarrations = (
  params: WindowParams & { generate?: boolean },
  signal?: AbortSignal,
) => apiGet<NarratedAnalysis>('/api/narrations', { generate: false, ...params }, { signal });

export const getLLMStatus = (signal?: AbortSignal) =>
  apiGet<LLMStatus>('/api/narrations/status', {}, { signal });

/**
 * Ask one question.
 *
 * Note the absence of a conversation id and of any history parameter. Each
 * question is answered independently from the analysis window; the transcript
 * on screen is a display artefact the server never sees (SRS-7.7).
 */
export const askChat = (
  body: { question: string; days?: number; generate?: boolean },
  signal?: AbortSignal,
) => apiPost<ChatResponse>('/api/chat', body, { signal });

export const getChatCapabilities = (signal?: AbortSignal) =>
  apiGet<ChatCapabilities>('/api/chat/capabilities', {}, { signal });

/** Destructive: replaces whatever is loaded with the demo dataset. */
export const seedDemo = (signal?: AbortSignal) =>
  apiPost<DemoStatus>('/api/demo/seed', {}, { signal });

/** Non-destructive: whether demo mode is on, and what the demo account holds. */
export const getDemoStatus = (signal?: AbortSignal) =>
  apiGet<DemoStatus>('/api/demo/status', {}, { signal });

/* ── Profile ──────────────────────────────────────────────────────────── */

export const updateProfile = (body: ProfileUpdate, signal?: AbortSignal) =>
  apiPatch<Profile>('/api/profile', body, { signal });

/** Destructive: wipes expenses, check-ins and events but keeps the profile. */
export const wipeData = (signal?: AbortSignal) => apiDelete('/api/profile/data', { signal });

/* ── Expenses ─────────────────────────────────────────────────────────── */

export interface ExpenseQuery {
  start_date?: string;
  end_date?: string;
  category?: string;
  limit?: number;
  offset?: number;
}

export const listExpenses = (query: ExpenseQuery = {}, signal?: AbortSignal) =>
  apiGet<ExpenseRead[]>('/api/expenses', { ...query }, { signal });

export const createExpense = (body: ExpenseCreate, signal?: AbortSignal) =>
  apiPost<ExpenseRead>('/api/expenses', body, { signal });

export const deleteExpense = (id: string, signal?: AbortSignal) =>
  apiDelete(`/api/expenses/${id}`, { signal });

/* ── Check-ins ────────────────────────────────────────────────────────── */

export const listCheckIns = (signal?: AbortSignal) =>
  apiGet<CheckInRead[]>('/api/check-ins', {}, { signal });

export const createCheckIn = (body: CheckInCreate, signal?: AbortSignal) =>
  apiPost<CheckInRead>('/api/check-ins', body, { signal });

/** Keyed by ISO log date, not an id — there is one check-in per day. */
export const updateCheckIn = (
  logDate: string,
  body: Omit<CheckInCreate, 'log_date'>,
  signal?: AbortSignal,
) => apiPatch<CheckInRead>(`/api/check-ins/${logDate}`, body, { signal });

export const deleteCheckIn = (logDate: string, signal?: AbortSignal) =>
  apiDelete(`/api/check-ins/${logDate}`, { signal });

/* ── Life events ──────────────────────────────────────────────────────── */

export const listLifeEvents = (signal?: AbortSignal) =>
  apiGet<LifeEventRead[]>('/api/life-events', {}, { signal });

export const createLifeEvent = (body: LifeEventCreate, signal?: AbortSignal) =>
  apiPost<LifeEventRead>('/api/life-events', body, { signal });

export const deleteLifeEvent = (id: string, signal?: AbortSignal) =>
  apiDelete(`/api/life-events/${id}`, { signal });
