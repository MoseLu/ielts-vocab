import { useCallback, useEffect } from 'react'
import * as AIChat from '../../../hooks/useAIChat'
import {
  retryPendingQuickMemorySync,
  syncQuickMemoryRecordsToBackend,
} from '../../../lib/quickMemorySync'
import type { QuickMemoryRecordState } from '../../../lib/quickMemory'
import type { QuickMemorySessionResult as SessionResult } from './QuickMemorySummary'

const QUICK_MEMORY_PENDING_SYNC_RETRY_MS = 15000

interface QuickMemoryModeSessionArgs {
  bookId: string | null
  chapterId: string | null
  bookIdRef: React.MutableRefObject<string | null>
  chapterIdRef: React.MutableRefObject<string | null>
  resultsRef: React.MutableRefObject<SessionResult[]>
  sessionStartRef: React.MutableRefObject<number>
  sessionLastActiveAtRef: React.MutableRefObject<number>
  completedSessionDurationSecondsRef: React.MutableRefObject<number | null>
  sessionIdRef: React.MutableRefObject<number | null>
  sessionLoggedRef: React.MutableRefObject<boolean>
  pendingRecordSyncRef: React.MutableRefObject<Record<string, QuickMemoryRecordState>>
  recordSyncInFlightRef: React.MutableRefObject<boolean>
  recordSyncPromiseRef: React.MutableRefObject<Promise<void> | null>
}

function summarizeResults(results: SessionResult[]) {
  return {
    wordsStudied: results.length,
    correctCount: results.filter(result => result.choice === 'known').length,
    wrongCount: results.filter(result => result.choice === 'unknown').length,
  }
}

