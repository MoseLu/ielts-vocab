import { useCallback } from 'react'
import type { UsePracticePageActionsParams } from './usePracticePageActions.types'

type UsePracticePageNavigationActionsParams = Pick<
  UsePracticePageActionsParams,
  | 'chapterId'
  | 'completeCurrentSession'
  | 'completedSessionDurationSecondsRef'
  | 'correctCount'
  | 'currentWord'
  | 'errorMode'
  | 'lastState'
  | 'navigate'
  | 'previousWord'
  | 'queue'
  | 'queueIndex'
  | 'setCorrectCount'
  | 'setLastState'
  | 'setPreviousWord'
  | 'setQueue'
  | 'setQueueIndex'
  | 'setSelectedAnswer'
  | 'setShowResult'
  | 'setSpellingFeedbackDismissing'
  | 'setSpellingFeedbackLocked'
  | 'setSpellingFeedbackSnapshot'
  | 'setSpellingInput'
  | 'setSpellingResult'
  | 'setWrongCount'
  | 'setWrongSelections'
  | 'settings'
  | 'wrongCount'
>

export function usePracticePageNavigationActions({
  chapterId,
  completeCurrentSession,
  completedSessionDurationSecondsRef,
  correctCount,
  currentWord,
  errorMode,
  lastState,
  navigate,
  previousWord,
  queue,
  queueIndex,
  setCorrectCount,
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
  setWrongCount,
  setWrongSelections,
  settings,
  wrongCount,
}: UsePracticePageNavigationActionsParams) {
  const resetAnswerState = useCallback(() => {
    setSelectedAnswer(null)
    setWrongSelections([])
    setShowResult(false)
    setSpellingInput('')
    setSpellingResult(null)
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)
  }, [
    setSelectedAnswer,
    setShowResult,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    setWrongSelections,
  ])

  const goNext = useCallback(async (wasCorrect: boolean) => {
    setLastState({ qi: queueIndex, cc: correctCount, wc: wrongCount, prevWord: previousWord })
    setPreviousWord(currentWord ?? null)
    resetAnswerState()

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
    completedSessionDurationSecondsRef,
    correctCount,
    currentWord,
    errorMode,
    navigate,
    previousWord,
    queue,
    queueIndex,
    resetAnswerState,
    setLastState,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    settings.repeatWrong,
    wrongCount,
  ])

  const goBack = useCallback(() => {
    if (!lastState) return
    setQueueIndex(lastState.qi)
    setCorrectCount(lastState.cc)
    setWrongCount(lastState.wc)
    setPreviousWord(lastState.prevWord)
    setLastState(null)
    resetAnswerState()
  }, [
    lastState,
    resetAnswerState,
    setCorrectCount,
    setLastState,
    setPreviousWord,
    setQueueIndex,
    setWrongCount,
  ])

  return { goBack, goNext }
}
