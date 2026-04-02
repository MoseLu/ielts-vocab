import {
  addWrongWordToList,
  applyWrongWordReviewResult,
  getWrongWordDimensionHistoryWrong,
  isWrongWordPendingInDimension,
  WRONG_WORD_ERROR_REVIEW_TARGET,
  type WrongWordRecord,
} from './wrongWordsStore'
import { vi } from 'vitest'

describe('wrongWordsStore review mastery', () => {
  function makeWord(overrides: Partial<WrongWordRecord> = {}): WrongWordRecord {
    return {
      word: 'alpha',
      phonetic: '/a/',
      pos: 'n.',
      definition: 'alpha definition',
      wrong_count: 3,
      recognition_pass_streak: 0,
      ...overrides,
    }
  }

  it('keeps the word in the wrong-word list after reaching the error-review target', () => {
    const words = [makeWord({ recognition_pass_streak: WRONG_WORD_ERROR_REVIEW_TARGET - 1 })]

    const result = applyWrongWordReviewResult(words, 'alpha', true, 'recognition')

    expect(result.removed).toBeNull()
    expect(result.words).toEqual([
      expect.objectContaining({
        word: 'alpha',
        recognition_pass_streak: WRONG_WORD_ERROR_REVIEW_TARGET,
        recognition_pending: false,
      }),
    ])
  })

  it('resets the mastery streak when the learner gets the word wrong again', () => {
    const words = [makeWord({ recognition_pass_streak: 1 })]

    const result = applyWrongWordReviewResult(words, 'alpha', false, 'recognition')

    expect(result.removed).toBeNull()
    expect(result.words).toEqual([
      expect.objectContaining({
        word: 'alpha',
        recognition_pass_streak: 0,
        recognition_pending: true,
      }),
    ])
  })

  it('tracks the first wrong date, increments history, and resets recognition progress when the same word is added again', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-31T08:30:00+08:00'))

    const firstAdd = addWrongWordToList([], {
      word: 'alpha',
      phonetic: '/a/',
      pos: 'n.',
      definition: 'alpha definition',
    })

    vi.setSystemTime(new Date('2026-04-02T10:00:00+08:00'))

    const secondAdd = addWrongWordToList(firstAdd, {
      word: 'alpha',
      phonetic: '/a/',
      pos: 'n.',
      definition: 'alpha definition',
    })

    expect(firstAdd).toEqual([
      expect.objectContaining({
        word: 'alpha',
        wrong_count: 1,
        recognition_pass_streak: 0,
        recognition_pending: true,
        first_wrong_at: expect.any(String),
      }),
    ])
    expect(secondAdd).toEqual([
      expect.objectContaining({
        word: 'alpha',
        wrong_count: 2,
        recognition_pass_streak: 0,
        recognition_pending: true,
        first_wrong_at: firstAdd[0].first_wrong_at,
      }),
    ])
    expect(getWrongWordDimensionHistoryWrong(secondAdd[0], 'recognition')).toBe(2)
    expect(isWrongWordPendingInDimension(secondAdd[0], 'recognition')).toBe(true)

    vi.useRealTimers()
  })
})
