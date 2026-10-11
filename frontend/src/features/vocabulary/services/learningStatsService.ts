// Learning stats HTTP service.
//
// Why this file exists:
// - `useLearningStats` previously inlined two `apiFetch` calls and one
//   `.catch(() => null)` normalization. Endpoint strings, query parameter
//   shapes, and the learner-profile fallback policy are domain knowledge
//   that belongs in a service module, not a hook.
// - The service is the single point that the Stats / Home / Profile pages
//   should call when they need raw stats payloads.

import { apiFetch } from '../../../lib'
import type { LearnerProfile, LearningStatsResponse, RangeKey } from '../hooks/useLearningStats'

export interface LearningStatsQuery {
  days: RangeKey
  bookId?: string
  mode?: string
}

export function getLearningStats({
  days,
  bookId,
  mode,
}: LearningStatsQuery): Promise<LearningStatsResponse> {
  const params = new URLSearchParams({ days: String(days) })
  if (bookId && bookId !== 'all') params.set('book_id', bookId)
  if (mode && mode !== 'all') params.set('mode', mode)

  return apiFetch<LearningStatsResponse>(
    `/api/ai/learning-stats?${params}`,
    { cache: 'no-store' },
  )
}

export function getLearnerProfile(): Promise<LearnerProfile | null> {
  return apiFetch<LearnerProfile>(
    '/api/ai/learner-profile?view=stats',
    { cache: 'no-store' },
  ).catch(() => null)
}
