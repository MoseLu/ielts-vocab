import { useCallback } from 'react'
import { usePracticePageSettings } from './usePracticePageSettings'
import type { UsePracticePageSessionParams, UsePracticePageSessionResult } from './usePracticePageSession.types'
import { usePracticeStudySessionLifecycle } from './usePracticeStudySessionLifecycle'
import { usePracticeStudySessionRefs } from './usePracticeStudySessionRefs'

export function usePracticePageSession({
  mode,
  errorMode,
  chapterId,
  practiceBookId,
  practiceChapterId,
  correctCount,
  wrongCount,
}: UsePracticePageSessionParams): UsePracticePageSessionResult {
  const { settings, radioQuickSettings, handleRadioSettingChange } = usePracticePageSettings()
  const refs = usePracticeStudySessionRefs({
    mode,
    errorMode,
    practiceBookId,
    practiceChapterId,
    correctCount,
    wrongCount,
  })
  const {
    beginSession,
    prepareSessionForLearningAction,
    completeCurrentSession,
    markFollowSessionInteraction,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
    isCurrentSessionActive,
  } = usePracticeStudySessionLifecycle({
    mode,
    errorMode,
    refs,
  })

  const computeChapterWordsLearned = useCallback((cap: number) => {
    if (!chapterId || !cap) return refs.wordsLearnedBaselineRef.current
    return Math.min(cap, Math.max(
      refs.wordsLearnedBaselineRef.current,
      refs.uniqueAnsweredRef.current.size,
    ))
  }, [chapterId, refs.uniqueAnsweredRef, refs.wordsLearnedBaselineRef])

  const registerAnsweredWord = useCallback((word: string) => {
    const key = word.trim().toLowerCase()
    if (!key) return
    refs.sessionUniqueWordsRef.current.add(key)
    if (chapterId) refs.uniqueAnsweredRef.current.add(key)
  }, [chapterId, refs.sessionUniqueWordsRef, refs.uniqueAnsweredRef])

  return {
    settings,
    radioQuickSettings,
    handleRadioSettingChange,
    sessionStartRef: refs.sessionStartRef,
    sessionIdRef: refs.sessionIdRef,
    sessionCorrectRef: refs.sessionCorrectRef,
    sessionWrongRef: refs.sessionWrongRef,
    correctCountRef: refs.correctCountRef,
    wrongCountRef: refs.wrongCountRef,
    completedSessionDurationSecondsRef: refs.completedSessionDurationSecondsRef,
    sessionLoggedRef: refs.sessionLoggedRef,
    currentModeRef: refs.currentModeRef,
    effectiveSessionModeRef: refs.effectiveSessionModeRef,
    sessionBookIdRef: refs.sessionBookIdRef,
    sessionChapterIdRef: refs.sessionChapterIdRef,
    radioWordsStudiedRef: refs.radioWordsStudiedRef,
    wordsLearnedBaselineRef: refs.wordsLearnedBaselineRef,
    uniqueAnsweredRef: refs.uniqueAnsweredRef,
    sessionUniqueWordsRef: refs.sessionUniqueWordsRef,
    beginSession,
    prepareSessionForLearningAction,
    completeCurrentSession,
    computeChapterWordsLearned,
    registerAnsweredWord,
    markFollowSessionInteraction,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
    isCurrentSessionActive,
  }
}
