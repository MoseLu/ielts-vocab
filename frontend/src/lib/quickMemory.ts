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

type QuickMemoryStorageUserId = string | number | null | undefined

export const QUICK_MEMORY_REVIEW_INTERVALS_DAYS = [1, 1, 4, 7, 14, 30] as const
export const QUICK_MEMORY_MASTERY_TARGET = QUICK_MEMORY_REVIEW_INTERVALS_DAYS.length

function normalizeWordKey(word: string): string {
  return word.trim().toLowerCase()
}

function startOfLocalDayTimestamp(timestamp: number): number {
  const localDate = new Date(timestamp)
  localDate.setHours(0, 0, 0, 0)
  return localDate.getTime()
}

function localDateKey(timestamp: number): string {
  return new Date(timestamp).toDateString()
}

function asNonNegativeNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? Math.max(0, value) : fallback
}

function normalizeStorageUserId(value: QuickMemoryStorageUserId): string | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return String(value)
  }

  if (typeof value === 'string') {
    const normalized = value.trim()
    return normalized || null
  }

  return null
}

function readStoredAuthUserId(): string | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (!raw) return null

    const parsed = JSON.parse(raw) as { id?: unknown } | null
    if (!parsed || typeof parsed !== 'object') return null

    return normalizeStorageUserId(parsed.id as QuickMemoryStorageUserId)
  } catch {
    return null
  }
}

export function getQuickMemoryStorageKey(userId?: QuickMemoryStorageUserId): string {
  const resolvedUserId = normalizeStorageUserId(userId) ?? readStoredAuthUserId()
  return resolvedUserId
    ? `${STORAGE_KEYS.QUICK_MEMORY_RECORDS}:${resolvedUserId}`
    : STORAGE_KEYS.QUICK_MEMORY_RECORDS
}

function normalizeQuickMemoryRecord(value: unknown): QuickMemoryRecordState | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null

  const raw = value as Record<string, unknown>
  const firstSeen = asNonNegativeNumber(raw.firstSeen)
  const lastSeen = asNonNegativeNumber(raw.lastSeen)
  const knownCount = asNonNegativeNumber(raw.knownCount)
  const unknownCount = asNonNegativeNumber(raw.unknownCount)
  const storedNextReview = asNonNegativeNumber(raw.nextReview)
  const expectedNextReview = lastSeen > 0
    ? nextQuickMemoryReviewTimestamp(knownCount, lastSeen)
    : storedNextReview
  const nextReview = lastSeen > 0 && (
    storedNextReview <= 0
    || localDateKey(storedNextReview) === localDateKey(expectedNextReview)
  )
    ? expectedNextReview
    : storedNextReview

  return {
    status: raw.status === 'known' ? 'known' : 'unknown',
    firstSeen,
    lastSeen,
    knownCount,
    unknownCount,
    nextReview,
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
  const dueDate = new Date(startOfLocalDayTimestamp(now))
  dueDate.setDate(dueDate.getDate() + days)
  return dueDate.getTime()
}

export function readQuickMemoryRecordsFromStorage(userId?: QuickMemoryStorageUserId): QuickMemoryRecordMap {
  try {
    const raw = JSON.parse(localStorage.getItem(getQuickMemoryStorageKey(userId)) || '{}')
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
  const storageKey = getQuickMemoryStorageKey()
  localStorage.setItem(storageKey, JSON.stringify(records))
  if (storageKey !== STORAGE_KEYS.QUICK_MEMORY_RECORDS) {
    localStorage.removeItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS)
  }
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
  target: number = QUICK_MEMORY_MASTERY_TARGET,
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
