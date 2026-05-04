import { describe, expect, it } from 'vitest'
import { isProgressCompleteForQueue } from './practicePageScopedLoad'

describe('practice page scoped load progress', () => {
  it('does not treat stale completed progress as complete after the word list grows', () => {
    expect(isProgressCompleteForQueue({
      current_index: 100,
      correct_count: 100,
      wrong_count: 0,
      is_completed: true,
      words_learned: 100,
      answered_words: Array.from({ length: 100 }, (_, index) => `word-${index}`),
    }, 320)).toBe(false)
  })

  it('keeps genuinely finished progress complete', () => {
    expect(isProgressCompleteForQueue({
      current_index: 320,
      correct_count: 320,
      wrong_count: 0,
      is_completed: true,
      words_learned: 320,
    }, 320)).toBe(true)
  })
})
