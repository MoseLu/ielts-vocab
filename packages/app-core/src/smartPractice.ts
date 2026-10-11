import type { LearningStatsPayload, MobileWord, PracticeMode } from './mobileSchemas'

export type SmartPracticeDimension = 'listening' | 'meaning' | 'dictation'

export type SmartDimensionStats = {
  correct: number
  wrong: number
}

export type SmartWordStats = Record<SmartPracticeDimension, SmartDimensionStats>

export type SmartWordStatsStore = Record<string, SmartWordStats>

export type SmartPracticeContext = {
  learnerProfile?: Record<string, unknown> | null
  learningStats?: LearningStatsPayload | Record<string, unknown> | null
}

export type SmartStatsSyncEntry = {
  word: string
  listening: SmartDimensionStats
  meaning: SmartDimensionStats
  dictation: SmartDimensionStats
}

export const SMART_PRACTICE_DIMENSION_LABELS: Record<SmartPracticeDimension, string> = {
  listening: '听音选义',
  meaning: '看义拼词',
  dictation: '听音拼写',
}

const SMART_DIMENSIONS: SmartPracticeDimension[] = ['listening', 'meaning', 'dictation']

function normalizeSmartAnswer(value: string | null | undefined): string {
  return String(value ?? '')
    .replace(/<script[\s\S]*?<\/script>/gi, '')
    .replace(/<style[\s\S]*?<\/style>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .replace(/[’']/g, '')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
}

function smartWordKey(word: Pick<MobileWord, 'word'>): string {
  return normalizeSmartAnswer(word.word)
}

function emptySmartWordStats(): SmartWordStats {
  return {
    listening: { correct: 0, wrong: 0 },
    meaning: { correct: 0, wrong: 0 },
    dictation: { correct: 0, wrong: 0 },
  }
}

function normalizeSmartDimension(value: unknown): SmartPracticeDimension | null {
  const normalized = normalizeSmartAnswer(String(value ?? ''))
  if (normalized === 'listening') return 'listening'
  if (normalized === 'meaning') return 'meaning'
  if (normalized === 'dictation' || normalized === 'writing' || normalized === 'spelling') return 'dictation'
  return null
}

function dimMastery(dim: SmartDimensionStats): number {
  const total = dim.correct + dim.wrong
  return total === 0 ? -1 : dim.correct / total
}

function readObject(value: unknown): Record<string, unknown> | null {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : null
}

function preferredDimensionFromContext(context?: SmartPracticeContext): SmartPracticeDimension | null {
  const profile = readObject(context?.learnerProfile)
  const profileSummary = readObject(profile?.summary)
  const profileWeakest = normalizeSmartDimension(profileSummary?.weakest_mode)
  if (profileWeakest) return profileWeakest
  const dimensions = Array.isArray(profile?.dimensions) ? profile.dimensions : []
  for (const item of dimensions) {
    const dimension = normalizeSmartDimension(readObject(item)?.dimension)
    if (dimension) return dimension
  }

  const learningStats = readObject(context?.learningStats)
  const alltime = readObject(learningStats?.alltime)
  return normalizeSmartDimension(alltime?.weakest_mode)
}

export function normalizeSmartStatsPayload(values: unknown): SmartWordStatsStore {
  const result: SmartWordStatsStore = {}
  if (!Array.isArray(values)) return result
  for (const item of values) {
    const row = readObject(item)
    const key = normalizeSmartAnswer(String(row?.word ?? ''))
    if (!key) continue
    const stats = emptySmartWordStats()
    for (const dimension of SMART_DIMENSIONS) {
      const source = readObject(row?.[dimension])
      stats[dimension] = {
        correct: Math.max(0, Math.trunc(Number(source?.correct ?? 0))),
        wrong: Math.max(0, Math.trunc(Number(source?.wrong ?? 0))),
      }
    }
    result[key] = stats
  }
  return result
}

export function chooseSmartPracticeDimension(
  word: Pick<MobileWord, 'word'> | string,
  stats: SmartWordStatsStore,
  context?: SmartPracticeContext,
  random = Math.random,
): SmartPracticeDimension {
  const key = typeof word === 'string' ? normalizeSmartAnswer(word) : smartWordKey(word)
  const wordStats = key ? stats[key] : undefined
  const preferred = preferredDimensionFromContext(context)
  if (!wordStats) return preferred ?? 'meaning'

  const weights = SMART_DIMENSIONS.map(dimension => {
    const mastery = dimMastery(wordStats[dimension])
    const base = mastery === -1 ? 0.6 : Math.max(0.05, 1 - mastery)
    return dimension === preferred ? base + 0.25 : base
  })
  const total = weights.reduce((sum, value) => sum + value, 0)
  let pick = random() * total
  for (let index = 0; index < SMART_DIMENSIONS.length; index += 1) {
    pick -= weights[index]
    if (pick <= 0) return SMART_DIMENSIONS[index]
  }
  return preferred ?? 'meaning'
}

export function resolveSmartPracticeMode(dimension: SmartPracticeDimension): Extract<PracticeMode, 'listening' | 'meaning' | 'dictation'> {
  return dimension
}

export function recordSmartPracticeResult(
  stats: SmartWordStatsStore,
  word: Pick<MobileWord, 'word'> | string,
  dimension: SmartPracticeDimension,
  correct: boolean,
): SmartWordStatsStore {
  const key = typeof word === 'string' ? normalizeSmartAnswer(word) : smartWordKey(word)
  if (!key) return stats
  const current = stats[key] ?? emptySmartWordStats()
  return {
    ...stats,
    [key]: {
      listening: { ...current.listening },
      meaning: { ...current.meaning },
      dictation: { ...current.dictation },
      [dimension]: {
        correct: current[dimension].correct + (correct ? 1 : 0),
        wrong: current[dimension].wrong + (correct ? 0 : 1),
      },
    },
  }
}
