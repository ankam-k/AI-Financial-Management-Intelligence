/**
 * The dashboard's data.
 *
 * Two requests, in parallel: `/api/insights` carries the metrics the charts
 * read, `/api/narrations` carries the prose. They are separate calls because
 * they are separate concerns on the backend — and joining them is free,
 * because insight ids are content-addressed, so the same window produces the
 * same ids in both responses.
 */

import { useCallback, useMemo } from 'react';
import { getInsights, getNarrations, getProfile } from '../api/endpoints';
import type { AnalysisResult, NarratedAnalysis, Narration, Profile } from '../api/types';
import { useAsync } from './useAsync';

export interface DashboardData {
  profile: Profile;
  analysis: AnalysisResult;
  narration: NarratedAnalysis;
  /** Narration for an insight id, or `undefined` if it was not narrated. */
  narrationFor: (insightId: string) => Narration | undefined;
}

export function useDashboardData(days: number, generate: boolean) {
  const run = useCallback(
    async (signal: AbortSignal) => {
      const [profile, analysis, narration] = await Promise.all([
        getProfile(signal),
        getInsights({ days }, signal),
        getNarrations({ days, generate }, signal),
      ]);
      return { profile, analysis, narration };
    },
    [days, generate],
  );

  const state = useAsync(run, [days, generate]);

  const data = useMemo<DashboardData | null>(() => {
    if (!state.data) return null;
    const index = new Map(state.data.narration.narrations.map((item) => [item.insight_id, item]));
    return {
      ...state.data,
      narrationFor: (insightId: string) => index.get(insightId),
    };
  }, [state.data]);

  return { ...state, data };
}
