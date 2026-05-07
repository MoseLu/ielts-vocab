import { useCallback, useEffect } from 'react'
import type { PracticeMode } from '../../../features/practice/types'
import { syncSmartStatsToBackend } from '../../../lib/smartMode'
import {
  AIChat,
  getAIChatNumber,
  getOptionalAIChatFunction,
  normalizeDuration,
} from './practiceSessionAiChatAdapter'
import type { PracticeStudySessionRefs } from './usePracticeStudySessionRefs'

interface UsePracticeStudySessionLifecycleParams {
  mode?: PracticeMode
  errorMode: boolean
  refs: PracticeStudySessionRefs
}

export function usePracticeStudySessionLifecycle({
  mode,
  errorMode,
  refs,
}: UsePracticeStudySessionLifecycleParams) {
  const isStudySessionActive = getOptionalAIChatFunction<typeof AIChat.isStudySessionActive>('isStudySessionActive')
  const finalizeStudySessionSegment = getOptionalAIChatFunction<typeof AIChat.finalizeStudySessionSegment>('finalizeStudySessionSegment')
  const markStudySessionRecoveryHandled = getOptionalAIChatFunction<typeof AIChat.markStudySessionRecoveryHandled>('markStudySessionRecoveryHandled')
  const prepareStudySessionForLearningAction = getOptionalAIChatFunction<typeof AIChat.prepareStudySessionForLearningAction>('prepareStudySessionForLearningAction')
  const passiveStudySessionMinSeconds = getAIChatNumber('PASSIVE_STUDY_SESSION_MIN_SECONDS', 30)

  const {
    sessionStartRef,
    sessionLastActiveAtRef,
    sessionIdRef,
    sessionCorrectRef,
    sessionWrongRef,
    completedSessionDurationSecondsRef,
    sessionLoggedRef,
    followInteractionRef,
    radioInteractionRef,
    radioWordsStudiedRef,
    sessionUniqueWordsRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    currentModeRef,
    effectiveSessionModeRef,
    activeSessionModeRef,
    previousEffectiveModeRef,
  } = refs

  const getCurrentSegmentWordsStudied = useCallback((sessionMode = activeSessionModeRef.current) => (
    sessionMode === 'radio'
      ? radioWordsStudiedRef.current
      : sessionUniqueWordsRef.current.size
  ), [activeSessionModeRef, radioWordsStudiedRef, sessionUniqueWordsRef])

  const accumulateCompletedDuration = useCallback((durationSeconds: number) => {
    completedSessionDurationSecondsRef.current = normalizeDuration(
      completedSessionDurationSecondsRef.current,
      durationSeconds,
    )
  }, [completedSessionDurationSecondsRef])

  const resetCurrentSegmentState = useCallback(() => {
    sessionStartRef.current = 0
    sessionLastActiveAtRef.current = 0
    sessionIdRef.current = null
    sessionCorrectRef.current = 0
    sessionWrongRef.current = 0
    sessionUniqueWordsRef.current = new Set()
    followInteractionRef.current = false
    radioInteractionRef.current = false
    radioWordsStudiedRef.current = 0
  }, [
    followInteractionRef,
    radioInteractionRef,
    radioWordsStudiedRef,
    sessionCorrectRef,
    sessionIdRef,
    sessionLastActiveAtRef,
    sessionStartRef,
    sessionUniqueWordsRef,
    sessionWrongRef,
  ])

  const syncCurrentSessionSnapshot = useCallback((activeAt?: number) => {
    if (sessionStartRef.current <= 0) return
    const nextActiveAt = activeAt ?? sessionLastActiveAtRef.current
    if (nextActiveAt > 0) {
      sessionLastActiveAtRef.current = Math.max(sessionLastActiveAtRef.current, nextActiveAt)
    }

    if (sessionIdRef.current == null) return
    AIChat.updateStudySessionSnapshot({
      sessionId: sessionIdRef.current,
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookIdRef.current,
      chapterId: sessionChapterIdRef.current,
      startedAt: sessionStartRef.current,
      ...(nextActiveAt > 0 ? { activeAt: nextActiveAt } : {}),
      wordsStudied: getCurrentSegmentWordsStudied(),
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    })
  }, [
    effectiveSessionModeRef,
    getCurrentSegmentWordsStudied,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionCorrectRef,
    sessionIdRef,
    sessionLastActiveAtRef,
    sessionStartRef,
    sessionWrongRef,
  ])

  const isCurrentSessionActive = useCallback((at = Date.now()) => {
    if (sessionStartRef.current <= 0) return false
    if (isStudySessionActive) {
      return isStudySessionActive({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
        lastActiveAt: sessionLastActiveAtRef.current,
      }, at)
    }
    return true
  }, [isStudySessionActive, sessionIdRef, sessionLastActiveAtRef, sessionStartRef])

  const closeActiveSegment = useCallback(async ({
    markRoundCompleted = false,
    syncStats = true,
    accumulateIntoCompletedRef = true,
  }: {
    markRoundCompleted?: boolean
    syncStats?: boolean
    accumulateIntoCompletedRef?: boolean
  } = {}) => {
    if (sessionStartRef.current <= 0 || sessionLoggedRef.current) {
      if (markRoundCompleted) {
        sessionLoggedRef.current = true
      }
      return completedSessionDurationSecondsRef.current ?? 0
    }

    const sessionMode = activeSessionModeRef.current
    const sessionBookId = sessionBookIdRef.current
    const sessionChapterId = sessionChapterIdRef.current
    if (sessionMode === 'quickmemory') {
      if (markRoundCompleted) {
        sessionLoggedRef.current = true
      }
      resetCurrentSegmentState()
      return completedSessionDurationSecondsRef.current ?? 0
    }

    const payload = {
      sessionId: sessionIdRef.current,
      mode: sessionMode,
      bookId: sessionBookId,
      chapterId: sessionChapterId,
      startedAt: sessionStartRef.current,
      wordsStudied: getCurrentSegmentWordsStudied(sessionMode),
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    }

    let finalized = { discarded: true, durationSeconds: 0 }
    if (finalizeStudySessionSegment) {
      finalized = await finalizeStudySessionSegment(payload)
    } else {
      const durationSeconds = AIChat.resolveStudySessionDurationSeconds({
        sessionId: payload.sessionId,
        startedAt: payload.startedAt,
      })
      const shouldDiscard = sessionMode === 'follow'
        ? !followInteractionRef.current
        : (
            payload.wordsStudied <= 0
            && payload.correctCount <= 0
            && payload.wrongCount <= 0
            && durationSeconds < passiveStudySessionMinSeconds
          )
      markStudySessionRecoveryHandled?.()
      if (shouldDiscard) {
        await AIChat.cancelSession(payload.sessionId)
      } else {
        AIChat.updateStudySessionSnapshot({
          sessionId: payload.sessionId,
          mode: payload.mode,
          bookId: payload.bookId,
          chapterId: payload.chapterId,
          startedAt: payload.startedAt,
          wordsStudied: payload.wordsStudied,
          correctCount: payload.correctCount,
          wrongCount: payload.wrongCount,
        })
        await AIChat.logSession({
          ...payload,
          durationSeconds,
        })
        finalized = { discarded: false, durationSeconds }
      }
    }

    if (!finalized.discarded && accumulateIntoCompletedRef) {
      accumulateCompletedDuration(finalized.durationSeconds)
    }
    if (!finalized.discarded && syncStats && sessionMode !== 'follow') {
      syncSmartStatsToBackend({
        bookId: sessionBookId,
        chapterId: sessionChapterId,
        mode: sessionMode,
      })
    }

    sessionLoggedRef.current = markRoundCompleted
    resetCurrentSegmentState()
    return completedSessionDurationSecondsRef.current ?? 0
  }, [
    accumulateCompletedDuration,
    activeSessionModeRef,
    completedSessionDurationSecondsRef,
    finalizeStudySessionSegment,
    followInteractionRef,
    getCurrentSegmentWordsStudied,
    markStudySessionRecoveryHandled,
    passiveStudySessionMinSeconds,
    resetCurrentSegmentState,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionCorrectRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
    sessionWrongRef,
  ])

  const startOrTouchLearningSession = useCallback(async (activityAt: number) => {
    if (sessionStartRef.current > 0) {
      sessionLastActiveAtRef.current = activityAt
      AIChat.touchStudySessionActivity(sessionIdRef.current, activityAt)
      sessionLoggedRef.current = false
      return
    }

    sessionStartRef.current = activityAt
    sessionLastActiveAtRef.current = activityAt
    sessionLoggedRef.current = false
    activeSessionModeRef.current = effectiveSessionModeRef.current
    sessionIdRef.current = await AIChat.startSession({
      mode: effectiveSessionModeRef.current,
      bookId: sessionBookIdRef.current,
      chapterId: sessionChapterIdRef.current,
    }, {
      skipRecovery: true,
      startedAt: activityAt,
    })
  }, [
    activeSessionModeRef,
    effectiveSessionModeRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionIdRef,
    sessionLastActiveAtRef,
    sessionLoggedRef,
    sessionStartRef,
  ])

  const prepareSessionForLearningAction = useCallback(async (activityAt = Date.now()) => {
    if (effectiveSessionModeRef.current === 'quickmemory') return

    const stats = {
      wordsStudied: getCurrentSegmentWordsStudied(),
      correctCount: sessionCorrectRef.current,
      wrongCount: sessionWrongRef.current,
    }

    if (prepareStudySessionForLearningAction) {
      const prepared = await prepareStudySessionForLearningAction({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
        lastActiveAt: sessionLastActiveAtRef.current,
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        activityAt,
        ...stats,
      })

      if (prepared.segmented) {
        const finalizedPreviousSegment = prepared.finalizedPreviousSegment
        if (finalizedPreviousSegment && !finalizedPreviousSegment.discarded) {
          accumulateCompletedDuration(finalizedPreviousSegment.durationSeconds)
          if (effectiveSessionModeRef.current !== 'follow') {
            syncSmartStatsToBackend({
              bookId: sessionBookIdRef.current,
              chapterId: sessionChapterIdRef.current,
              mode: effectiveSessionModeRef.current,
            })
          }
        }
        sessionCorrectRef.current = 0
        sessionWrongRef.current = 0
        sessionUniqueWordsRef.current = new Set()
        followInteractionRef.current = false
        radioInteractionRef.current = false
        radioWordsStudiedRef.current = 0
      }

      sessionStartRef.current = prepared.startedAt
      sessionLastActiveAtRef.current = prepared.lastActiveAt
      sessionIdRef.current = prepared.sessionId
      sessionLoggedRef.current = false
      activeSessionModeRef.current = effectiveSessionModeRef.current
      return
    }

    await startOrTouchLearningSession(activityAt)
  }, [
    accumulateCompletedDuration,
    activeSessionModeRef,
    effectiveSessionModeRef,
    followInteractionRef,
    getCurrentSegmentWordsStudied,
    prepareStudySessionForLearningAction,
    radioInteractionRef,
    radioWordsStudiedRef,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionCorrectRef,
    sessionIdRef,
    sessionLastActiveAtRef,
    sessionLoggedRef,
    sessionStartRef,
    sessionUniqueWordsRef,
    sessionWrongRef,
    startOrTouchLearningSession,
  ])

  const completeCurrentSession = useCallback(async () => {
    const totalDurationSeconds = await closeActiveSegment({
      markRoundCompleted: true,
      syncStats: true,
    })
    completedSessionDurationSecondsRef.current = totalDurationSeconds
    return totalDurationSeconds
  }, [closeActiveSegment, completedSessionDurationSecondsRef])

  useEffect(() => {
    const nextMode = errorMode ? 'errors' : (mode ?? 'smart')
    const previousMode = previousEffectiveModeRef.current
    currentModeRef.current = mode
    effectiveSessionModeRef.current = nextMode
    if (
      previousMode !== nextMode
      && sessionStartRef.current > 0
      && activeSessionModeRef.current !== 'quickmemory'
      && !sessionLoggedRef.current
    ) {
      void closeActiveSegment({ syncStats: true, accumulateIntoCompletedRef: false })
    }
    previousEffectiveModeRef.current = nextMode
  }, [
    activeSessionModeRef,
    closeActiveSegment,
    currentModeRef,
    effectiveSessionModeRef,
    errorMode,
    mode,
    previousEffectiveModeRef,
    sessionLoggedRef,
    sessionStartRef,
  ])

  useEffect(() => () => {
    void closeActiveSegment({ syncStats: true, accumulateIntoCompletedRef: false })
  }, [closeActiveSegment])

  useEffect(() => {
    const handlePageHide = () => {
      if (currentModeRef.current === 'quickmemory') return
      if (sessionLoggedRef.current || sessionStartRef.current <= 0) return
      AIChat.flushStudySessionOnPageHide({
        mode: effectiveSessionModeRef.current,
        bookId: sessionBookIdRef.current,
        chapterId: sessionChapterIdRef.current,
        wordsStudied: getCurrentSegmentWordsStudied(),
        correctCount: sessionCorrectRef.current,
        wrongCount: sessionWrongRef.current,
        startedAt: sessionStartRef.current,
        sessionId: sessionIdRef.current,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [
    currentModeRef,
    effectiveSessionModeRef,
    getCurrentSegmentWordsStudied,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionCorrectRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
    sessionWrongRef,
  ])

  const beginSession = useCallback((context?: { bookId?: string | null; chapterId?: string | null }) => {
    if (sessionStartRef.current > 0 && !sessionLoggedRef.current && activeSessionModeRef.current !== 'quickmemory') {
      void closeActiveSegment({ syncStats: true, accumulateIntoCompletedRef: false })
    }

    sessionBookIdRef.current = context?.bookId ?? sessionBookIdRef.current
    sessionChapterIdRef.current = context?.chapterId ?? sessionChapterIdRef.current
    activeSessionModeRef.current = effectiveSessionModeRef.current
    completedSessionDurationSecondsRef.current = null
    sessionLoggedRef.current = false
    resetCurrentSegmentState()
  }, [
    activeSessionModeRef,
    closeActiveSegment,
    completedSessionDurationSecondsRef,
    effectiveSessionModeRef,
    resetCurrentSegmentState,
    sessionBookIdRef,
    sessionChapterIdRef,
    sessionLoggedRef,
    sessionStartRef,
  ])

  const markFollowSessionInteraction = useCallback(async (activityAt = Date.now()) => {
    await prepareSessionForLearningAction(activityAt)
    followInteractionRef.current = true
    syncCurrentSessionSnapshot(activityAt)
  }, [followInteractionRef, prepareSessionForLearningAction, syncCurrentSessionSnapshot])

  const markRadioSessionInteraction = useCallback(async () => {
    await prepareSessionForLearningAction()
    radioInteractionRef.current = true
  }, [prepareSessionForLearningAction, radioInteractionRef])

  const handleRadioProgressChange = useCallback((wordsStudied: number) => {
    const activeAt = Date.now()
    if (!isCurrentSessionActive(activeAt)) return
    radioWordsStudiedRef.current = Math.max(radioWordsStudiedRef.current, wordsStudied)
    syncCurrentSessionSnapshot(activeAt)
  }, [isCurrentSessionActive, radioWordsStudiedRef, syncCurrentSessionSnapshot])

  return {
    beginSession,
    prepareSessionForLearningAction,
    completeCurrentSession,
    markFollowSessionInteraction,
    markRadioSessionInteraction,
    handleRadioProgressChange,
    syncCurrentSessionSnapshot,
    isCurrentSessionActive,
  }
}
