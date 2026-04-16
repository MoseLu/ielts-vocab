import { act, renderHook } from '@testing-library/react'
import type { Dispatch, SetStateAction } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AppSettings, LastState, Word, WordStatuses } from '../../../components/practice/types'
import { usePracticePageControls } from './usePracticePageControls'

const apiFetchMock = vi.fn(() => Promise.resolve(undefined))

vi.mock('../../../lib', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
}))

function createWord(): Word {
  return {
    word: 'alpha',
    phonetic: '/a/',
    pos: 'n.',
    definition: 'alpha',
  }
}

function createParams(overrides: Partial<Parameters<typeof usePracticePageControls>[0]> = {}) {
  return {
    mode: 'quickmemory' as const,
    currentDay: 1,
    userId: 42,
    bookId: null,
    chapterId: null,
    reviewMode: false,
    errorMode: false,
    queue: [0],
    queueIndex: 0,
    vocabulary: [createWord()],
    correctCount: 0,
    wrongCount: 0,
    errorReviewRound: 1,
    settings: {} as AppSettings,
    practiceBookId: null,
    reviewSummary: null,
    navigate: vi.fn(),
    showToast: vi.fn(),
    beginSession: vi.fn(),
    computeChapterWordsLearned: vi.fn(() => 0),
    correctCountRef: { current: 0 },
    wrongCountRef: { current: 0 },
    uniqueAnsweredRef: { current: new Set<string>() },
    errorProgressHydratedRef: { current: false },
    errorRoundResultsRef: { current: {} },
    vocabRef: { current: [createWord()] },
    queueRef: { current: [0] },
    startSpeechRecording: vi.fn(async () => {}),
    stopSpeechRecording: vi.fn(),
    speechConnected: true,
    setVocabulary: vi.fn(),
    setQueue: vi.fn(),
    setQueueIndex: vi.fn(),
    setCorrectCount: vi.fn(),
    setWrongCount: vi.fn(),
    setPreviousWord: vi.fn() as Dispatch<SetStateAction<Word | null>>,
    setLastState: vi.fn() as Dispatch<SetStateAction<LastState | null>>,
    setWordStatuses: vi.fn() as Dispatch<SetStateAction<WordStatuses>>,
    setReviewOffset: vi.fn(),
    setErrorReviewRound: vi.fn(),
    ...overrides,
  }
}

describe('usePracticePageControls saveProgress', () => {
  beforeEach(() => {
    apiFetchMock.mockReset()
    apiFetchMock.mockImplementation(() => Promise.resolve(undefined))
    localStorage.clear()
  })

  it('skips legacy day progress sync when currentDay is invalid', () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      currentDay: Number.NaN,
    })))

    act(() => {
      result.current.saveProgress(1, 0)
    })

    expect(apiFetchMock).not.toHaveBeenCalled()
    expect(localStorage.getItem('day_progress')).toBeNull()
  })

  it('posts legacy day progress when currentDay is valid', () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      currentDay: 3,
    })))

    act(() => {
      result.current.saveProgress(1, 0)
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/progress', {
      method: 'POST',
      body: JSON.stringify({
        day: 3,
        current_index: 1,
        correct_count: 1,
        wrong_count: 0,
        is_completed: true,
      }),
    })
    expect(localStorage.getItem('day_progress')).toContain('"3"')
  })

  it('stores resumable chapter snapshots locally and remotely', () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      mode: 'dictation',
      bookId: 'book-1',
      chapterId: 'chapter-1',
      queue: [0, 1],
      queueIndex: 0,
      vocabulary: [createWord(), { ...createWord(), word: 'beta' }],
      uniqueAnsweredRef: { current: new Set(['alpha']) },
      computeChapterWordsLearned: vi.fn(() => 1),
    })))

    act(() => {
      result.current.saveProgress(1, 0)
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/books/book-1/chapters/chapter-1/progress', {
      method: 'POST',
      body: JSON.stringify({
        current_index: 1,
        correct_count: 1,
        wrong_count: 0,
        is_completed: false,
        words_learned: 1,
        answered_words: ['alpha'],
        queue_words: ['alpha', 'beta'],
      }),
    })
    expect(JSON.parse(localStorage.getItem('chapter_progress') || '{}')['book-1_chapter-1']).toMatchObject({
      current_index: 1,
      answered_words: ['alpha'],
      queue_words: ['alpha', 'beta'],
    })
  })

  it('can reset an interrupted chapter back to the first word', async () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      mode: 'dictation',
      bookId: 'book-1',
      chapterId: 'chapter-1',
      queue: [0, 1],
      queueIndex: 1,
      vocabulary: [createWord(), { ...createWord(), word: 'beta' }],
    })))

    await act(async () => {
      await result.current.resetChapterProgress()
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/books/book-1/chapters/chapter-1/progress', {
      method: 'POST',
      body: JSON.stringify({
        current_index: 0,
        correct_count: 0,
        wrong_count: 0,
        is_completed: false,
        words_learned: 0,
        answered_words: [],
        queue_words: ['alpha', 'beta'],
      }),
    })
    expect(JSON.parse(localStorage.getItem('chapter_progress') || '{}')['book-1_chapter-1']).toMatchObject({
      current_index: 0,
      correct_count: 0,
      wrong_count: 0,
      words_learned: 0,
      answered_words: [],
      queue_words: ['alpha', 'beta'],
    })
  })
})
