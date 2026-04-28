import { apiFetch } from './index'
import {
  getQuickMemoryStorageKey,
  mergeQuickMemoryRecordsByLastSeen,
  type QuickMemoryRecordMap,
  readQuickMemoryRecordsFromStorage,
  type QuickMemoryRecordInput,
  type QuickMemoryRecordState,
  writeQuickMemoryRecordsToStorage,
} from './quickMemory'

export interface QuickMemorySyncEntry {
  word: string
  record: QuickMemoryRecordState
}

export interface QuickMemoryReconcileResult {
  uploadedCount: number
}

interface ReconcileQuickMemoryOptions {
  skipIfLocalEmpty?: boolean
  minIntervalMs?: number
  force?: boolean
}

function normalizeWordKey(word: string): string {
  return word.trim().toLowerCase()
}

function getPendingSyncStorageKey(): string {
  return `${getQuickMemoryStorageKey()}:pending_sync`
}

function mergeRecordMap(base: QuickMemoryRecordMap, incoming: QuickMemoryRecordMap): QuickMemoryRecordMap {
  const merged: QuickMemoryRecordMap = { ...base }
  Object.entries(incoming).forEach(([word, record]) => {
    const current = merged[word]
    if (!current || record.lastSeen >= current.lastSeen) {
      merged[word] = record
    }
  })
  return merged
}

function normalizeSyncEntries(records: QuickMemorySyncEntry[]): QuickMemorySyncEntry[] {
  const normalized: Record<string, QuickMemoryRecordState> = {}
  records.forEach(({ word, record }) => {
    const wordKey = normalizeWordKey(word)
    if (!wordKey) return
    const current = normalized[wordKey]
    if (!current || record.lastSeen >= current.lastSeen) {
      normalized[wordKey] = record
    }
  })
  return Object.entries(normalized).map(([word, record]) => ({ word, record }))
}

function readPendingSyncRecords(): QuickMemoryRecordMap {
  try {
    const raw = JSON.parse(localStorage.getItem(getPendingSyncStorageKey()) || '{}')
    if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {}
    const inputs = Object.entries(raw as Record<string, unknown>).map(([word, value]) => ({
      word,
      ...(value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}),
    }))
    return mergeQuickMemoryRecordsByLastSeen({}, inputs)
  } catch {
    return {}
  }
}

function writePendingSyncRecords(records: QuickMemoryRecordMap): void {
  const storageKey = getPendingSyncStorageKey()
  if (Object.keys(records).length === 0) {
    localStorage.removeItem(storageKey)
    return
  }
  localStorage.setItem(storageKey, JSON.stringify(records))
}

function persistPendingSyncEntries(entries: QuickMemorySyncEntry[]): void {
  const pending = readPendingSyncRecords()
  writePendingSyncRecords(mergeRecordMap(
    pending,
    Object.fromEntries(entries.map(({ word, record }) => [word, record])),
  ))
}

function clearPendingSyncEntries(entries: QuickMemorySyncEntry[]): void {
  const pending = readPendingSyncRecords()
  let changed = false
  entries.forEach(({ word, record }) => {
    const pendingRecord = pending[word]
    if (pendingRecord && pendingRecord.lastSeen <= record.lastSeen) {
      delete pending[word]
      changed = true
    }
  })
  if (changed) writePendingSyncRecords(pending)
}

function clearServerSyncedPendingRecords(serverLastSeenByWord: Map<string, number>): void {
  const pending = readPendingSyncRecords()
  let changed = false
  Object.entries(pending).forEach(([word, record]) => {
    if ((serverLastSeenByWord.get(word) ?? 0) >= record.lastSeen) {
      delete pending[word]
      changed = true
    }
  })
  if (changed) writePendingSyncRecords(pending)
}

function buildQuickMemorySyncRecord(word: string, record: QuickMemoryRecordState) {
  return {
    word: normalizeWordKey(word),
    bookId: record.bookId,
    chapterId: record.chapterId,
    status: record.status,
    firstSeen: record.firstSeen,
    lastSeen: record.lastSeen,
    knownCount: record.knownCount,
    unknownCount: record.unknownCount,
    nextReview: record.nextReview,
    fuzzyCount: record.fuzzyCount,
  }
}

