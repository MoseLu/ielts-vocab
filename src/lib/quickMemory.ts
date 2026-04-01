import { STORAGE_KEYS } from '../constants'

export interface QuickMemoryRecordState {
  status: 'known' | 'unknown'
  firstSeen: number
  lastSeen: number
  knownCount: number
  unknownCount: number
  nextReview: number
  fuzzyCount: number
  bookId?: string
  chapterId?: string
}

export type QuickMemoryRecordMap = Record<string, QuickMemoryRecordState>

export type QuickMemoryRecordInput = Partial<QuickMemoryRecordState> & {
  word?: string | null
}

const DAY_MS = 86_400_000

export const QUICK_MEMORY_REVIEW_INTERVALS_DAYS = [1, 1, 4, 7, 14, 30] as const
export const QUICK_MEMORY_MASTERY_TARGET = QUICK_MEMORY_REVIEW_INTERVALS_DAYS.length

function normalizeWordKey(word: string): string {
  return word.trim().toLowerCase()
}

function asNonNegativeNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, value) : fallback
}

function normalizeQuickMemoryRecord(value: unknown): QuickMemoryRecordState | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null

  const raw = value as Record<string, unknown>

  return {
    status: raw.status === 'known' ? 'known' : 'unknown',
    firstSeen: asNonNegativeNumber(raw.firstSeen),
    lastSeen: asNonNegativeNumber(raw.lastSeen),
    knownCount: asNonNegativeNumber(raw.knownCount),
    unknownCount: asNonNegativeNumber(raw.unknownCount),
    nextReview: asNonNegativeNumber(raw.nextReview),
    fuzzyCount: asNonNegativeNumber(raw.fuzzyCount),
    bookId: typeof raw.bookId === 'string' && raw.bookId.trim() ? raw.bookId.trim() : undefined,
    chapterId: typeof raw.chapterId === 'string' && raw.chapterId.trim() ? raw.chapterId.trim() : undefined,
  }
}

export function nextQuickMemoryReviewTimestamp(knownCount: number, now = Date.now()): number {
  const safeKnownCount = Math.max(0, Math.floor(knownCount))
  if (safeKnownCount >= QUICK_MEMORY_MASTERY_TARGET) {
    return 0
  }

  const days = QUICK_MEMORY_REVIEW_INTERVALS_DAYS[
    Math.min(safeKnownCount, QUICK_MEMORY_REVIEW_INTERVALS_DAYS.length - 1)
  ]
  return now + days * DAY_MS
}

export function readQuickMemoryRecordsFromStorage(): QuickMemoryRecordMap {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS) || '{}')
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}

    const normalized: QuickMemoryRecordMap = {}
    for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
      const normalizedKey = normalizeWordKey(key)
      const normalizedValue = normalizeQuickMemoryRecord(value)
      if (!normalizedKey || !normalizedValue) continue
      normalized[normalizedKey] = normalizedValue
    }

    return normalized
  } catch {
    return {}
  }
}

export function writeQuickMemoryRecordsToStorage(records: QuickMemoryRecordMap): QuickMemoryRecordMap {
  localStorage.setItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS, JSON.stringify(records))
  return records
}

export function mergeQuickMemoryRecordsByLastSeen(
  base: QuickMemoryRecordMap,
  incoming: QuickMemoryRecordInput[],
): QuickMemoryRecordMap {
  const merged: QuickMemoryRecordMap = { ...base }

  for (const item of incoming) {
    const key = normalizeWordKey(typeof item.word === 'string' ? item.word : '')
    if (!key) continue

    const normalized = normalizeQuickMemoryRecord(item)
    if (!normalized) continue

    const existing = merged[key]
    if (!existing || normalized.lastSeen >= existing.lastSeen) {
      merged[key] = normalized
    }
  }

  return merged
}

export function updateQuickMemoryRecord(
  records: QuickMemoryRecordMap,
  word: string,
  choice: 'known' | 'unknown',
  isFuzzy: boolean,
  nowOrContext: number | { bookId?: string; chapterId?: string } = Date.now(),
  maybeContext?: { bookId?: string; chapterId?: string },
): {
  records: QuickMemoryRecordMap
  record: QuickMemoryRecordState | null
} {
  const now = typeof nowOrContext === 'number' ? nowOrContext : Date.now()
  const context = typeof nowOrContext === 'number' ? maybeContext : nowOrContext
  const key = normalizeWordKey(word)
  if (!key) {
    return { records, record: null }
  }

  const existing = records[key]
  const knownCount = choice === 'known'
    ? (existing?.knownCount ?? 0) + 1
    : 0
  const unknownCount = (existing?.unknownCount ?? 0) + (choice === 'unknown' ? 1 : 0)
  const fuzzyCount = (existing?.fuzzyCount ?? 0) + (isFuzzy ? 1 : 0)

  const record: QuickMemoryRecordState = {
    status: choice,
    firstSeen: existing?.firstSeen ?? now,
    lastSeen: now,
    knownCount,
    unknownCount,
    fuzzyCount,
    nextReview: nextQuickMemoryReviewTimestamp(knownCount, now),
    bookId: context?.bookId ?? existing?.bookId,
    chapterId: context?.chapterId ?? existing?.chapterId,
  }

  return {
    records: {
      ...records,
      [key]: record,
    },
    record,
  }
}

export function resetQuickMemoryRecord(
  records: QuickMemoryRecordMap,
  word: string,
  now = Date.now(),
): {
  records: QuickMemoryRecordMap
  record: QuickMemoryRecordState | null
} {
  const key = normalizeWordKey(word)
  if (!key) {
    return { records, record: null }
  }

  const existing = records[key]
  const record: QuickMemoryRecordState = {
    status: 'unknown',
    firstSeen: existing?.firstSeen ?? now,
    lastSeen: now,
    knownCount: 0,
    unknownCount: existing?.unknownCount ?? 0,
    fuzzyCount: existing?.fuzzyCount ?? 0,
    nextReview: nextQuickMemoryReviewTimestamp(0, now),
    bookId: existing?.bookId,
    chapterId: existing?.chapterId,
  }

  return {
    records: {
      ...records,
      [key]: record,
    },
    record,
  }
}

export function getQuickMemoryReviewProgress(
  record?: QuickMemoryRecordState | null,
  target = QUICK_MEMORY_MASTERY_TARGET,
): {
  streak: number
  target: number
  remaining: number
  completed: boolean
} {
  const streak = Math.min(asNonNegativeNumber(record?.knownCount), target)

  return {
    streak,
    target,
    remaining: Math.max(0, target - streak),
    completed: streak >= target,
  }
}

export function isQuickMemoryRecordMastered(
  record?: QuickMemoryRecordState | null,
  target = QUICK_MEMORY_MASTERY_TARGET,
): boolean {
  return asNonNegativeNumber(record?.knownCount) >= target
}
