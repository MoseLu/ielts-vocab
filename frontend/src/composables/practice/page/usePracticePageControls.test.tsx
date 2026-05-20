import { act, renderHook } from '@testing-library/react'
import type { Dispatch, SetStateAction } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AppSettings, LastState, Word, WordStatuses } from '../../../features/practice/types'
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
    chapterCorrectBaselineRef: { current: 0 },
    chapterWrongBaselineRef: { current: 0 },
    uniqueAnsweredRef: { current: new Set<string>() },
    chapterGroupStartRef: { current: 0 },
    chapterQueueWordsRef: { current: [] },
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
    setPracticeGroup: vi.fn(),
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
        mode: 'dictation',
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

  it('stores grouped chapter progress using the full chapter queue', () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      mode: 'dictation',
      bookId: 'book-1',
      chapterId: 'chapter-1',
      queue: [1, 2],
      queueIndex: 0,
      vocabulary: [
        { ...createWord(), word: 'alpha' },
        { ...createWord(), word: 'beta' },
        { ...createWord(), word: 'gamma' },
        { ...createWord(), word: 'delta' },
      ],
      uniqueAnsweredRef: { current: new Set(['beta']) },
      chapterGroupStartRef: { current: 1 },
      chapterQueueWordsRef: { current: ['alpha', 'beta', 'gamma', 'delta'] },
      computeChapterWordsLearned: vi.fn(() => 1),
    })))

    act(() => {
      result.current.saveProgress(1, 0)
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/books/book-1/chapters/chapter-1/progress', {
      method: 'POST',
      body: JSON.stringify({
        mode: 'dictation',
        current_index: 2,
        correct_count: 1,
        wrong_count: 0,
        is_completed: false,
        words_learned: 1,
        answered_words: ['beta'],
        queue_words: ['alpha', 'beta', 'gamma', 'delta'],
      }),
    })
    expect(JSON.parse(localStorage.getItem('chapter_progress') || '{}')['book-1_chapter-1']).toMatchObject({
      current_index: 2,
      queue_words: ['alpha', 'beta', 'gamma', 'delta'],
    })
  })

  it('stores grouped chapter progress with cumulative chapter counts', () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      mode: 'dictation',
      bookId: 'wrong_words_3',
      chapterId: 'wrong_words_3_m',
      queue: [2, 3],
      queueIndex: 1,
      vocabulary: [
        { ...createWord(), word: 'mock' },
        { ...createWord(), word: 'model' },
        { ...createWord(), word: 'module' },
        { ...createWord(), word: 'modify' },
      ],
      uniqueAnsweredRef: { current: new Set(['module', 'modify']) },
      chapterGroupStartRef: { current: 2 },
      chapterQueueWordsRef: { current: ['mock', 'model', 'module', 'modify'] },
      chapterCorrectBaselineRef: { current: 2 },
      chapterWrongBaselineRef: { current: 0 },
      computeChapterWordsLearned: vi.fn(() => 4),
    })))

    act(() => {
      result.current.saveProgress(1, 1)
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/books/wrong_words_3/chapters/wrong_words_3_m/progress', {
      method: 'POST',
      body: JSON.stringify({
        mode: 'dictation',
        current_index: 4,
        correct_count: 3,
        wrong_count: 1,
        is_completed: true,
        words_learned: 4,
        answered_words: ['module', 'modify'],
        queue_words: ['mock', 'model', 'module', 'modify'],
      }),
    })
  })

  it('marks a resumed grouped chapter complete when the full chapter queue reaches the end', () => {
    const { result } = renderHook(() => usePracticePageControls(createParams({
      mode: 'quickmemory',
      bookId: 'wrong_words_3',
      chapterId: 'wrong_words_3_m',
      queue: [167, 168],
      queueIndex: 1,
      vocabulary: Array.from({ length: 169 }, (_, index) => ({
        ...createWord(),
        word: `m-word-${index}`,
      })),
      uniqueAnsweredRef: { current: new Set(['m-word-167', 'm-word-168']) },
      chapterGroupStartRef: { current: 167 },
      chapterQueueWordsRef: { current: Array.from({ length: 169 }, (_, index) => `m-word-${index}`) },
      chapterCorrectBaselineRef: { current: 58 },
      chapterWrongBaselineRef: { current: 30 },
      computeChapterWordsLearned: vi.fn(() => 167),
    })))

    act(() => {
      result.current.saveProgress(2, 0)
    })

    expect(apiFetchMock).toHaveBeenCalledWith('/api/books/wrong_words_3/chapters/wrong_words_3_m/progress', {
      method: 'POST',
      body: expect.stringContaining('"current_index":169'),
    })
    const body = JSON.parse((apiFetchMock.mock.calls[0][1] as { body: string }).body)
    expect(body).toMatchObject({
      mode: 'quickmemory',
      current_index: 169,
      correct_count: 60,
      wrong_count: 30,
      is_completed: true,
      words_learned: 169,
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
        mode: 'dictation',
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
