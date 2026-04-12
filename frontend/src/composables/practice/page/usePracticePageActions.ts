import { useCallback } from 'react'
import {
  recordWordResult,
  syncSmartStatsToBackend,
} from '../../../lib/smartMode'
import {
  logSession,
  recordModeAnswer,
  resolveStudySessionDurationSeconds,
} from '../../../hooks/useAIChat'
import type {
  PracticeMode,
  SmartDimension,
  SpellingSubmitSource,
} from '../../../components/practice/types'
import {
  normalizeWordAnswer,
} from '../../../components/practice/utils'
import type {
  UsePracticePageActionsParams,
  UsePracticePageActionsResult,
} from './usePracticePageActions.types'
import { usePracticePageWrongWordActions } from './usePracticePageWrongWordActions'

export function usePracticePageActions({
  user,
  userId,
  mode,
  smartDimension,
  bookId,
  chapterId,
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
  sessionCorrectRef,
  sessionWrongRef,
  sessionStartRef,
  sessionIdRef,
  sessionLoggedRef,
  completedSessionDurationSecondsRef,
  sessionUniqueWordsRef,
  sessionBookIdRef,
  sessionChapterIdRef,
  effectiveSessionModeRef,
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

  const goNext = useCallback((wasCorrect: boolean) => {
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
      const finalSessionCorrect = wasCorrect ? sessionCorrectRef.current + 1 : sessionCorrectRef.current
      const finalSessionWrong = wasCorrect ? sessionWrongRef.current : sessionWrongRef.current + 1
      const sessionStart = sessionStartRef.current
      const durationSeconds = resolveStudySessionDurationSeconds({
        sessionId: sessionIdRef.current,
        startedAt: sessionStart,
      })
      completedSessionDurationSecondsRef.current = durationSeconds
      sessionLoggedRef.current = true
      syncCurrentSessionSnapshot()
      logSession({
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        wordsStudied: sessionUniqueWordsRef.current.size,
        correctCount: finalSessionCorrect,
        wrongCount: finalSessionWrong,
        durationSeconds,
        startedAt: sessionStart,
        sessionId: sessionIdRef.current,
      })
      syncSmartStatsToBackend({
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        mode: effectiveSessionModeRef.current,
      })
      if (errorMode) {
        setQueueIndex(queue.length)
        return
      }
      if (sessionChapterIdRef.current) {
        setQueueIndex(queue.length)
        return
      }
      navigate('/plan')
      return
    }

    setQueueIndex(prev => prev + 1)
  }, [
    correctCount,
    currentWord,
    effectiveSessionModeRef,
    errorMode,
    navigate,
    previousWord,
    queue,
    queueIndex,
    completedSessionDurationSecondsRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionCorrectRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
    sessionUniqueWordsRef,
    sessionWrongRef,
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
    syncCurrentSessionSnapshot,
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
    wrongCount,
  ])

  const commitAnswerResult = useCallback((
    isCorrect: boolean,
    {
      dimension,
      analyticsMode,
      advanceToNext = true,
      completionDelayMs = 1200,
    }: {
      dimension: SmartDimension
      analyticsMode: PracticeMode
      advanceToNext?: boolean
      completionDelayMs?: number
    },
  ) => {
    const nextCorrect = isCorrect ? correctCount + 1 : correctCount
    const nextWrong = isCorrect ? wrongCount : wrongCount + 1

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
      recordWordResult(currentWord.word, dimension, isCorrect)
      if (!isCorrect) saveWrongWord(currentWord)
      recordErrorReviewOutcome(currentWord, isCorrect)
    }

    recordModeAnswer(analyticsMode, isCorrect)

    if (!advanceToNext) return
    window.setTimeout(() => goNext(isCorrect), completionDelayMs)
  }, [
    correctCount,
    currentWord,
    goNext,
    queue,
    queueIndex,
    recordErrorReviewOutcome,
    registerAnsweredWord,
    saveProgress,
    saveWrongWord,
    syncCurrentSessionSnapshot,
    wrongCount,
    setCorrectCount,
    setWrongCount,
    setWordStatuses,
    sessionCorrectRef,
    sessionWrongRef,
  ])

  const handleOptionSelect = useCallback((idx: number) => {
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
        commitAnswerResult(false, {
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
    commitAnswerResult(true, {
      dimension,
      analyticsMode: mode ?? 'smart',
    })
  }, [
    choiceOptionsReady,
    commitAnswerResult,
    correctIndex,
    mode,
    currentWord,
    options,
    playWord,
    showResult,
    smartDimension,
    wrongSelections,
    setSelectedAnswer,
    setShowResult,
    setWrongSelections,
  ])

  const handleSpellingSubmit = useCallback((source: SpellingSubmitSource = 'button') => {
    if (spellingResult || !currentWord) return
    const isCorrect = normalizeWordAnswer(spellingInput) === normalizeWordAnswer(currentWord.word)
    clearSpellingRetryTimer()
    clearSpellingFeedbackDismissTimer()
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(isCorrect ? null : spellingInput)
    setSpellingResult(isCorrect ? 'correct' : 'wrong')
    commitAnswerResult(isCorrect, {
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

  const handleMeaningRecallSubmit = useCallback((_source: SpellingSubmitSource = 'button') => {
    if (spellingResult || !currentWord) return
    const isCorrect = normalizeWordAnswer(spellingInput) === normalizeWordAnswer(currentWord.word)
    clearSpellingRetryTimer()
    clearSpellingFeedbackDismissTimer()
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)
    setSpellingResult(isCorrect ? 'correct' : 'wrong')
    commitAnswerResult(isCorrect, {
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

  const handleSkip = useCallback(() => {
    if (!currentWord) return
    const hasPendingListeningMistake = wrongSelections.length > 0
      && (mode === 'listening' || (mode === 'smart' && smartDimension === 'listening'))

    if (hasPendingListeningMistake) {
      goNext(false)
      return
    }

    saveWrongWord(currentWord)
    recordErrorReviewOutcome(currentWord, false)
    registerAnsweredWord(currentWord.word)
    const nextWrong = wrongCount + 1
    setWrongCount(nextWrong)
    saveProgress(correctCount, nextWrong)
    sessionWrongRef.current += 1
    syncCurrentSessionSnapshot(Date.now())
    recordModeAnswer(mode ?? 'smart', false)
    setWordStatuses(prev => ({ ...prev, [queue[queueIndex]]: 'wrong' }))
    goNext(false)
  }, [
    correctCount,
    currentWord,
    goNext,
    mode,
    queue,
    queueIndex,
    recordErrorReviewOutcome,
    registerAnsweredWord,
    saveProgress,
    saveWrongWord,
    smartDimension,
    syncCurrentSessionSnapshot,
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
    handleSkip,
  }
}
