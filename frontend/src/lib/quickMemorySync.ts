import { apiFetch } from './index'
import {
  getQuickMemoryStorageKey,
  mergeQuickMemoryRecordsByLastSeen,
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

function buildQuickMemorySyncRecord(word: string, record: QuickMemoryRecordState) {
  return {
    word: word.toLowerCase(),
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
  if (!records.length) return

  await apiFetch('/api/ai/quick-memory/sync', {
    method: 'POST',
    keepalive: options.keepalive,
    body: JSON.stringify({
      source: 'quickmemory',
      records: records.map(({ word, record }) => buildQuickMemorySyncRecord(word, record)),
    }),
  })
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
    if (options.skipIfLocalEmpty && Object.keys(localRecords).length === 0) {
      return { uploadedCount: 0 }
    }

    const data = await apiFetch<{ records: QuickMemoryRecordInput[] }>('/api/ai/quick-memory', {
      cache: 'no-store',
    })
    const serverRecords = Array.isArray(data.records) ? data.records : []
    const merged = mergeQuickMemoryRecordsByLastSeen(localRecords, serverRecords)
    writeQuickMemoryRecordsToStorage(merged)

    const serverLastSeenByWord = new Map<string, number>()
    serverRecords.forEach(item => {
      const wordKey = String(item.word || '').trim().toLowerCase()
      if (!wordKey) return
      const nextLastSeen = typeof item.lastSeen === 'number' ? item.lastSeen : 0
      serverLastSeenByWord.set(
        wordKey,
        Math.max(serverLastSeenByWord.get(wordKey) ?? 0, nextLastSeen),
      )
    })

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
