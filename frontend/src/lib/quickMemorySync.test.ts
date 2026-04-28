import { beforeEach, describe, expect, it, vi } from 'vitest'
import { STORAGE_KEYS } from '../constants'
import {
  getQuickMemoryStorageKey,
  readQuickMemoryRecordsFromStorage,
} from './quickMemory'
import {
  reconcileQuickMemoryRecordsWithBackend,
  retryPendingQuickMemorySync,
  resetQuickMemorySyncStateForTests,
  syncQuickMemoryRecordsToBackend,
} from './quickMemorySync'

const apiFetchMock = vi.fn()

vi.mock('./index', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

describe('quickMemorySync', () => {
  beforeEach(() => {
    localStorage.clear()
    localStorage.setItem(STORAGE_KEYS.AUTH_USER, JSON.stringify({ id: 42 }))
    apiFetchMock.mockReset()
    resetQuickMemorySyncStateForTests()
  })

  it('pushes newer local quick-memory records back to the backend before stats consumers read stale totals', async () => {
    localStorage.setItem(getQuickMemoryStorageKey(42), JSON.stringify({
      alpha: {
        status: 'known',
        firstSeen: 1000,
        lastSeen: 5000,
        knownCount: 2,
        unknownCount: 0,
        nextReview: 9000,
        fuzzyCount: 0,
        bookId: 'book-1',
        chapterId: '1',
      },
      beta: {
        status: 'unknown',
        firstSeen: 2000,
        lastSeen: 4000,
        knownCount: 0,
        unknownCount: 1,
        nextReview: 6000,
        fuzzyCount: 0,
        bookId: 'book-1',
        chapterId: '2',
      },
    }))

    apiFetchMock.mockImplementation((url: string) => {
      if (url === '/api/ai/quick-memory') {
        return Promise.resolve({
          records: [
            {
              word: 'alpha',
              status: 'known',
              firstSeen: 1000,
              lastSeen: 3000,
              knownCount: 1,
              unknownCount: 0,
              nextReview: 7000,
              fuzzyCount: 0,
              bookId: 'book-1',
              chapterId: '1',
            },
            {
              word: 'beta',
              status: 'known',
              firstSeen: 2000,
              lastSeen: 7000,
              knownCount: 1,
              unknownCount: 1,
              nextReview: 12000,
              fuzzyCount: 0,
              bookId: 'book-1',
              chapterId: '2',
            },
          ],
        })
      }

      if (url === '/api/ai/quick-memory/sync') {
        return Promise.resolve({})
      }

      return Promise.reject(new Error(`Unexpected url: ${url}`))
    })

    const result = await reconcileQuickMemoryRecordsWithBackend()

    expect(apiFetchMock).toHaveBeenNthCalledWith(
      1,
      '/api/ai/quick-memory',
      { cache: 'no-store' },
    )

    const syncCall = apiFetchMock.mock.calls.find(([url]) => url === '/api/ai/quick-memory/sync')
    expect(syncCall).toBeTruthy()
    expect(JSON.parse(String(syncCall?.[1]?.body ?? '{}'))).toMatchObject({
      source: 'quickmemory',
      records: [
        expect.objectContaining({
          word: 'alpha',
          lastSeen: 5000,
          knownCount: 2,
          nextReview: 9000,
        }),
      ],
    })

    expect(readQuickMemoryRecordsFromStorage()).toMatchObject({
      alpha: expect.objectContaining({ lastSeen: 5000, knownCount: 2 }),
      beta: expect.objectContaining({ lastSeen: 7000, knownCount: 1, nextReview: 12000 }),
    })
    expect(result).toEqual({ uploadedCount: 1 })
  })

  it('skips reconciliation when stats pages have no local quick-memory data yet', async () => {
    const result = await reconcileQuickMemoryRecordsWithBackend({ skipIfLocalEmpty: true })

    expect(apiFetchMock).not.toHaveBeenCalled()
    expect(result).toEqual({ uploadedCount: 0 })
  })

  it('persists failed quick-memory sync records and retries them later', async () => {
    const record = {
      status: 'known' as const,
      firstSeen: 1000,
      lastSeen: 5000,
      knownCount: 2,
      unknownCount: 0,
      nextReview: 9000,
      fuzzyCount: 0,
      bookId: 'book-1',
      chapterId: '1',
    }
    const pendingKey = `${getQuickMemoryStorageKey(42)}:pending_sync`

    apiFetchMock.mockRejectedValueOnce(new Error('offline'))
    await expect(syncQuickMemoryRecordsToBackend([{ word: 'Alpha', record }])).rejects.toThrow('offline')

    expect(JSON.parse(localStorage.getItem(pendingKey) || '{}')).toMatchObject({
      alpha: expect.objectContaining({ lastSeen: 5000, knownCount: 2 }),
    })

    apiFetchMock.mockResolvedValueOnce({})
    const result = await retryPendingQuickMemorySync()

    expect(result).toEqual({ uploadedCount: 1 })
    expect(localStorage.getItem(pendingKey)).toBeNull()
    const retryBody = JSON.parse(String(apiFetchMock.mock.calls[1]?.[1]?.body ?? '{}'))
    expect(retryBody.records).toEqual([
      expect.objectContaining({ word: 'alpha', lastSeen: 5000, knownCount: 2 }),
    ])
  })
})
