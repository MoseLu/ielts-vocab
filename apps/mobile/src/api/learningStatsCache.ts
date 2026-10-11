import type { LearningStatsPayload } from '@ielts-vocab/app-core'

const CACHE_TTL_MS = 30_000

let cached: LearningStatsPayload | null = null
let cachedAt = 0
let inFlight: Promise<LearningStatsPayload> | null = null

export function peekLearningStats(): LearningStatsPayload | null {
  return cached
}

export function resetLearningStatsCacheForTests() {
  cached = null
  cachedAt = 0
  inFlight = null
}

export async function loadLearningStatsCached(
  fetcher: () => Promise<LearningStatsPayload>,
): Promise<LearningStatsPayload> {
  if (cached && Date.now() - cachedAt < CACHE_TTL_MS) {
    return cached
  }
  if (inFlight) return inFlight

  inFlight = fetcher()
    .then(payload => {
      cached = payload
      cachedAt = Date.now()
      return payload
    })
    .finally(() => {
      inFlight = null
    })

  return inFlight
}