export function useQuickMemoryModeSession({
  bookId,
  chapterId,
  bookIdRef,
  chapterIdRef,
  resultsRef,
  sessionStartRef,
  sessionLastActiveAtRef,
  completedSessionDurationSecondsRef,
  sessionIdRef,
  sessionLoggedRef,
  pendingRecordSyncRef,
  recordSyncInFlightRef,
  recordSyncPromiseRef,
}: QuickMemoryModeSessionArgs) {
  useEffect(() => {
    bookIdRef.current = bookId
  }, [bookId, bookIdRef])

  useEffect(() => {
    chapterIdRef.current = chapterId
  }, [chapterId, chapterIdRef])

  const syncSessionSnapshot = useCallback((patch: {
    activeAt?: number
    wordsStudied?: number
    correctCount?: number
    wrongCount?: number
  } = {}) => {
    if (patch.activeAt != null) {
      sessionLastActiveAtRef.current = Math.max(sessionLastActiveAtRef.current, patch.activeAt)
    }
    if (sessionIdRef.current == null || sessionStartRef.current <= 0) return
    AIChat.updateStudySessionSnapshot({
      sessionId: sessionIdRef.current,
      mode: 'quickmemory',
      bookId: bookIdRef.current,
      chapterId: chapterIdRef.current,
      startedAt: sessionStartRef.current,
      ...(patch.activeAt != null ? { activeAt: patch.activeAt } : {}),
      wordsStudied: patch.wordsStudied,
      correctCount: patch.correctCount,
      wrongCount: patch.wrongCount,
    })
  }, [bookIdRef, chapterIdRef, sessionIdRef, sessionLastActiveAtRef, sessionStartRef])

  const flushPendingRecordSync = useCallback((keepalive = false) => {
    if (recordSyncInFlightRef.current) {
      return recordSyncPromiseRef.current ?? Promise.resolve()
    }

    const pendingEntries = Object.entries(pendingRecordSyncRef.current)
    if (!pendingEntries.length) return Promise.resolve()

    pendingRecordSyncRef.current = {}
    recordSyncInFlightRef.current = true

    const syncTask = syncQuickMemoryRecordsToBackend(
      pendingEntries.map(([word, record]) => ({ word, record })),
      { keepalive },
    ).catch(() => {
      pendingRecordSyncRef.current = {
        ...Object.fromEntries(pendingEntries),
        ...pendingRecordSyncRef.current,
      }
    }).finally(() => {
      recordSyncInFlightRef.current = false
      recordSyncPromiseRef.current = null
    })
    recordSyncPromiseRef.current = syncTask
    return syncTask
  }, [pendingRecordSyncRef, recordSyncInFlightRef, recordSyncPromiseRef])

  const accumulateCompletedDuration = useCallback((durationSeconds: number) => {
    completedSessionDurationSecondsRef.current = Math.max(
      0,
      Math.round(completedSessionDurationSecondsRef.current ?? 0) + Math.max(0, Math.round(durationSeconds)),
    )
  }, [completedSessionDurationSecondsRef])

  const resetCurrentSessionSegment = useCallback(() => {
    sessionStartRef.current = 0
    sessionLastActiveAtRef.current = 0
    sessionIdRef.current = null
  }, [sessionIdRef, sessionLastActiveAtRef, sessionStartRef])

  useEffect(() => {
    const retryPendingSync = () => {
      if (document.visibilityState === 'hidden') return
      void retryPendingQuickMemorySync().catch(() => {})
    }
    const timerId = window.setInterval(retryPendingSync, QUICK_MEMORY_PENDING_SYNC_RETRY_MS)
    window.addEventListener('online', retryPendingSync)
    return () => {
      window.clearInterval(timerId)
      window.removeEventListener('online', retryPendingSync)
    }
  }, [])

  const prepareLearningSession = useCallback(async (activityAt = Date.now()) => {
    const summary = summarizeResults(resultsRef.current)

    if (typeof AIChat.prepareStudySessionForLearningAction === 'function') {
      const prepared = await AIChat.prepareStudySessionForLearningAction({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
        lastActiveAt: sessionLastActiveAtRef.current,
        mode: 'quickmemory',
        bookId: bookIdRef.current,
        chapterId: chapterIdRef.current,
        wordsStudied: summary.wordsStudied,
        correctCount: summary.correctCount,
        wrongCount: summary.wrongCount,
        activityAt,
      })

      if (prepared.segmented && prepared.finalizedPreviousSegment && !prepared.finalizedPreviousSegment.discarded) {
        accumulateCompletedDuration(prepared.finalizedPreviousSegment.durationSeconds)
      }

      sessionStartRef.current = prepared.startedAt
      sessionLastActiveAtRef.current = prepared.lastActiveAt
      sessionIdRef.current = prepared.sessionId
      sessionLoggedRef.current = false
      return
    }

    if (sessionStartRef.current > 0) {
      sessionLastActiveAtRef.current = activityAt
      AIChat.touchStudySessionActivity(sessionIdRef.current, activityAt)
      sessionLoggedRef.current = false
      return
    }

    sessionStartRef.current = activityAt
    sessionLastActiveAtRef.current = activityAt
    sessionLoggedRef.current = false
    sessionIdRef.current = await AIChat.startSession({
      mode: 'quickmemory',
      bookId: bookIdRef.current,
      chapterId: chapterIdRef.current,
    }, {
      skipRecovery: true,
      startedAt: activityAt,
    })
  }, [
    accumulateCompletedDuration,
    bookIdRef,
    chapterIdRef,
    resultsRef,
    sessionIdRef,
    sessionLastActiveAtRef,
    sessionLoggedRef,
    sessionStartRef,
  ])

  const completeCurrentSession = useCallback(async () => {
    if (sessionLoggedRef.current || sessionStartRef.current <= 0) {
      sessionLoggedRef.current = true
      return completedSessionDurationSecondsRef.current ?? 0
    }

    const summary = summarizeResults(resultsRef.current)
    let finalized = { discarded: true, durationSeconds: 0 }

    if (typeof AIChat.finalizeStudySessionSegment === 'function') {
      finalized = await AIChat.finalizeStudySessionSegment({
        sessionId: sessionIdRef.current,
        mode: 'quickmemory',
        bookId: bookIdRef.current,
        chapterId: chapterIdRef.current,
        wordsStudied: summary.wordsStudied,
        correctCount: summary.correctCount,
        wrongCount: summary.wrongCount,
        startedAt: sessionStartRef.current,
      })
    } else {
      const durationSeconds = AIChat.resolveStudySessionDurationSeconds({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
      })
      const shouldDiscard = (
        summary.wordsStudied <= 0
        && summary.correctCount <= 0
        && summary.wrongCount <= 0
        && durationSeconds < AIChat.PASSIVE_STUDY_SESSION_MIN_SECONDS
      )

      if (shouldDiscard) {
        await AIChat.cancelSession(sessionIdRef.current)
      } else {
        await AIChat.logSession({
          mode: 'quickmemory',
          bookId: bookIdRef.current,
          chapterId: chapterIdRef.current,
          wordsStudied: summary.wordsStudied,
          correctCount: summary.correctCount,
          wrongCount: summary.wrongCount,
          durationSeconds,
          startedAt: sessionStartRef.current,
          sessionId: sessionIdRef.current,
        })
        finalized = { discarded: false, durationSeconds }
      }
    }

    if (!finalized.discarded) {
      accumulateCompletedDuration(finalized.durationSeconds)
    }

    sessionLoggedRef.current = true
    resetCurrentSessionSegment()
    return completedSessionDurationSecondsRef.current ?? 0
  }, [
    accumulateCompletedDuration,
    bookIdRef,
    chapterIdRef,
    completedSessionDurationSecondsRef,
    resetCurrentSessionSegment,
    resultsRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
  ])

  return {
    completeCurrentSession,
    flushPendingRecordSync,
    prepareLearningSession,
    resetCurrentSessionSegment,
    syncSessionSnapshot,
  }
}