export async function syncQuickMemoryRecordsToBackend(
  records: QuickMemorySyncEntry[],
  options: { keepalive?: boolean } = {},
): Promise<void> {
  const entries = normalizeSyncEntries(records)
  if (!entries.length) return

  persistPendingSyncEntries(entries)

  await apiFetch('/api/ai/quick-memory/sync', {
    method: 'POST',
    keepalive: options.keepalive,
    body: JSON.stringify({
      source: 'quickmemory',
      records: entries.map(({ word, record }) => buildQuickMemorySyncRecord(word, record)),
    }),
  })
  clearPendingSyncEntries(entries)
}

export async function retryPendingQuickMemorySync(
  options: { keepalive?: boolean } = {},
): Promise<QuickMemoryReconcileResult> {
  const pending = readPendingSyncRecords()
  const entries = Object.entries(pending).map(([word, record]) => ({ word, record }))
  if (entries.length === 0) return { uploadedCount: 0 }

  await syncQuickMemoryRecordsToBackend(entries, options)
  return { uploadedCount: entries.length }
}

const reconcileState = new Map<string, { inFlight: Promise<QuickMemoryReconcileResult> | null; lastCompletedAt: number }>()

export async function reconcileQuickMemoryRecordsWithBackend(
  options: ReconcileQuickMemoryOptions = {},
): Promise<QuickMemoryReconcileResult> {
  const storageKey = getQuickMemoryStorageKey()
  const existingState = reconcileState.get(storageKey)
  const state = existingState ?? { inFlight: null, lastCompletedAt: 0 }
  if (!existingState) reconcileState.set(storageKey, state)

  const minIntervalMs = options.minIntervalMs ?? 0
  if (!options.force) {
    if (state.inFlight) return state.inFlight
    if (minIntervalMs > 0 && Date.now() - state.lastCompletedAt < minIntervalMs) {
      return { uploadedCount: 0 }
    }
  }

  const task = (async () => {
    const localRecords = readQuickMemoryRecordsFromStorage()
    const pendingRecords = readPendingSyncRecords()
    if (
      options.skipIfLocalEmpty
      && Object.keys(localRecords).length === 0
      && Object.keys(pendingRecords).length === 0
    ) {
      return { uploadedCount: 0 }
    }

    const data = await apiFetch<{ records: QuickMemoryRecordInput[] }>('/api/ai/quick-memory', {
      cache: 'no-store',
    })
    const serverRecords = Array.isArray(data.records) ? data.records : []
    const serverLastSeenByWord = new Map<string, number>()
    serverRecords.forEach(item => {
      const wordKey = normalizeWordKey(String(item.word || ''))
      if (!wordKey) return
      const nextLastSeen = typeof item.lastSeen === 'number' ? item.lastSeen : 0
      serverLastSeenByWord.set(
        wordKey,
        Math.max(serverLastSeenByWord.get(wordKey) ?? 0, nextLastSeen),
      )
    })
    clearServerSyncedPendingRecords(serverLastSeenByWord)

    const localAndPendingRecords = mergeRecordMap(localRecords, pendingRecords)
    const merged = mergeQuickMemoryRecordsByLastSeen(localAndPendingRecords, serverRecords)
    writeQuickMemoryRecordsToStorage(merged)

    const newerLocalRecords = Object.entries(merged)
      .filter(([wordKey, record]) => record.lastSeen > (serverLastSeenByWord.get(wordKey) ?? 0))
      .map(([word, record]) => ({ word, record }))

    if (newerLocalRecords.length > 0) {
      await syncQuickMemoryRecordsToBackend(newerLocalRecords)
    }

    return { uploadedCount: newerLocalRecords.length }
  })()

  state.inFlight = task
  let result: QuickMemoryReconcileResult
  try {
    result = await task
  } finally {
    state.inFlight = null
    state.lastCompletedAt = Date.now()
  }
  return result
}

export function resetQuickMemorySyncStateForTests(): void {
  reconcileState.clear()
}
