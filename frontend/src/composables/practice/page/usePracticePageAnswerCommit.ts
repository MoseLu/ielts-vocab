import { useCallback, type Dispatch, type MutableRefObject, type SetStateAction } from 'react'
import { recordModeAnswer } from '../../../hooks/useAIChat'
import { recordWordResult } from '../../../lib/smartMode'
import type { PracticeMode, SmartDimension, Word, WordStatuses } from '../../../features/practice/types'

type MasteryDimension = SmartDimension | 'speaking'
type MasteryResult = 'correct' | 'wrong' | 'skipped'

export interface SubmitPracticeWordMasteryInput {
  dimension: MasteryDimension
  analyticsMode: PracticeMode
  passed: boolean
  result: MasteryResult
  attemptIndex: number
  recordEbbinghaus?: boolean
}

export function usePracticePageAnswerCommit({
  currentWord,
  correctCount,
  wrongCount,
  queue,
  queueIndex,
  prepareSessionForLearningAction,
  registerAnsweredWord,
  syncCurrentSessionSnapshot,
  saveProgress,
  setCorrectCount,
  setWrongCount,
  setWordStatuses,
  sessionCorrectRef,
  sessionWrongRef,
  goNext,
  saveWrongWord,
  recordErrorReviewOutcome,
  submitPracticeWordMastery,
}: {
  currentWord: Word | undefined
  correctCount: number
  wrongCount: number
  queue: number[]
  queueIndex: number
  prepareSessionForLearningAction: () => Promise<void>
  registerAnsweredWord: (word: string) => void
  syncCurrentSessionSnapshot: (activeAt?: number) => void
  saveProgress: (correct: number, wrong: number, options?: { advanceToNext?: boolean }) => void
  setCorrectCount: (value: number) => void
  setWrongCount: (value: number) => void
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  sessionCorrectRef: MutableRefObject<number>
  sessionWrongRef: MutableRefObject<number>
  goNext: (wasCorrect: boolean) => Promise<void>
  saveWrongWord: (word: Word) => void
  recordErrorReviewOutcome: (word: Word, wasCorrect: boolean) => void
  submitPracticeWordMastery: (input: SubmitPracticeWordMasteryInput) => void
}) {
  return useCallback(async (
    isCorrect: boolean,
    {
      dimension,
      analyticsMode,
      advanceToNext = true,
      completionDelayMs = 1200,
      recordEbbinghaus = true,
      result,
    }: {
      dimension: MasteryDimension
      analyticsMode: PracticeMode
      advanceToNext?: boolean
      completionDelayMs?: number
      recordEbbinghaus?: boolean
      result?: MasteryResult
    },
  ) => {
    await prepareSessionForLearningAction()

    const nextCorrect = isCorrect ? correctCount + 1 : correctCount
    const nextWrong = isCorrect ? wrongCount : wrongCount + 1
    const attemptIndex = sessionCorrectRef.current + sessionWrongRef.current

    setCorrectCount(nextCorrect)
    setWrongCount(nextWrong)
    if (isCorrect) sessionCorrectRef.current += 1
    else sessionWrongRef.current += 1

    if (currentWord) {
      registerAnsweredWord(currentWord.word)
    }
    syncCurrentSessionSnapshot(Date.now())
    saveProgress(nextCorrect, nextWrong, { advanceToNext })
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: isCorrect ? 'correct' : 'wrong' }))

    if (currentWord) {
      submitPracticeWordMastery({
        dimension,
        analyticsMode,
        passed: isCorrect,
        result: result ?? (isCorrect ? 'correct' : 'wrong'),
        attemptIndex,
        recordEbbinghaus,
      })
      if (dimension !== 'speaking') {
        recordWordResult(currentWord.word, dimension, isCorrect)
      }
      if (!isCorrect) saveWrongWord(currentWord)
      recordErrorReviewOutcome(currentWord, isCorrect)
    }

    recordModeAnswer(analyticsMode, isCorrect)

    if (!advanceToNext) return
    window.setTimeout(() => { void goNext(isCorrect) }, completionDelayMs)
  }, [
    correctCount,
    currentWord,
    goNext,
    prepareSessionForLearningAction,
    queue,
    queueIndex,
    recordErrorReviewOutcome,
    registerAnsweredWord,
    saveProgress,
    saveWrongWord,
    submitPracticeWordMastery,
    syncCurrentSessionSnapshot,
    wrongCount,
    setCorrectCount,
    setWrongCount,
    setWordStatuses,
    sessionCorrectRef,
    sessionWrongRef,
  ])
}
