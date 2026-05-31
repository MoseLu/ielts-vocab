import { act, renderHook } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { Word } from '../../../features/practice/types'
import { usePracticeChapterGroupControls } from './usePracticeChapterGroupControls'

function word(value: string): Word {
  return { word: value, phonetic: '', pos: '', definition: value }
}

describe('usePracticeChapterGroupControls', () => {
  it('carries completed group counts into the next chapter progress save', () => {
    const chapterCorrectBaselineRef = { current: 4 }
    const chapterWrongBaselineRef = { current: 1 }
    const setQueue = vi.fn()
    const setQueueIndex = vi.fn()
    const beginSession = vi.fn()

    const { result } = renderHook(() => usePracticeChapterGroupControls({
      bookId: 'wrong_words_3',
      chapterId: 'wrong_words_3_m',
      practiceGroup: { start: 0, end: 2, total: 4, groupSize: 2 },
      vocabulary: [word('mock'), word('model'), word('module'), word('modify')],
      queueRef: { current: [0, 1] },
      chapterGroupStartRef: { current: 0 },
      chapterQueueWordsRef: { current: ['mock', 'model', 'module', 'modify'] },
      correctCountRef: { current: 2 },
      wrongCountRef: { current: 0 },
      chapterCorrectBaselineRef,
      chapterWrongBaselineRef,
      completedSessionDurationSecondsRef: { current: 12 },
      beginSession,
      setPracticeGroup: vi.fn(),
      setQueue,
      setQueueIndex,
      setCorrectCount: vi.fn(),
      setWrongCount: vi.fn(),
      setPreviousWord: vi.fn(),
      setLastState: vi.fn(),
      setWordStatuses: vi.fn(),
      setSelectedAnswer: vi.fn(),
      setWrongSelections: vi.fn(),
      setShowResult: vi.fn(),
      setSpellingInput: vi.fn(),
      setSpellingResult: vi.fn(),
      setSpellingFeedbackLocked: vi.fn(),
      setSpellingFeedbackDismissing: vi.fn(),
      setSpellingFeedbackSnapshot: vi.fn(),
    }))

    act(() => {
      result.current()
    })

    expect(chapterCorrectBaselineRef.current).toBe(6)
    expect(chapterWrongBaselineRef.current).toBe(1)
    expect(setQueue).toHaveBeenCalledWith([2, 3])
    expect(setQueueIndex).toHaveBeenCalledWith(0)
    expect(beginSession).toHaveBeenCalledWith({ bookId: 'wrong_words_3', chapterId: 'wrong_words_3_m' })
  })
})
