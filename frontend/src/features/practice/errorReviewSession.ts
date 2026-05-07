import type { Word } from './types'

export type ErrorReviewRoundResults = Record<string, boolean>

export function updateErrorReviewRoundResults(
  results: ErrorReviewRoundResults,
  word: string,
  wasCorrect: boolean,
): ErrorReviewRoundResults {
  const key = word.trim().toLowerCase()
  if (!key) return results

  return {
    ...results,
    [key]: wasCorrect,
  }
}

export function buildNextErrorReviewWords(
  vocabulary: Word[],
  results: ErrorReviewRoundResults,
): Word[] {
  return vocabulary.filter(word => results[word.word.trim().toLowerCase()] === false)
}
