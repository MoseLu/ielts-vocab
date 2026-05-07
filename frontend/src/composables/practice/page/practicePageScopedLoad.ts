import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { LastState, PracticeMode, ProgressData, Word, WordStatuses } from '../../../features/practice/types'
import { loadSmartStats, buildSmartQueue } from '../../../lib/smartMode'
import { shuffleArray } from '../../../features/practice/practiceOptions'
import {
  buildWrongWordsQueue,
  createResetProgressState,
  filterVocabularyForMode,
} from '../../../features/practice/practiceSessionHelpers'
import {
  resolvePracticeGroupWindow,
  sliceQueueForPracticeGroup,
  type PracticeGroupWindow,
} from './practicePageGrouping'

interface ScopedLoadStateRef {
  key: string | null
  generation: number
}

interface ResolvePracticeWordsForModeOptions {
  rawWords: Word[]
  mode?: PracticeMode
  isCustomPracticeScope: boolean
  setNoListeningPresets: Dispatch<SetStateAction<boolean>>
  onListeningModeFallback: () => void
}

export function resolvePracticeWordsForMode({
  rawWords,
  mode,
  isCustomPracticeScope,
  setNoListeningPresets,
  onListeningModeFallback,
}: ResolvePracticeWordsForModeOptions): Word[] | null {
  const words = filterVocabularyForMode(rawWords, mode)
  const listeningUnavailable = mode === 'listening' && words.length === 0 && rawWords.length > 0

  if (listeningUnavailable && isCustomPracticeScope) {
    setNoListeningPresets(false)
    onListeningModeFallback()
    return null
  }

  setNoListeningPresets(listeningUnavailable)
  return words
}

interface ApplyScopedWordsLoadOptions {
  words: Word[]
  progress: ProgressData | null
  chapterId: string | null
  mode?: PracticeMode
  shuffle?: boolean
  groupSize?: number | null
  scopedLoadKey: string | null
  scopedLoadGeneration: number
  canApplyScopedLoad: () => boolean
  lastAppliedScopedLoadRef: MutableRefObject<ScopedLoadStateRef>
  scopedQueueWordsCacheRef: MutableRefObject<Record<string, string[]>>
  queueRef: MutableRefObject<number[]>
  vocabRef: MutableRefObject<Word[]>
  chapterGroupStartRef: MutableRefObject<number>
  chapterQueueWordsRef: MutableRefObject<string[]>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  setVocabulary: Dispatch<SetStateAction<Word[]>>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  setPracticeGroup: Dispatch<SetStateAction<PracticeGroupWindow | null>>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
}

