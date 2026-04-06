import {
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_PENDING_REVIEW_TARGET,
  type WrongWordCollectionScope,
  type WrongWordDimension,
  type WrongWordDimensionState,
  type WrongWordInput,
  type WrongWordRecord,
} from './types'
import {
  applyDimensionStateClear,
  applyDimensionStateFailure,
  applyDimensionStateReviewResult,
  clampPassStreak,
  emptyDimensionState,
  isDimensionPendingState,
  mergeWrongWordLists,
  normalizeDimensionStates,
  normalizeWrongWord,
  updateWordWithDimensionMutation,
  withDerivedFields,
} from './core'

export function addWrongWordToList(
  words: WrongWordInput[],
  word: WrongWordInput,
  options: { dimension?: WrongWordDimension } = {},
): WrongWordRecord[] {
  const normalizedIncoming = normalizeWrongWord(word)
  if (!normalizedIncoming) return mergeWrongWordLists(words)

  const dimension = options.dimension ?? 'recognition'
  const nowIso = new Date().toISOString()
  const key = normalizedIncoming.word.toLowerCase()
  const existingWords = mergeWrongWordLists(words)
  let matched = false

  const nextWords = existingWords.map(existingWord => {
    if (existingWord.word.toLowerCase() !== key) return existingWord

    matched = true
    const nextStates = {
      ...(existingWord.dimension_states ?? normalizeDimensionStates(existingWord as WrongWordInput & Record<string, unknown>)),
    }
    nextStates[dimension] = applyDimensionStateFailure(nextStates[dimension] ?? emptyDimensionState(), nowIso)

    return withDerivedFields({
      ...existingWord,
      first_wrong_at: existingWord.first_wrong_at ?? nowIso,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })

  if (!matched) {
    const nextStates = {
      ...(normalizedIncoming.dimension_states ?? normalizeDimensionStates(normalizedIncoming as WrongWordInput & Record<string, unknown>)),
    }
    nextStates[dimension] = applyDimensionStateFailure(nextStates[dimension] ?? emptyDimensionState(), nowIso)

    nextWords.push(withDerivedFields({
      ...normalizedIncoming,
      first_wrong_at: normalizedIncoming.first_wrong_at ?? nowIso,
      updated_at: nowIso,
      dimension_states: nextStates,
    }))
  }

  return mergeWrongWordLists(nextWords)
}

export function removeWrongWordFromList(words: WrongWordInput[], wordToRemove: string): WrongWordRecord[] {
  const needle = wordToRemove.trim().toLowerCase()
  return mergeWrongWordLists(words).filter(word => word.word.toLowerCase() !== needle)
}

export function getWrongWordDimensionState(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): WrongWordDimensionState {
  const normalized = normalizeWrongWord(word as WrongWordInput)
  return normalized?.dimension_states?.[dimension] ?? emptyDimensionState()
}

export function getWrongWordDimensionHistoryWrong(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): number {
  return getWrongWordDimensionState(word, dimension).history_wrong
}

export function getWrongWordDimensionPassStreak(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): number {
  return getWrongWordDimensionState(word, dimension).pass_streak
}

export function isWrongWordPendingInDimension(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): boolean {
  return isDimensionPendingState(getWrongWordDimensionState(word, dimension))
}

export function hasWrongWordHistory(word: Partial<WrongWordRecord>): boolean {
  return WRONG_WORD_DIMENSIONS.some(dimension => getWrongWordDimensionHistoryWrong(word, dimension) > 0)
}

export function hasWrongWordPending(word: Partial<WrongWordRecord>): boolean {
  return WRONG_WORD_DIMENSIONS.some(dimension => isWrongWordPendingInDimension(word, dimension))
}

export function getWrongWordActiveCount(
  word: Partial<WrongWordRecord>,
  scope: WrongWordCollectionScope,
): number {
  const normalized = normalizeWrongWord(word as WrongWordInput)
  if (!normalized) return 0
  return scope === 'pending'
    ? normalized.pending_wrong_count ?? 0
    : normalized.wrong_count ?? 0
}

export function getWrongWordDimensionProgress(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
  masteryTarget = WRONG_WORD_PENDING_REVIEW_TARGET,
) {
  const streak = Math.min(getWrongWordDimensionPassStreak(word, dimension), masteryTarget)
  return {
    streak,
    target: masteryTarget,
    remaining: Math.max(0, masteryTarget - streak),
    pending: getWrongWordDimensionHistoryWrong(word, dimension) > 0 && streak < masteryTarget,
  }
}

export function getWrongWordReviewProgress(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension = 'meaning',
  masteryTarget = WRONG_WORD_PENDING_REVIEW_TARGET,
) {
  return getWrongWordDimensionProgress(word, dimension, masteryTarget)
}

export function applyWrongWordReviewResult(
  words: WrongWordInput[],
  reviewedWord: string,
  wasCorrect: boolean,
  dimension: WrongWordDimension = 'meaning',
) {
  const nextWords = updateWordWithDimensionMutation(words, reviewedWord, (word, nowIso) => {
    const state = getWrongWordDimensionState(word, dimension)
    if (state.history_wrong <= 0) return word

    const nextStates = {
      ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
      [dimension]: applyDimensionStateReviewResult(state, wasCorrect, nowIso),
    }

    return withDerivedFields({
      ...word,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })

  return {
    words: nextWords,
    removed: null,
  }
}

export function syncWrongWordDimensionPassStreak(
  words: WrongWordInput[],
  reviewedWord: string,
  dimension: WrongWordDimension,
  passStreak: number,
): WrongWordRecord[] {
  const clampedPassStreak = clampPassStreak(passStreak)

  return updateWordWithDimensionMutation(words, reviewedWord, (word, nowIso) => {
    const state = getWrongWordDimensionState(word, dimension)
    if (state.history_wrong <= 0) return word

    const nextStates = {
      ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
      [dimension]: {
        ...state,
        pass_streak: clampedPassStreak,
        last_pass_at: clampedPassStreak > 0 ? nowIso : state.last_pass_at,
      },
    }

    return withDerivedFields({
      ...word,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })
}

export function clearWrongWordPendingFromList(words: WrongWordInput[], targetWord: string): WrongWordRecord[] {
  return updateWordWithDimensionMutation(words, targetWord, (word, nowIso) => {
    const nextStates = {
      ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
    }

    for (const dimension of WRONG_WORD_DIMENSIONS) {
      nextStates[dimension] = applyDimensionStateClear(nextStates[dimension] ?? emptyDimensionState(), nowIso)
    }

    return withDerivedFields({
      ...word,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })
}

export function clearAllWrongWordPendingFromList(words: WrongWordInput[]): WrongWordRecord[] {
  const nowIso = new Date().toISOString()

  return mergeWrongWordLists(
    mergeWrongWordLists(words).map(word => {
      const nextStates = {
        ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
      }

      for (const dimension of WRONG_WORD_DIMENSIONS) {
        nextStates[dimension] = applyDimensionStateClear(nextStates[dimension] ?? emptyDimensionState(), nowIso)
      }

      return withDerivedFields({
        ...word,
        updated_at: nowIso,
        dimension_states: nextStates,
      })
    }),
  )
}
