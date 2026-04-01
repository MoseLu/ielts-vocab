import type { SmartDimension } from '../../lib/smartMode'
import type { WrongWordRecord } from './wrongWordsStore'

export type WrongWordDimensionFilter = 'all' | SmartDimension

export interface WrongWordFilters {
  dimFilter?: WrongWordDimensionFilter
  minWrongCount?: number
  startDate?: string
  endDate?: string
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
  return value === 'listening' || value === 'meaning' || value === 'dictation' ? value : 'all'
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
  const dimFilter = normalizeDimensionFilter(filters.dimFilter)
  const minWrongCount = normalizeMinWrongCount(filters.minWrongCount)
  const startTimestamp = buildBoundaryTimestamp(filters.startDate, false)
  const endTimestamp = buildBoundaryTimestamp(filters.endDate, true)

  return words.filter(word => {
    const rawWord = word as Partial<WrongWordRecord> & Record<string, unknown>
    const totalWrongCount = typeof word.wrong_count === 'number' ? word.wrong_count : 0
    if (totalWrongCount < minWrongCount) return false

    if (dimFilter !== 'all') {
      const dimWrongCount = rawWord[`${dimFilter}_wrong`] as number | undefined
      if ((dimWrongCount ?? 0) <= 0) return false
    }

    if (startTimestamp != null || endTimestamp != null) {
      const occurrenceAt = getWrongWordOccurrenceAt(word)
      if (!occurrenceAt) return false

      const occurrenceTimestamp = Date.parse(occurrenceAt)
      if (Number.isNaN(occurrenceTimestamp)) return false
      if (startTimestamp != null && occurrenceTimestamp < startTimestamp) return false
      if (endTimestamp != null && occurrenceTimestamp > endTimestamp) return false
    }

    return true
  })
}

export function buildWrongWordsPracticeQuery(filters: WrongWordFilters): string {
  const params = new URLSearchParams()
  const startDate = normalizeDateInput(filters.startDate)
  const endDate = normalizeDateInput(filters.endDate)
  const minWrongCount = normalizeMinWrongCount(filters.minWrongCount)
  const dimFilter = normalizeDimensionFilter(filters.dimFilter)

  if (startDate) params.set('startDate', startDate)
  if (endDate) params.set('endDate', endDate)
  if (minWrongCount > 0) params.set('minWrong', String(minWrongCount))
  if (dimFilter !== 'all') params.set('dim', dimFilter)

  return params.toString()
}

export function parseWrongWordsFiltersFromSearchParams(searchParams: URLSearchParams): WrongWordFilters {
  const minWrongRaw = searchParams.get('minWrong')
  const minWrongCount = minWrongRaw ? Number.parseInt(minWrongRaw, 10) : 0
  const dimFilter = searchParams.get('dim')

  return {
    dimFilter: normalizeDimensionFilter(dimFilter as WrongWordDimensionFilter | undefined),
    startDate: searchParams.get('startDate') ?? undefined,
    endDate: searchParams.get('endDate') ?? undefined,
    minWrongCount: Number.isFinite(minWrongCount) ? minWrongCount : 0,
  }
}
