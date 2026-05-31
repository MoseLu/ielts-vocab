import { describe, expect, it, vi, beforeEach } from 'vitest'
import {
  loadBookProgressSnapshot,
  loadChapterProgressSnapshot,
  persistBookProgressSnapshot,
} from './progressStorage'
import { STORAGE_KEYS } from '../../constants'

const apiFetchMock = vi.fn()

vi.mock('../../lib', async () => {
  const actual = await vi.importActual<typeof import('../../lib')>('../../lib')
  return {
    ...actual,
    apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  }
})

describe('progressStorage remote/local resume snapshots', () => {
  beforeEach(() => {
    localStorage.clear()
    apiFetchMock.mockReset()
  })

  it('uses a newer remote chapter snapshot over stale local progress', async () => {
    localStorage.setItem(STORAGE_KEYS.CHAPTER_PROGRESS, JSON.stringify({
      'book-1_chapter-1': {
        current_index: 133,
        correct_count: 10,
        wrong_count: 2,
        words_learned: 133,
        is_completed: false,
        queue_words: ['chop', 'ceremony'],
        updatedAt: '2026-05-03T00:00:00.000Z',
      },
    }))
    apiFetchMock.mockResolvedValue({
      chapter_progress: {
        'chapter-1': {
          current_index: 134,
          correct_count: 11,
          wrong_count: 2,
          words_learned: 134,
          is_completed: false,
          queue_words: ['chop', 'ceremony'],
          updated_at: '2026-05-04T00:00:00.000Z',
        },
      },
    })

    await expect(loadChapterProgressSnapshot('book-1', 'chapter-1')).resolves.toMatchObject({
      current_index: 134,
      words_learned: 134,
    })
  })

  it('keeps newer local book progress and falls back to local when remote fails', async () => {
    persistBookProgressSnapshot('book-1', {
      current_index: 9,
      correct_count: 7,
      wrong_count: 1,
      is_completed: false,
      updatedAt: '2026-05-04T00:00:00.000Z',
    }, ['alpha'])
    apiFetchMock.mockResolvedValueOnce({
      progress: {
        current_index: 4,
        correct_count: 4,
        wrong_count: 0,
        is_completed: false,
        updated_at: '2026-05-03T00:00:00.000Z',
      },
    })

    await expect(loadBookProgressSnapshot('book-1')).resolves.toMatchObject({
      current_index: 9,
    })

    apiFetchMock.mockRejectedValueOnce(new Error('offline'))
    await expect(loadBookProgressSnapshot('book-1')).resolves.toMatchObject({
      current_index: 9,
    })
  })
})
