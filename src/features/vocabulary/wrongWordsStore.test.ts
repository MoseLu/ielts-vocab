import {
  addWrongWordToList,
  applyWrongWordReviewResult,
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
      review_streak: 0,
      ...overrides,
    }
  }

  it('keeps the word in the wrong-word list after reaching the error-review target', () => {
    const words = [makeWord({ review_streak: WRONG_WORD_ERROR_REVIEW_TARGET - 1 })]

    const result = applyWrongWordReviewResult(words, 'alpha', true)

    expect(result.removed).toBeNull()
    expect(result.words).toEqual([
      expect.objectContaining({
        word: 'alpha',
        review_streak: WRONG_WORD_ERROR_REVIEW_TARGET,
      }),
    ])
  })

  it('resets the mastery streak when the learner gets the word wrong again', () => {
    const words = [makeWord({ review_streak: 1 })]

    const result = applyWrongWordReviewResult(words, 'alpha', false)

    expect(result.removed).toBeNull()
    expect(result.words).toEqual([
      expect.objectContaining({
        word: 'alpha',
        review_streak: 0,
      }),
    ])
  })

  it('tracks the first wrong date, increments wrong_count, and resets review_streak when the same word is added again', () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-03-31T08:30:00+08:00'))

    const firstAdd = addWrongWordToList([], {
      word: 'alpha',
      phonetic: '/a/',
      pos: 'n.',
      definition: 'alpha definition',
      review_streak: 1,
    })

    vi.setSystemTime(new Date('2026-04-02T10:00:00+08:00'))

    const secondAdd = addWrongWordToList(firstAdd, {
      word: 'alpha',
      phonetic: '/a/',
      pos: 'n.',
      definition: 'alpha definition',
      review_streak: 2,
    })

    expect(firstAdd).toEqual([
      expect.objectContaining({
        word: 'alpha',
        wrong_count: 1,
        review_streak: 0,
        first_wrong_at: expect.any(String),
      }),
    ])
    expect(secondAdd).toEqual([
      expect.objectContaining({
        word: 'alpha',
        wrong_count: 2,
        review_streak: 0,
        first_wrong_at: firstAdd[0].first_wrong_at,
      }),
    ])

    vi.useRealTimers()
  })
})
