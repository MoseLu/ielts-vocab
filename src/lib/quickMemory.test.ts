import {
  getQuickMemoryStorageKey,
  QUICK_MEMORY_MASTERY_TARGET,
  readQuickMemoryRecordsFromStorage,
  resetQuickMemoryRecord,
  updateQuickMemoryRecord,
  writeQuickMemoryRecordsToStorage,
} from './quickMemory'
import { STORAGE_KEYS } from '../constants'

describe('quickMemory', () => {
  const sampleRecord = {
    alpha: {
      status: 'known' as const,
      firstSeen: 1000,
      lastSeen: 2000,
      knownCount: 1,
      unknownCount: 0,
      nextReview: 3000,
      fuzzyCount: 0,
    },
  }

  beforeEach(() => {
    localStorage.clear()
  })

  it('resets the consecutive known count when the learner gets a word wrong', () => {
    const { records: seeded } = updateQuickMemoryRecord({}, 'alpha', 'known', false, 1000)
    const result = updateQuickMemoryRecord(seeded, 'alpha', 'unknown', false, 2000)

    expect(result.record).toEqual(expect.objectContaining({
      status: 'unknown',
      knownCount: 0,
      unknownCount: 1,
      lastSeen: 2000,
    }))
  })

  it('marks a word as mastered after the full Ebbinghaus streak completes', () => {
    let records = {}
    let currentRecord = null

    for (let index = 0; index < QUICK_MEMORY_MASTERY_TARGET; index += 1) {
      const result = updateQuickMemoryRecord(records, 'alpha', 'known', false, 1000 + index)
      records = result.records
      currentRecord = result.record
    }

    expect(currentRecord).toEqual(expect.objectContaining({
      status: 'known',
      knownCount: QUICK_MEMORY_MASTERY_TARGET,
      nextReview: 0,
    }))
  })

  it('resets an existing word back to the start of the Ebbinghaus chain', () => {
    const { records: seeded } = updateQuickMemoryRecord({}, 'alpha', 'known', true, 1000)
    const result = resetQuickMemoryRecord(seeded, 'alpha', 2000)

    expect(result.record).toEqual(expect.objectContaining({
      status: 'unknown',
      knownCount: 0,
      fuzzyCount: 1,
      lastSeen: 2000,
    }))
    expect(result.record?.nextReview).toBeGreaterThan(2000)
  })

  it('stores quick-memory records under a user-scoped key', () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 2 }))

    writeQuickMemoryRecordsToStorage(sampleRecord)

    expect(localStorage.getItem(getQuickMemoryStorageKey(2))).not.toBeNull()
    expect(localStorage.getItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS)).toBeNull()
  })

  it('isolates quick-memory records between different users', () => {
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 2 }))
    writeQuickMemoryRecordsToStorage(sampleRecord)

    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 3 }))
    writeQuickMemoryRecordsToStorage({
      beta: {
        status: 'unknown',
        firstSeen: 4000,
        lastSeen: 5000,
        knownCount: 0,
        unknownCount: 1,
        nextReview: 6000,
        fuzzyCount: 0,
      },
    })

    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 2 }))
    expect(Object.keys(readQuickMemoryRecordsFromStorage())).toEqual(['alpha'])

    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 3 }))
    expect(Object.keys(readQuickMemoryRecordsFromStorage())).toEqual(['beta'])
  })

  it('ignores the legacy global quick-memory cache when a user is known', () => {
    localStorage.setItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS, JSON.stringify(sampleRecord))
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 2 }))

    expect(readQuickMemoryRecordsFromStorage()).toEqual({})
  })
})
