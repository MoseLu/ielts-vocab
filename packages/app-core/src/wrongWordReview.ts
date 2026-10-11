import type { MobileWord, PracticeMode, WrongWord } from './mobileSchemas'
import { normalizeAnswer } from './practiceEngine'

export const MOBILE_WRONG_WORD_DIMENSIONS = [
  'recognition',
  'meaning',
  'listening',
  'dictation',
  'speaking',
] as const

export type MobileWrongWordDimension = typeof MOBILE_WRONG_WORD_DIMENSIONS[number]
export type MobileWrongWordDimensionFilter = 'all' | MobileWrongWordDimension
export type MobileWrongWordScope = 'pending' | 'history'
export type MobileWrongWordFilters = {
  dimension?: MobileWrongWordDimensionFilter
  maxWrongCount?: number
  minWrongCount?: number
  mode?: PracticeMode | 'all'
  scope?: MobileWrongWordScope
}

export type ErrorReviewRoundResults = Record<string, boolean>
export type MobileErrorReviewProgress = {
  correctCount: number
  currentIndex: number
  filters: MobileWrongWordFilters
  isCompleted: boolean
  mode: PracticeMode
  queueWords: string[]
  results: ErrorReviewRoundResults
  round: number
  updatedAt: string
  wrongCount: number
}

export function normalizeErrorReviewWordKey(value: string | null | undefined): string {
  return normalizeAnswer(value)
}

export function wrongWordDimensionForMode(mode?: PracticeMode | 'all'): MobileWrongWordDimensionFilter {
  if (mode === 'quickmemory' || mode === 'test') return 'recognition'
  if (mode === 'meaning') return 'meaning'
  if (mode === 'listening') return 'listening'
  if (mode === 'dictation') return 'dictation'
  if (mode === 'follow') return 'speaking'
  return 'all'
}

function normalizeWrongWordDimension(value?: string | null): MobileWrongWordDimension | null {
  return MOBILE_WRONG_WORD_DIMENSIONS.includes(value as MobileWrongWordDimension)
    ? value as MobileWrongWordDimension
    : null
}

function normalizedWrongWordDimensions(word: WrongWord): Set<MobileWrongWordDimension> {
  const raw = word as WrongWord & Record<string, unknown>
  const dimensions = new Set<MobileWrongWordDimension>()
  const add = (value: unknown) => {
    if (typeof value !== 'string') return
    const dimension = normalizeWrongWordDimension(value)
    if (dimension) dimensions.add(dimension)
  }

  add(raw.mistake_type)
  add(raw.dimension)
  if (Array.isArray(raw.pending_dimensions)) raw.pending_dimensions.forEach(add)
  if (raw.dimension_states && typeof raw.dimension_states === 'object') {
    Object.entries(raw.dimension_states as Record<string, Record<string, unknown>>).forEach(([key, state]) => {
      if (state?.pending === false && Number(state.history_wrong ?? 0) <= 0) return
      add(key)
    })
  }
  return dimensions
}

function wrongWordCountForFilter(word: WrongWord, dimension: MobileWrongWordDimensionFilter): number {
  if (dimension === 'all') return Math.max(0, Math.trunc(word.wrong_count ?? 0))

  const state = (word.dimension_states as Record<string, Record<string, unknown>> | undefined)?.[dimension]
  const historyWrong = Number(state?.history_wrong ?? state?.wrong_count ?? Number.NaN)
  if (Number.isFinite(historyWrong)) return Math.max(0, Math.trunc(historyWrong))
  return normalizedWrongWordDimensions(word).has(dimension) ? Math.max(1, Math.trunc(word.wrong_count ?? 1)) : 0
}

export function filterMobileWrongWords(words: WrongWord[], filters: MobileWrongWordFilters = {}): WrongWord[] {
  const modeDimension = wrongWordDimensionForMode(filters.mode)
  const dimension = filters.dimension && filters.dimension !== 'all' ? filters.dimension : modeDimension
  const minWrongCount = Math.max(0, Math.trunc(filters.minWrongCount ?? 0))
  const maxWrongCount = filters.maxWrongCount == null ? null : Math.max(0, Math.trunc(filters.maxWrongCount))

  return words.filter(word => {
    const count = wrongWordCountForFilter(word, dimension)
    if (count < minWrongCount) return false
    if (maxWrongCount != null && count > maxWrongCount) return false
    return count > 0
  })
}

export function buildMobileWrongWordsReviewQueue(
  words: WrongWord[],
  filters: MobileWrongWordFilters = {},
  selectedWords: string[] = [],
): WrongWord[] {
  const entries = words
    .map(word => [normalizeErrorReviewWordKey(word.word), word] as const)
    .filter((entry): entry is readonly [string, WrongWord] => Boolean(entry[0]))
  const wordsByKey = new Map(entries)
  const selectedKeys = selectedWords.map(normalizeErrorReviewWordKey).filter(Boolean)
  if (selectedKeys.length > 0) return selectedKeys.flatMap(key => wordsByKey.get(key) ?? [])
  return filterMobileWrongWords(words, filters)
}

export function updateErrorReviewRoundResults(
  results: ErrorReviewRoundResults,
  word: string,
  wasCorrect: boolean,
): ErrorReviewRoundResults {
  const key = normalizeErrorReviewWordKey(word)
  if (!key) return results
  return { ...results, [key]: wasCorrect }
}

export function buildNextErrorReviewRoundWords<T extends Pick<MobileWord, 'word'>>(
  vocabulary: T[],
  results: ErrorReviewRoundResults,
): T[] {
  return vocabulary.filter(word => results[normalizeErrorReviewWordKey(word.word)] === false)
}

export function buildErrorReviewProgress(params: {
  correctCount: number
  currentIndex: number
  filters?: MobileWrongWordFilters
  mode: PracticeMode
  queue: MobileWord[]
  results: ErrorReviewRoundResults
  round?: number
  wrongCount: number
}): MobileErrorReviewProgress {
  return {
    correctCount: params.correctCount,
    currentIndex: params.currentIndex,
    filters: params.filters ?? {},
    isCompleted: params.currentIndex >= params.queue.length,
    mode: params.mode,
    queueWords: params.queue.map(word => word.word),
    results: params.results,
    round: params.round ?? 1,
    updatedAt: new Date().toISOString(),
    wrongCount: params.wrongCount,
  }
}

export function isErrorReviewProgressForQueue(
  progress: MobileErrorReviewProgress | null | undefined,
  queue: MobileWord[],
  mode: PracticeMode,
): progress is MobileErrorReviewProgress {
  if (!progress || progress.mode !== mode) return false
  const queueKeys = queue.map(word => normalizeErrorReviewWordKey(word.word))
  const progressKeys = progress.queueWords.map(normalizeErrorReviewWordKey)
  return queueKeys.length === progressKeys.length
    && queueKeys.every((key, index) => key === progressKeys[index])
}