export function applyScopedWordsLoad({
  words,
  progress,
  chapterId,
  mode,
  shuffle,
  groupSize,
  scopedLoadKey,
  scopedLoadGeneration,
  canApplyScopedLoad,
  lastAppliedScopedLoadRef,
  scopedQueueWordsCacheRef,
  queueRef,
  vocabRef,
  chapterGroupStartRef,
  chapterQueueWordsRef,
  wordsLearnedBaselineRef,
  uniqueAnsweredRef,
  setVocabulary,
  setQueue,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setWordStatuses,
  setResumeProgress,
  setPracticeGroup,
  beginSession,
}: ApplyScopedWordsLoadOptions) {
  const cachedQueueWords = scopedLoadKey != null
    ? scopedQueueWordsCacheRef.current[scopedLoadKey]
    : undefined
  const previousQueueWords = lastAppliedScopedLoadRef.current.key === scopedLoadKey
    ? queueRef.current
      .map(index => vocabRef.current[index]?.word)
      .filter((word): word is string => Boolean(word))
    : []
  const fullQueue = buildWrongWordsQueue(words, progress?.queue_words)
    ?? (cachedQueueWords?.length ? buildWrongWordsQueue(words, cachedQueueWords) : null)
    ?? (previousQueueWords.length ? buildWrongWordsQueue(words, previousQueueWords) : null)
    ?? buildModeQueue(words, mode, shuffle)
  const fullQueueWords = fullQueue
    .map(index => words[index]?.word)
    .filter((word): word is string => Boolean(word))
  const normalizedProgress = normalizeProgressForQueue(progress, fullQueue.length)
  const currentIndex = normalizedProgress?.is_completed ? 0 : (normalizedProgress?.current_index ?? 0)
  const practiceGroup = chapterId
    ? resolvePracticeGroupWindow(fullQueue.length, groupSize ?? null, currentIndex)
    : null
  const nextQueue = sliceQueueForPracticeGroup(fullQueue, practiceGroup)

  if (scopedLoadKey != null) {
    scopedQueueWordsCacheRef.current[scopedLoadKey] = fullQueueWords
  }

  if (!canApplyScopedLoad()) return

  queueRef.current = nextQueue
  chapterGroupStartRef.current = practiceGroup?.start ?? 0
  chapterQueueWordsRef.current = chapterId ? fullQueueWords : []
  setPracticeGroup(practiceGroup)
  setVocabulary(words)
  vocabRef.current = words
  setQueue(nextQueue)
  resetScopedProgress({
    progress: normalizedProgress,
    words,
    chapterId,
    queueLength: nextQueue.length,
    groupStart: practiceGroup?.start ?? 0,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    setResumeProgress,
    setQueueIndex,
    setCorrectCount,
    setWrongCount,
    setPreviousWord,
    setLastState,
    setWordStatuses,
  })
  lastAppliedScopedLoadRef.current = {
    key: scopedLoadKey,
    generation: scopedLoadGeneration,
  }
  beginSession()
}

export function isProgressCompleteForQueue(progress: ProgressData | null, queueLength: number): boolean {
  if (!progress?.is_completed) return false
  const safeQueueLength = Math.max(0, Math.floor(queueLength))
  if (safeQueueLength <= 0) return true

  const currentIndex = Number(progress.current_index)
  if (Number.isFinite(currentIndex) && currentIndex >= safeQueueLength) return true

  const wordsLearned = Number(progress.words_learned)
  if (Number.isFinite(wordsLearned) && wordsLearned >= safeQueueLength) return true

  const answeredWords = Array.isArray(progress.answered_words) ? progress.answered_words.length : 0
  return answeredWords >= safeQueueLength
}

function normalizeProgressForQueue(
  progress: ProgressData | null,
  queueLength: number,
): ProgressData | null {
  if (!progress) return null
  return {
    ...progress,
    is_completed: isProgressCompleteForQueue(progress, queueLength),
  }
}

function buildModeQueue(words: Word[], mode?: PracticeMode, shuffle?: boolean) {
  const indices = Array.from({ length: words.length }, (_, index) => index)
  if (mode === 'smart') {
    return buildSmartQueue(words.map(word => word.word), loadSmartStats())
  }

  return shuffle !== false ? shuffleArray(indices) : indices
}

interface ResetScopedProgressOptions {
  progress: ProgressData | null
  words: Word[]
  chapterId: string | null
  queueLength: number
  groupStart: number
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
}

function resetScopedProgress({
  progress,
  words,
  chapterId,
  queueLength,
  groupStart,
  wordsLearnedBaselineRef,
  uniqueAnsweredRef,
  setResumeProgress,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setWordStatuses,
}: ResetScopedProgressOptions) {
  if (!progress) {
    setResumeProgress(null)
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    wordsLearnedBaselineRef.current = 0
    uniqueAnsweredRef.current = new Set()
    return
  }

  const restored = createResetProgressState(queueLength, {
    ...progress,
    current_index: Math.max(0, progress.current_index - groupStart),
  }, chapterId, words.length)
  setQueueIndex(restored.queueIndex)
  setCorrectCount(restored.correctCount)
  setWrongCount(restored.wrongCount)
  setPreviousWord(null)
  setLastState(null)
  setWordStatuses({})
  setResumeProgress(progress.is_completed ? null : progress)
  wordsLearnedBaselineRef.current = restored.wordsLearnedBaseline
  uniqueAnsweredRef.current = restored.answeredWords
}
