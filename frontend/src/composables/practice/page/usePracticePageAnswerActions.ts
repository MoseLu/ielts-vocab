import { useCallback } from 'react'
import { normalizeWordAnswer } from '../../../features/practice/practiceOptions'
import type {
  SmartDimension,
  SpellingSubmitSource,
  Word,
} from '../../../features/practice/types'
import type { UsePracticePageActionsParams } from './usePracticePageActions.types'
import { usePracticePageAnswerCommit, type SubmitPracticeWordMasteryInput } from './usePracticePageAnswerCommit'

type UsePracticePageAnswerActionsParams = Pick<
  UsePracticePageActionsParams,
  | 'mode'
  | 'smartDimension'
  | 'currentWord'
  | 'queue'
  | 'queueIndex'
  | 'correctCount'
  | 'wrongCount'
  | 'correctIndex'
  | 'options'
  | 'wrongSelections'
  | 'choiceOptionsReady'
  | 'showResult'
  | 'spellingInput'
  | 'spellingResult'
  | 'playWord'
  | 'saveProgress'
  | 'clearSpellingRetryTimer'
  | 'clearSpellingFeedbackDismissTimer'
  | 'prepareSessionForLearningAction'
  | 'registerAnsweredWord'
  | 'syncCurrentSessionSnapshot'
  | 'setSelectedAnswer'
  | 'setWrongSelections'
  | 'setShowResult'
  | 'setSpellingInput'
  | 'setSpellingResult'
  | 'setSpellingFeedbackLocked'
  | 'setSpellingFeedbackDismissing'
  | 'setSpellingFeedbackSnapshot'
  | 'setCorrectCount'
  | 'setWrongCount'
  | 'setWordStatuses'
  | 'spellingRetryTimerRef'
  | 'sessionCorrectRef'
  | 'sessionWrongRef'
> & {
  goNext: (wasCorrect: boolean) => Promise<void>
  saveWrongWord: (word: Word) => void
  recordErrorReviewOutcome: (word: Word, wasCorrect: boolean) => void
  submitPracticeWordMastery: (input: SubmitPracticeWordMasteryInput) => void
}

export function usePracticePageAnswerActions({
  mode,
  smartDimension,
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
  playWord,
  saveProgress,
  clearSpellingRetryTimer,
  clearSpellingFeedbackDismissTimer,
  prepareSessionForLearningAction,
  registerAnsweredWord,
  syncCurrentSessionSnapshot,
  setSelectedAnswer,
  setWrongSelections,
  setShowResult,
  setSpellingInput,
  setSpellingResult,
  setSpellingFeedbackLocked,
  setSpellingFeedbackDismissing,
  setSpellingFeedbackSnapshot,
  setCorrectCount,
  setWrongCount,
  setWordStatuses,
  spellingRetryTimerRef,
  sessionCorrectRef,
  sessionWrongRef,
  goNext,
  saveWrongWord,
  recordErrorReviewOutcome,
  submitPracticeWordMastery,
}: UsePracticePageAnswerActionsParams) {
  const commitAnswerResult = usePracticePageAnswerCommit({
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
  })

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
    await commitAnswerResult(passed, {
      dimension: 'speaking',
      analyticsMode: 'follow',
      advanceToNext: false,
      recordEbbinghaus: true,
    })
  }, [
    commitAnswerResult,
    currentWord,
  ])

  const handleSkip = useCallback(async () => {
    if (!currentWord) return
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
      await prepareSessionForLearningAction()
      void goNext(false)
      return
    }

    await commitAnswerResult(false, {
      dimension,
      analyticsMode: mode ?? 'smart',
      advanceToNext: false,
      result: 'skipped',
      recordEbbinghaus: true,
    })
    void goNext(false)
  }, [
    commitAnswerResult,
    currentWord,
    goNext,
    mode,
    prepareSessionForLearningAction,
    smartDimension,
    wrongSelections.length,
  ])

  return {
    handleOptionSelect,
    handleSpellingSubmit,
    handleMeaningRecallSubmit,
    handleFollowReadEvaluated,
    handleSkip,
  }
}
