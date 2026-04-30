import { STORAGE_KEYS } from '../constants'
import { apiFetch } from './index'

const MIGRATION_TASK = 'local_storage_migration_v1_once'
const SMART_PENDING_KEY = 'smart_word_stats_pending'

type MigrationUser = {
  id?: string | number | null
}

type MigrationSourcePayload = {
  stats?: unknown[]
  records?: unknown[]
  words?: unknown[]
}

type MigrationResponse = {
  migration_task?: string
  sources?: Record<string, { ok?: boolean; migrated_count?: number; error?: string }>
}

export type LegacyLocalStorageMigrationResult = {
  completed: boolean
  attempted: boolean
}

export function getLegacyLocalStorageMigrationDoneKey(userId: string | number): string {
  return `local_storage_migration_v1_done:user:${String(userId)}`
}

function parseJson(raw: string | null): unknown {
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

function nonEmptyRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null
  const record = value as Record<string, unknown>
  return Object.keys(record).length > 0 ? record : null
}

function normalizeSmartStats(value: unknown): unknown[] {
  const stats = nonEmptyRecord(value)
  if (!stats) return []
  return Object.entries(stats)
    .filter(([word, stat]) => word.trim() && stat && typeof stat === 'object')
    .map(([word, stat]) => ({ word, ...(stat as Record<string, unknown>) }))
}

function normalizeSmartPending(value: unknown): unknown[] {
  if (!Array.isArray(value)) return []
  return value
    .filter(item => item && typeof item === 'object')
    .map(item => item as Record<string, unknown>)
    .filter(item => typeof item.word === 'string' && item.word.trim())
}

function normalizeMappedRecords(value: unknown): unknown[] {
  const records = nonEmptyRecord(value)
  if (!records) return []
  return Object.entries(records)
    .filter(([key, record]) => key.trim() && record && typeof record === 'object')
    .map(([key, record]) => ({ word: key, ...(record as Record<string, unknown>) }))
}

function normalizeWrongWords(value: unknown): unknown[] {
  if (Array.isArray(value)) return value.filter(item => item && typeof item === 'object')
  const records = nonEmptyRecord(value)
  return records ? Object.values(records).filter(item => item && typeof item === 'object') : []
}

function normalizeBookProgress(value: unknown): unknown[] {
  const progress = nonEmptyRecord(value)
  if (!progress) return []
  return Object.entries(progress)
    .filter(([bookId, record]) => bookId.trim() && record && typeof record === 'object')
    .map(([bookId, record]) => ({
      book_id: bookId,
      ...(record as Record<string, unknown>),
    }))
}

function splitChapterProgressKey(key: string): { bookId: string; chapterId: string } | null {
  const dividerIndex = key.lastIndexOf('_')
  if (dividerIndex <= 0 || dividerIndex >= key.length - 1) return null
  return {
    bookId: key.slice(0, dividerIndex),
    chapterId: key.slice(dividerIndex + 1),
  }
}

function normalizeChapterProgress(value: unknown): unknown[] {
  const progress = nonEmptyRecord(value)
  if (!progress) return []
  return Object.entries(progress)
    .filter(([, record]) => record && typeof record === 'object')
    .map(([key, record]) => {
      const raw = record as Record<string, unknown>
      const parsed = splitChapterProgressKey(key)
      const bookId = typeof raw.book_id === 'string' ? raw.book_id : parsed?.bookId
      const chapterId = raw.chapter_id ?? parsed?.chapterId
      if (!bookId || chapterId == null) return null
      return {
        book_id: bookId,
        chapter_id: String(chapterId),
        mode: typeof raw.mode === 'string' && raw.mode.trim() ? raw.mode : 'smart',
        ...raw,
      }
    })
    .filter((record): record is Record<string, unknown> => record !== null)
}

function normalizeDayProgress(value: unknown): unknown[] {
  const progress = nonEmptyRecord(value)
  if (!progress) return []
  return Object.entries(progress)
    .filter(([day, record]) => Number.isFinite(Number(day)) && record && typeof record === 'object')
    .map(([day, record]) => ({
      day: Number(day),
      ...(record as Record<string, unknown>),
    }))
}

function collectLegacySources(): Record<string, MigrationSourcePayload> {
  const sources: Record<string, MigrationSourcePayload> = {}
  const smartStats = normalizeSmartStats(parseJson(localStorage.getItem(STORAGE_KEYS.SMART_WORD_STATS)))
  const smartPending = normalizeSmartPending(parseJson(localStorage.getItem(SMART_PENDING_KEY)))
  const quickMemory = normalizeMappedRecords(parseJson(localStorage.getItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS)))
  const wrongWords = normalizeWrongWords(parseJson(localStorage.getItem(STORAGE_KEYS.WRONG_WORDS)))
  const bookProgress = normalizeBookProgress(parseJson(localStorage.getItem(STORAGE_KEYS.BOOK_PROGRESS)))
  const chapterProgress = normalizeChapterProgress(parseJson(localStorage.getItem(STORAGE_KEYS.CHAPTER_PROGRESS)))
  const dayProgress = normalizeDayProgress(parseJson(localStorage.getItem(STORAGE_KEYS.DAY_PROGRESS)))

  if (smartStats.length) sources[STORAGE_KEYS.SMART_WORD_STATS] = { stats: smartStats }
  if (smartPending.length) sources[SMART_PENDING_KEY] = { stats: smartPending }
  if (quickMemory.length) sources[STORAGE_KEYS.QUICK_MEMORY_RECORDS] = { records: quickMemory }
  if (wrongWords.length) sources[STORAGE_KEYS.WRONG_WORDS] = { words: wrongWords }
  if (bookProgress.length) sources[STORAGE_KEYS.BOOK_PROGRESS] = { records: bookProgress }
  if (chapterProgress.length) sources[STORAGE_KEYS.CHAPTER_PROGRESS] = { records: chapterProgress }
  if (dayProgress.length) sources[STORAGE_KEYS.DAY_PROGRESS] = { records: dayProgress }
  return sources
}

export async function runLegacyLocalStorageMigration(
  user: MigrationUser | null | undefined,
): Promise<LegacyLocalStorageMigrationResult> {
  if (user?.id == null) return { completed: false, attempted: false }

  const doneKey = getLegacyLocalStorageMigrationDoneKey(user.id)
  if (localStorage.getItem(doneKey) === '1') {
    return { completed: true, attempted: false }
  }

  const sources = collectLegacySources()
  const sourceNames = Object.keys(sources)
  if (!sourceNames.length) {
    return { completed: true, attempted: false }
  }

  const response = await apiFetch<MigrationResponse>('/api/ai/local-storage-migration', {
    method: 'POST',
    body: JSON.stringify({
      migration_task: MIGRATION_TASK,
      sources,
    }),
  })
  const results = response.sources ?? {}
  let completed = true

  for (const sourceName of sourceNames) {
    if (results[sourceName]?.ok) {
      localStorage.removeItem(sourceName)
    } else {
      completed = false
    }
  }

  if (completed) {
    localStorage.setItem(doneKey, '1')
  }
  return { completed, attempted: true }
}
