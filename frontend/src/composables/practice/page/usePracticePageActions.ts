import { useCallback } from 'react'
import { recordWordResult } from '../../../lib/smartMode'
import { recordModeAnswer } from '../../../hooks/useAIChat'
import type {
  PracticeMode,
  SmartDimension,
  SpellingSubmitSource,
} from '../../../components/practice/types'
import { normalizeWordAnswer } from '../../../components/practice/utils'
import type {
  UsePracticePageActionsParams,
  UsePracticePageActionsResult,
} from './usePracticePageActions.types'
import { usePracticePageWrongWordActions } from './usePracticePageWrongWordActions'
import { usePracticeWordMasterySubmitter } from './usePracticeWordMasterySubmitter'

export function usePracticePageActions({
  user,
  userId,
  mode,
  smartDimension,
  bookId,
  chapterId,
  currentDay,
  currentWord,
  queue,
  queueIndex,
  correctCount,
  wrongCount,
  correctIndex,
  options,
  wrongSelections,
  choiceOptionsReady,
  showResult,
  spellingInput,
  spellingResult,
  errorMode,
  settings,
  navigate,
  showToast,
  playWord,
  saveProgress,
  clearSpellingRetryTimer,
  clearSpellingFeedbackDismissTimer,
  prepareSessionForLearningAction,
  completeCurrentSession,
  registerAnsweredWord,
  syncCurrentSessionSnapshot,
  lastState,
  setLastState,
  setPreviousWord,
  previousWord,
  setSelectedAnswer,
  setWrongSelections,
  setShowResult,
  setSpellingInput,
  setSpellingResult,
  setSpellingFeedbackLocked,
  setSpellingFeedbackDismissing,
  setSpellingFeedbackSnapshot,
  setQueue,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setWordStatuses,
  spellingRetryTimerRef,
  sessionIdRef,
  sessionCorrectRef,
  sessionWrongRef,
  completedSessionDurationSecondsRef,
  errorRoundResultsRef,
}: UsePracticePageActionsParams): UsePracticePageActionsResult {
  const {
    saveWrongWord,
    handleQuickMemoryRecordChange,
    recordErrorReviewOutcome,
  } = usePracticePageWrongWordActions({
    user,
    userId,
    mode,
    smartDimension,
    bookId,
    chapterId,
    errorMode,
    showToast,
    errorRoundResultsRef,
  })
  const submitPracticeWordMastery = usePracticeWordMasterySubmitter({
    userId,
    bookId,
    chapterId,
    currentDay,
    currentWord,
    errorMode,
    sessionIdRef,
  })

  const goNext = useCallback(async (wasCorrect: boolean) => {
    setLastState({ qi: queueIndex, cc: correctCount, wc: wrongCount, prevWord: previousWord })
    setPreviousWord(currentWord ?? null)
    setSelectedAnswer(null)
    setWrongSelections([])
    setShowResult(false)
    setSpellingInput('')
    setSpellingResult(null)
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)

    if (!wasCorrect && settings.repeatWrong !== false) {
      setQueue(prev => [...prev, queue[queueIndex]])
    }

    if (queueIndex + 1 >= queue.length) {
      const totalDurationSeconds = await completeCurrentSession()
      completedSessionDurationSecondsRef.current = totalDurationSeconds
      if (errorMode || chapterId) {
        setQueueIndex(queue.length)
        return
      }
      navigate('/plan')
      return
    }

    setQueueIndex(prev => prev + 1)
  }, [
    chapterId,
    completeCurrentSession,
    correctCount,
    currentWord,
    errorMode,
    navigate,
    previousWord,
    queue,
    queueIndex,
    completedSessionDurationSecondsRef,
    setLastState,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    setSelectedAnswer,
    setShowResult,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    setWrongSelections,
    settings.repeatWrong,
  ])

  const goBack = useCallback(() => {
    if (!lastState) return
    setQueueIndex(lastState.qi)
    setCorrectCount(lastState.cc)
    setWrongCount(lastState.wc)
    setPreviousWord(lastState.prevWord)
    setLastState(null)
    setSelectedAnswer(null)
    setWrongSelections([])
    setShowResult(false)
    setSpellingInput('')
    setSpellingResult(null)
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)
  }, [
    lastState,
    setCorrectCount,
    setLastState,
    setPreviousWord,
    setQueueIndex,
    setSelectedAnswer,
    setShowResult,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    setWrongCount,
    setWrongSelections,
  ])

  const commitAnswerResult = useCallback(async (
    isCorrect: boolean,
    {
      dimension,
      analyticsMode,
      advanceToNext = true,
      completionDelayMs = 1200,
      recordEbbinghaus = true,
    }: {
      dimension: SmartDimension
      analyticsMode: PracticeMode
      advanceToNext?: boolean
      completionDelayMs?: number
      recordEbbinghaus?: boolean
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
        result: isCorrect ? 'correct' : 'wrong',
        attemptIndex,
        recordEbbinghaus,
      })
      recordWordResult(currentWord.word, dimension, isCorrect)
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

  const handleOptionSelect = useCallback(async (idx: number) => {
    if (!choiceOptionsReady || showResult) return
    const dimension: SmartDimension = mode === 'smart' ? smartDimension : 'listening'
    const shouldReplayListeningPrompt = Boolean(
      currentWord
      && (mode === 'listening' || (mode === 'smart' && smartDimension === 'listening')),
    )
    const selectedOptionWord = options[idx]?.word?.trim()

    if (idx !== correctIndex) {
      if (wrongSelections.includes(idx)) return
      setSelectedAnswer(idx)
      setWrongSelections(prev => [...prev, idx])
      if (wrongSelections.length === 0) {
        await commitAnswerResult(false, {
          dimension,
          analyticsMode: mode ?? 'smart',
          advanceToNext: false,
        })
      }
      if (shouldReplayListeningPrompt && currentWord) {
        playWord(selectedOptionWord || currentWord.word)
      }
      return
    }

    setSelectedAnswer(idx)
    setShowResult(true)
    await commitAnswerResult(true, {
      dimension,
      analyticsMode: mode ?? 'smart',
      recordEbbinghaus: wrongSelections.length === 0,
    })
  }, [
    choiceOptionsReady,
    commitAnswerResult,
    correctIndex,
    currentWord,
    mode,
    options,
    playWord,
    setSelectedAnswer,
    setShowResult,
    setWrongSelections,
    showResult,
    smartDimension,
    wrongSelections,
  ])

  const handleSpellingSubmit = useCallback(async (source: SpellingSubmitSource = 'button') => {
    if (spellingResult || !currentWord) return
    const isCorrect = normalizeWordAnswer(spellingInput) === normalizeWordAnswer(currentWord.word)
    clearSpellingRetryTimer()
    clearSpellingFeedbackDismissTimer()
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(isCorrect ? null : spellingInput)
    setSpellingResult(isCorrect ? 'correct' : 'wrong')
    await commitAnswerResult(isCorrect, {
      dimension: 'dictation',
      analyticsMode: mode ?? 'dictation',
      advanceToNext: isCorrect,
      completionDelayMs: 1500,
    })
    if (!isCorrect && source !== 'enter') {
      spellingRetryTimerRef.current = window.setTimeout(() => {
        setSpellingInput('')
        setSpellingResult(current => current === 'wrong' ? null : current)
        setSpellingFeedbackLocked(false)
        setSpellingFeedbackDismissing(false)
        setSpellingFeedbackSnapshot(null)
        spellingRetryTimerRef.current = null
      }, 3000)
      return
    }
    if (!isCorrect) {
      setSpellingFeedbackLocked(true)
    }
  }, [
    clearSpellingFeedbackDismissTimer,
    clearSpellingRetryTimer,
    commitAnswerResult,
    currentWord,
    mode,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    spellingInput,
    spellingResult,
    spellingRetryTimerRef,
  ])

  const handleMeaningRecallSubmit = useCallback(async (_source: SpellingSubmitSource = 'button') => {
    if (spellingResult || !currentWord) return
    const isCorrect = normalizeWordAnswer(spellingInput) === normalizeWordAnswer(currentWord.word)
    clearSpellingRetryTimer()
    clearSpellingFeedbackDismissTimer()
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)
    setSpellingResult(isCorrect ? 'correct' : 'wrong')
    await commitAnswerResult(isCorrect, {
      dimension: 'meaning',
      analyticsMode: mode ?? 'meaning',
    })
  }, [
    clearSpellingFeedbackDismissTimer,
    clearSpellingRetryTimer,
    commitAnswerResult,
    currentWord,
    mode,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingResult,
    spellingInput,
    spellingResult,
  ])

  const handleFollowReadEvaluated = useCallback(async (passed: boolean) => {
    if (!currentWord) return
    await prepareSessionForLearningAction()
    const attemptIndex = sessionCorrectRef.current + sessionWrongRef.current
    const nextCorrect = passed ? correctCount + 1 : correctCount
    const nextWrong = passed ? wrongCount : wrongCount + 1
    setCorrectCount(nextCorrect)
    setWrongCount(nextWrong)
    if (passed) sessionCorrectRef.current += 1
    else sessionWrongRef.current += 1
    registerAnsweredWord(currentWord.word)
    syncCurrentSessionSnapshot(Date.now())
    saveProgress(nextCorrect, nextWrong, { advanceToNext: false })
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: passed ? 'correct' : 'wrong' }))
    submitPracticeWordMastery({
      dimension: 'speaking',
      analyticsMode: 'follow',
      passed,
      result: passed ? 'correct' : 'wrong',
      attemptIndex,
      recordEbbinghaus: true,
    })
    if (!passed) saveWrongWord(currentWord)
    recordErrorReviewOutcome(currentWord, passed)
    recordModeAnswer('follow', passed)
  }, [
    correctCount,
    currentWord,
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
    setWordStatuses,
    setWrongCount,
    sessionCorrectRef,
    sessionWrongRef,
  ])

  const handleSkip = useCallback(async () => {
    if (!currentWord) return
    await prepareSessionForLearningAction()
    const dimension: SmartDimension = mode === 'smart'
      ? smartDimension
      : mode === 'dictation'
        ? 'dictation'
        : mode === 'listening'
          ? 'listening'
          : 'meaning'
    const hasPendingListeningMistake = wrongSelections.length > 0
      && (mode === 'listening' || (mode === 'smart' && smartDimension === 'listening'))

    if (hasPendingListeningMistake) {
      void goNext(false)
      return
    }

    const attemptIndex = sessionCorrectRef.current + sessionWrongRef.current
    saveWrongWord(currentWord)
    recordErrorReviewOutcome(currentWord, false)
    submitPracticeWordMastery({
      dimension,
      analyticsMode: mode ?? 'smart',
      passed: false,
      result: 'skipped',
      attemptIndex,
      recordEbbinghaus: true,
    })
    registerAnsweredWord(currentWord.word)
    const nextWrong = wrongCount + 1
    setWrongCount(nextWrong)
    saveProgress(correctCount, nextWrong)
    sessionWrongRef.current += 1
    syncCurrentSessionSnapshot(Date.now())
    recordModeAnswer(mode ?? 'smart', false)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: 'wrong' }))
    void goNext(false)
  }, [
    correctCount,
    currentWord,
    goNext,
    mode,
    prepareSessionForLearningAction,
    queue,
    queueIndex,
    recordErrorReviewOutcome,
    registerAnsweredWord,
    saveProgress,
    saveWrongWord,
    smartDimension,
    syncCurrentSessionSnapshot,
    submitPracticeWordMastery,
    wrongCount,
    wrongSelections.length,
    setWordStatuses,
    setWrongCount,
    sessionWrongRef,
  ])

  return {
    saveWrongWord,
    handleQuickMemoryRecordChange,
    recordErrorReviewOutcome,
    goBack,
    handleOptionSelect,
    handleSpellingSubmit,
    handleMeaningRecallSubmit,
    handleFollowReadEvaluated,
    handleSkip,
  }
}
