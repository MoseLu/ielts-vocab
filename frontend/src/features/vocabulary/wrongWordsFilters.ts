import type {
  WrongWordCollectionScope,
  WrongWordDimension,
  WrongWordRecord,
} from './wrongWordsStore'
import {
  getWrongWordActiveCount,
  getWrongWordDimensionHistoryWrong,
  isWrongWordPendingInDimension,
} from './wrongWordsStore'

export type WrongWordDimensionFilter = 'all' | WrongWordDimension

export interface WrongWordFilters {
  scope?: WrongWordCollectionScope
  dimFilter?: WrongWordDimensionFilter
  minWrongCount?: number
  maxWrongCount?: number
  startDate?: string
  endDate?: string
}

export function normalizeWrongWordSearchTerm(value?: string): string {
  if (typeof value !== 'string') return ''
  return value.trim().toLowerCase()
}

function normalizeDateInput(value?: string): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  return /^\d{4}-\d{2}-\d{2}$/.test(trimmed) ? trimmed : undefined
}

function normalizeMinWrongCount(value?: number): number {
  if (typeof value !== 'number' || !Number.isFinite(value)) return 0
  return Math.max(0, Math.floor(value))
}

function normalizeMaxWrongCount(value?: number): number | null {
  if (typeof value !== 'number' || !Number.isFinite(value)) return null
  return Math.max(0, Math.floor(value))
}

function buildBoundaryTimestamp(value: string | undefined, endOfDay: boolean): number | null {
  const normalized = normalizeDateInput(value)
  if (!normalized) return null

  const [year, month, day] = normalized.split('-').map(Number)
  const boundary = endOfDay
    ? new Date(year, month - 1, day, 23, 59, 59, 999)
    : new Date(year, month - 1, day, 0, 0, 0, 0)
  const timestamp = boundary.getTime()

  return Number.isNaN(timestamp) ? null : timestamp
}

function normalizeDimensionFilter(value?: WrongWordDimensionFilter): WrongWordDimensionFilter {
  return value === 'recognition' || value === 'listening' || value === 'meaning' || value === 'dictation'
    ? value
    : 'all'
}

function normalizeScope(value?: WrongWordCollectionScope): WrongWordCollectionScope {
  return value === 'history' ? 'history' : 'pending'
}

export function matchesWrongWordSearchTerm<T extends Partial<WrongWordRecord>>(
  word: T,
  searchTerm?: string,
): boolean {
  const normalizedSearch = normalizeWrongWordSearchTerm(searchTerm)
  if (!normalizedSearch) return true

  return typeof word.word === 'string' && word.word.toLowerCase().includes(normalizedSearch)
}

export function getWrongWordOccurrenceAt(word: Partial<WrongWordRecord>): string | null {
  const rawWord = word as Partial<WrongWordRecord> & Record<string, unknown>
  const candidates = [
    rawWord.first_wrong_at,
    rawWord.firstWrongAt,
    rawWord.created_at,
    rawWord.createdAt,
    rawWord.added_at,
    rawWord.addedAt,
    rawWord.updated_at,
    rawWord.updatedAt,
  ]

  for (const candidate of candidates) {
    if (typeof candidate !== 'string' || !candidate.trim()) continue
    const timestamp = Date.parse(candidate)
    if (!Number.isNaN(timestamp)) {
      return new Date(timestamp).toISOString()
    }
  }

  return null
}

export function formatWrongWordOccurrenceDate(word: Partial<WrongWordRecord>): string | null {
  const occurrenceAt = getWrongWordOccurrenceAt(word)
  if (!occurrenceAt) return null

  const date = new Date(occurrenceAt)
  if (Number.isNaN(date.getTime())) return null

  const year = date.getFullYear()
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function filterWrongWords<T extends Partial<WrongWordRecord>>(
  words: T[],
  filters: WrongWordFilters,
): T[] {
  const scope = normalizeScope(filters.scope)
  const dimFilter = normalizeDimensionFilter(filters.dimFilter)
  const minWrongCount = normalizeMinWrongCount(filters.minWrongCount)
  const maxWrongCount = normalizeMaxWrongCount(filters.maxWrongCount)
  const startTimestamp = buildBoundaryTimestamp(filters.startDate, false)
  const endTimestamp = buildBoundaryTimestamp(filters.endDate, true)

  return words.filter(word => {
    const activeWrongCount = getWrongWordActiveCount(word, scope)
    if (activeWrongCount < minWrongCount) return false
    if (maxWrongCount != null && activeWrongCount > maxWrongCount) return false

    if (dimFilter !== 'all') {
      if (scope === 'history') {
        if (getWrongWordDimensionHistoryWrong(word, dimFilter) <= 0) return false
      } else if (!isWrongWordPendingInDimension(word, dimFilter)) {
        return false
      }
    }

    if (startTimestamp != null || endTimestamp != null) {
      const occurrenceAt = getWrongWordOccurrenceAt(word)
      if (!occurrenceAt) return false

      const occurrenceTimestamp = Date.parse(occurrenceAt)
      if (Number.isNaN(occurrenceTimestamp)) return false
      if (startTimestamp != null && occurrenceTimestamp < startTimestamp) return false
      if (endTimestamp != null && occurrenceTimestamp > endTimestamp) return false
    }

    return activeWrongCount > 0
  })
}

export function buildWrongWordsPracticeQuery(filters: WrongWordFilters): string {
  const params = new URLSearchParams()
  const scope = normalizeScope(filters.scope)
  const startDate = normalizeDateInput(filters.startDate)
  const endDate = normalizeDateInput(filters.endDate)
  const minWrongCount = normalizeMinWrongCount(filters.minWrongCount)
  const maxWrongCount = normalizeMaxWrongCount(filters.maxWrongCount)
  const dimFilter = normalizeDimensionFilter(filters.dimFilter)

  params.set('scope', scope)
  if (startDate) params.set('startDate', startDate)
  if (endDate) params.set('endDate', endDate)
  if (minWrongCount > 0) params.set('minWrong', String(minWrongCount))
  if (maxWrongCount != null) params.set('maxWrong', String(maxWrongCount))
  if (dimFilter !== 'all') params.set('dim', dimFilter)

  return params.toString()
}

export function parseWrongWordsFiltersFromSearchParams(searchParams: URLSearchParams): WrongWordFilters {
  const minWrongRaw = searchParams.get('minWrong')
  const maxWrongRaw = searchParams.get('maxWrong')
  const minWrongCount = minWrongRaw ? Number.parseInt(minWrongRaw, 10) : 0
  const maxWrongCount = maxWrongRaw ? Number.parseInt(maxWrongRaw, 10) : Number.NaN
  const dimFilter = searchParams.get('dim')
  const scope = searchParams.get('scope')

  return {
    scope: normalizeScope(scope as WrongWordCollectionScope | undefined),
    dimFilter: normalizeDimensionFilter(dimFilter as WrongWordDimensionFilter | undefined),
    startDate: searchParams.get('startDate') ?? undefined,
    endDate: searchParams.get('endDate') ?? undefined,
    minWrongCount: Number.isFinite(minWrongCount) ? minWrongCount : 0,
    maxWrongCount: Number.isFinite(maxWrongCount) ? maxWrongCount : undefined,
  }
}
