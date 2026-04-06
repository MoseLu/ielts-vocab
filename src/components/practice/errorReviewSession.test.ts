import type { Word } from './types'
import {
  buildNextErrorReviewWords,
  updateErrorReviewRoundResults,
} from './errorReviewSession'

describe('errorReviewSession', () => {
  const vocabulary: Word[] = [
    { word: 'alpha', phonetic: '/a/', pos: 'n.', definition: 'alpha definition' },
    { word: 'beta', phonetic: '/b/', pos: 'n.', definition: 'beta definition' },
    { word: 'gamma', phonetic: '/g/', pos: 'n.', definition: 'gamma definition' },
  ]

  it('keeps only the words answered wrong for the next round while preserving order', () => {
    let results = {}
    results = updateErrorReviewRoundResults(results, 'gamma', false)
    results = updateErrorReviewRoundResults(results, 'alpha', true)
    results = updateErrorReviewRoundResults(results, 'beta', false)

    const nextRoundWords = buildNextErrorReviewWords(vocabulary, results)

    expect(nextRoundWords.map(word => word.word)).toEqual(['beta', 'gamma'])
  })

  it('uses the latest answer when a word is retried in the same round', () => {
    let results = {}
    results = updateErrorReviewRoundResults(results, 'beta', false)
    results = updateErrorReviewRoundResults(results, 'beta', true)

    const nextRoundWords = buildNextErrorReviewWords(vocabulary, results)

    expect(nextRoundWords.map(word => word.word)).toEqual([])
  })
})
