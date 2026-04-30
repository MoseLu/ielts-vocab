import { beforeEach, describe, expect, it, vi } from 'vitest'
import { STORAGE_KEYS } from '../constants'
import {
  getLegacyLocalStorageMigrationDoneKey,
  runLegacyLocalStorageMigration,
} from './localStorageMigration'

const apiFetchMock = vi.fn()

vi.mock('./index', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

const user = {
  id: 3,
  username: 'alice',
}

describe('localStorageMigration', () => {
  beforeEach(() => {
    localStorage.clear()
    apiFetchMock.mockReset()
  })

  it('uploads legacy learning keys once and clears successful sources', async () => {
    localStorage.setItem(STORAGE_KEYS.SMART_WORD_STATS, JSON.stringify({
      dynamic: {
        listening: { correct: 2, wrong: 1 },
        meaning: { correct: 1, wrong: 0 },
        dictation: { correct: 0, wrong: 1 },
      },
    }))
    localStorage.setItem('smart_word_stats_pending', JSON.stringify([{
      word: 'stamina',
      listening: { correct: 1, wrong: 0 },
      meaning: { correct: 0, wrong: 1 },
      dictation: { correct: 0, wrong: 0 },
      failedAt: '2026-04-01T00:00:00.000Z',
    }]))
    localStorage.setItem(STORAGE_KEYS.QUICK_MEMORY_RECORDS, JSON.stringify({
      alpha: {
        status: 'known',
        firstSeen: 100,
        lastSeen: 200,
        knownCount: 2,
        unknownCount: 0,
        nextReview: 300,
        fuzzyCount: 0,
        bookId: 'book-1',
        chapterId: '2',
      },
    }))
    localStorage.setItem(STORAGE_KEYS.WRONG_WORDS, JSON.stringify([
      { word: 'fragile', definition: 'easy to break', wrong_count: 2 },
    ]))
    localStorage.setItem(STORAGE_KEYS.BOOK_PROGRESS, JSON.stringify({
      'book-1': { current_index: 8, correct_count: 6, wrong_count: 2, is_completed: false },
    }))
    localStorage.setItem(STORAGE_KEYS.CHAPTER_PROGRESS, JSON.stringify({
      'book-1_2': {
        current_index: 4,
        words_learned: 4,
        correct_count: 3,
        wrong_count: 1,
        is_completed: false,
        queue_words: ['alpha', 'beta'],
      },
    }))
    localStorage.setItem(STORAGE_KEYS.DAY_PROGRESS, JSON.stringify({
      7: { current_index: 5, correct_count: 4, wrong_count: 1 },
    }))
    apiFetchMock.mockResolvedValueOnce({
      migration_task: 'local_storage_migration_v1_once',
      sources: {
        smart_word_stats: { ok: true, migrated_count: 1 },
        smart_word_stats_pending: { ok: true, migrated_count: 1 },
        quick_memory_records: { ok: true, migrated_count: 1 },
        wrong_words: { ok: true, migrated_count: 1 },
        book_progress: { ok: true, migrated_count: 1 },
        chapter_progress: { ok: true, migrated_count: 1 },
        day_progress: { ok: true, migrated_count: 1 },
      },
    })

    const result = await runLegacyLocalStorageMigration(user)

    expect(apiFetchMock).toHaveBeenCalledTimes(1)
    const [url, options] = apiFetchMock.mock.calls[0]
    expect(url).toBe('/api/ai/local-storage-migration')
    const body = JSON.parse(String(options.body))
    expect(body.migration_task).toBe('local_storage_migration_v1_once')
    expect(body.sources.smart_word_stats.stats[0]).toMatchObject({ word: 'dynamic' })
    expect(body.sources.smart_word_stats_pending.stats[0]).toMatchObject({ word: 'stamina' })
    expect(body.sources.quick_memory_records.records[0]).toMatchObject({ word: 'alpha' })
    expect(body.sources.chapter_progress.records[0]).toMatchObject({
      book_id: 'book-1',
      chapter_id: '2',
      mode: 'smart',
    })

    expect(result.completed).toBe(true)
    for (const key of [
      STORAGE_KEYS.SMART_WORD_STATS,
      'smart_word_stats_pending',
      STORAGE_KEYS.QUICK_MEMORY_RECORDS,
      STORAGE_KEYS.WRONG_WORDS,
      STORAGE_KEYS.BOOK_PROGRESS,
      STORAGE_KEYS.CHAPTER_PROGRESS,
      STORAGE_KEYS.DAY_PROGRESS,
    ]) {
      expect(localStorage.getItem(key)).toBeNull()
    }
    expect(localStorage.getItem(getLegacyLocalStorageMigrationDoneKey(3))).toBe('1')
  })

  it('keeps failed sources for the next login retry', async () => {
    localStorage.setItem(STORAGE_KEYS.WRONG_WORDS, JSON.stringify([{ word: 'fragile' }]))
    localStorage.setItem(STORAGE_KEYS.BOOK_PROGRESS, JSON.stringify({
      'book-1': { current_index: 1 },
    }))
    apiFetchMock.mockResolvedValueOnce({
      migration_task: 'local_storage_migration_v1_once',
      sources: {
        wrong_words: { ok: true, migrated_count: 1 },
        book_progress: { ok: false, error: 'upstream unavailable' },
      },
    })

    const result = await runLegacyLocalStorageMigration(user)

    expect(result.completed).toBe(false)
    expect(localStorage.getItem(STORAGE_KEYS.WRONG_WORDS)).toBeNull()
    expect(localStorage.getItem(STORAGE_KEYS.BOOK_PROGRESS)).not.toBeNull()
    expect(localStorage.getItem(getLegacyLocalStorageMigrationDoneKey(3))).toBeNull()
  })

  it('does not mark the one-shot task done when no legacy keys exist', async () => {
    const result = await runLegacyLocalStorageMigration(user)

    expect(result).toEqual({ completed: true, attempted: false })
    expect(apiFetchMock).not.toHaveBeenCalled()
    expect(localStorage.getItem(getLegacyLocalStorageMigrationDoneKey(3))).toBeNull()
  })
})
