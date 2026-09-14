import { useCallback, type Dispatch, type SetStateAction } from 'react'
import {
  buildProgressSnapshot,
  buildQuickMemorySyncRecord,
  buildWrongWordRecord,
  evaluatePracticeAnswer,
  updateErrorReviewRoundResults,
  type ErrorReviewRoundResults,
  type MobileWord,
  type PracticeMode,
  type PracticeQueueSource,
  type SmartPracticeDimension,
} from '@ielts-vocab/app-core'
import { syncQuickMemory, syncWrongWord } from '../../../api/learnerApi'
import type { NavigateOptions } from '../../../navigation/types'
import { persistErrorReviewProgress } from './errorReviewProgressStorage'
import { buildDictationFeedback } from './practiceFeedback'
import { completePracticeSession, persistPracticeSessionProgress } from './practiceSessionLifecycle'
import { practiceSessionDependencies } from './practiceSessionLifecycleRuntime'

type PracticeProgressBaseline = {
  correctCount: number
  wrongCount: number
}

export function usePracticeAnswerSubmission(params: {
  activeMode: PracticeMode
  bookId: string
  chapterBaselineRef: { current: PracticeProgressBaseline }
  chapterId?: string | number | null
  correctCount: number
  currentWord?: MobileWord
  errorReviewRound: number
  errorRoundResults: ErrorReviewRoundResults
  index: number
  mode: PracticeMode
  options?: NavigateOptions
  playWord: (source?: 'auto' | 'manual' | 'radio') => Promise<void>
  queue: MobileWord[]
  queueSource: PracticeQueueSource
  recordSmartAnswer: (params: {
    bookId?: string | null
    chapterId?: string | number | null
    correct: boolean
    dimension: SmartPracticeDimension
    word: MobileWord
  }) => Promise<void>
  setAnswer: (answer: string) => void
  setCorrectCount: (count: number) => void
  setErrorRoundResults: Dispatch<SetStateAction<ErrorReviewRoundResults>>
  setFeedback: (message: string) => void
  setIndex: (index: number) => void
  setWrongCount: (count: number) => void
  smartDimension: SmartPracticeDimension
  startedAtRef: { current: number }
  wrongCount: number
}) {
  return useCallback(async (value: string) => {
    if (!params.currentWord) return
    const currentSmartDimension = params.mode === 'smart' ? params.smartDimension : undefined
    const result = evaluatePracticeAnswer(params.currentWord, params.mode, value, { smartDimension: currentSmartDimension })
    if (params.mode === 'follow' && !value.trim()) {
      params.setFeedback(result.feedback)
      return
    }

    const nextCorrect = params.correctCount + (result.correct ? 1 : 0)
    const nextWrong = params.wrongCount + (result.correct ? 0 : 1)
    const nextIndex = params.index + 1
    const nextErrorRoundResults = params.mode === 'errors'
      ? updateErrorReviewRoundResults(params.errorRoundResults, params.currentWord.word, result.correct)
      : params.errorRoundResults

    params.setCorrectCount(nextCorrect)
    params.setWrongCount(nextWrong)
    if (params.mode === 'errors') params.setErrorRoundResults(nextErrorRoundResults)
    params.setFeedback(params.activeMode === 'dictation' && !result.correct
      ? buildDictationFeedback(value, result.expected)
      : result.feedback)
    params.setAnswer('')

    if (params.activeMode === 'dictation' && !result.correct) void params.playWord('auto')
    if (params.mode === 'smart' && currentSmartDimension) {
      await params.recordSmartAnswer({
        bookId: params.bookId,
        chapterId: params.chapterId,
        correct: result.correct,
        dimension: currentSmartDimension,
        word: params.currentWord,
      })
    }
    if (!result.correct || value === 'unknown') {
      await syncWrongWord(buildWrongWordRecord(params.currentWord, params.mode, currentSmartDimension)).catch(() => undefined)
    }
    if (params.mode === 'quickmemory' || params.mode === 'test') {
      await syncQuickMemory(buildQuickMemorySyncRecord(params.currentWord, value === 'known')).catch(() => undefined)
    }

    const snapshot = buildProgressSnapshot({
      correctCount: nextCorrect,
      currentIndex: nextIndex,
      queue: params.queue,
      wrongCount: nextWrong,
    })
    const persistedSnapshot = await persistPracticeSessionProgress({
      bookId: params.bookId,
      chapterBaseline: params.chapterBaselineRef.current,
      chapterId: params.chapterId,
      dependencies: practiceSessionDependencies,
      mode: params.mode,
      queueSource: params.queueSource,
      snapshot,
    }).catch(() => null)
    if (snapshot.isCompleted) {
      await completePracticeSession({
        bookId: params.bookId,
        chapterId: params.chapterId,
        dependencies: practiceSessionDependencies,
        durationSeconds: Math.round((Date.now() - params.startedAtRef.current) / 1000),
        mode: params.mode,
        queueSource: params.queueSource,
        snapshot: persistedSnapshot ?? snapshot,
        wordCount: params.queue.length,
      }).catch(() => undefined)
    }
    if (params.queueSource === 'errors') {
      await persistErrorReviewProgress({
        correct: nextCorrect,
        current: nextIndex,
        mode: params.mode,
        options: params.options,
        results: nextErrorRoundResults,
        round: params.errorReviewRound,
        wrong: nextWrong,
        words: params.queue,
      })
    }
    params.setIndex(nextIndex)
  }, [params])
}
