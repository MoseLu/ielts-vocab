import {
  CORE_STORAGE_KEYS,
  buildErrorReviewProgress,
  isErrorReviewProgressForQueue,
  readJson,
  writeJson,
  type ErrorReviewRoundResults,
  type MobileErrorReviewProgress,
  type MobileWord,
  type MobileWrongWordFilters,
  type PracticeMode,
} from '@ielts-vocab/app-core'
import type { NavigateOptions } from '../../../navigation/types'
import { asyncAppStorage } from '../../../storage/mobileStorage'

export function getErrorReviewFilters(options?: NavigateOptions): MobileWrongWordFilters {
  return {
    scope: 'pending',
    ...options?.wrongWordFilters,
    dimension: options?.wrongWordDimension ?? options?.wrongWordFilters?.dimension,
    mode: options?.wrongWordMode ?? options?.wrongWordFilters?.mode,
  }
}

export async function hydrateErrorReviewProgress(words: MobileWord[], mode: PracticeMode) {
  const saved = await readJson<MobileErrorReviewProgress | null>(
    asyncAppStorage,
    CORE_STORAGE_KEYS.wrongWordReview,
    null,
  )
  return isErrorReviewProgressForQueue(saved, words, mode) && !saved.isCompleted ? saved : null
}

export async function persistErrorReviewProgress(params: {
  correct: number
  current: number
  mode: PracticeMode
  options?: NavigateOptions
  results: ErrorReviewRoundResults
  round: number
  wrong: number
  words: MobileWord[]
}) {
  await writeJson(
    asyncAppStorage,
    CORE_STORAGE_KEYS.wrongWordReview,
    buildErrorReviewProgress({
      correctCount: params.correct,
      currentIndex: params.current,
      filters: getErrorReviewFilters(params.options),
      mode: params.mode,
      queue: params.words,
      results: params.results,
      round: params.round,
      wrongCount: params.wrong,
    }),
  ).catch(() => undefined)
}
