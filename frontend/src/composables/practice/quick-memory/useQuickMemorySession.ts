import { useEffect } from 'react'
import { apiFetch } from '../../../lib'
import {
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  cancelSession,
  flushStudySessionOnPageHide,
  logSession,
  resolveStudySessionDurationSeconds,
  startSession,
  touchStudySessionActivity,
} from '../../../hooks/useAIChat'
import type { QuickMemorySessionResult } from '../../../components/practice/quick-memory/QuickMemorySummary'

interface QuickMemorySessionLifecycleArgs {
  bookId: string | null
  chapterId: string | null
  done: boolean
  index: number
  queueLength: number
  reviewMode?: boolean
  results: QuickMemorySessionResult[]
  resultsRef: React.MutableRefObject<QuickMemorySessionResult[]>
  sessionStartRef: React.MutableRefObject<number>
  bookIdRef: React.MutableRefObject<string | null>
  chapterIdRef: React.MutableRefObject<string | null>
  sessionIdRef: React.MutableRefObject<number | null>
  sessionLoggedRef: React.MutableRefObject<boolean>
  pendingSessionCancelRef: React.MutableRefObject<boolean>
  flushPendingRecordSync: (keepalive?: boolean) => void
  syncSessionSnapshot: (patch?: {
    activeAt?: number
    wordsStudied?: number
    correctCount?: number
    wrongCount?: number
  }) => void
  showSaveError: () => void
}

function summarizeResults(results: QuickMemorySessionResult[]) {
  return {
    wordsStudied: results.length,
    correctCount: results.filter(result => result.choice === 'known').length,
    wrongCount: results.filter(result => result.choice === 'unknown').length,
  }
}

export function useQuickMemorySession({
  bookId,
  chapterId,
  done,
  index,
  queueLength,
  reviewMode,
  results,
  resultsRef,
  sessionStartRef,
  bookIdRef,
  chapterIdRef,
  sessionIdRef,
  sessionLoggedRef,
  pendingSessionCancelRef,
  flushPendingRecordSync,
  syncSessionSnapshot,
  showSaveError,
}: QuickMemorySessionLifecycleArgs) {
  useEffect(() => {
    bookIdRef.current = bookId
  }, [bookId, bookIdRef])

  useEffect(() => {
    chapterIdRef.current = chapterId
  }, [chapterId, chapterIdRef])

  useEffect(() => {
    const touch = () => {
      if (sessionStartRef.current <= 0) return
      touchStudySessionActivity(sessionIdRef.current)
    }
    const onVisible = () => {
      if (document.visibilityState === 'visible') touch()
    }
    window.addEventListener('pointerdown', touch, true)
    window.addEventListener('keydown', touch, true)
    window.addEventListener('focus', touch)
    document.addEventListener('visibilitychange', onVisible)
    return () => {
      window.removeEventListener('pointerdown', touch, true)
      window.removeEventListener('keydown', touch, true)
      window.removeEventListener('focus', touch)
      document.removeEventListener('visibilitychange', onVisible)
    }
  }, [sessionIdRef, sessionStartRef])

  useEffect(() => {
    const handlePageHide = () => {
      flushPendingRecordSync(true)
      if (sessionLoggedRef.current || sessionStartRef.current <= 0) return
      const summary = summarizeResults(resultsRef.current)
      flushStudySessionOnPageHide({
        mode: 'quickmemory',
        bookId: bookIdRef.current,
        chapterId: chapterIdRef.current,
        wordsStudied: summary.wordsStudied,
        correctCount: summary.correctCount,
        wrongCount: summary.wrongCount,
        startedAt: sessionStartRef.current,
        sessionId: sessionIdRef.current,
      })
    }
    window.addEventListener('pagehide', handlePageHide)
    return () => window.removeEventListener('pagehide', handlePageHide)
  }, [
    bookIdRef,
    chapterIdRef,
    flushPendingRecordSync,
    resultsRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
  ])

  useEffect(() => {
    if (reviewMode || !done || !bookId || !chapterId) return
    const progressData = {
      current_index: queueLength,
      correct_count: results.filter(result => result.choice === 'known').length,
      wrong_count: results.filter(result => result.choice === 'unknown').length,
      words_learned: queueLength,
      is_completed: true,
    }

    const chapterProgress: Record<string, typeof progressData & { updatedAt: string }> =
      JSON.parse(localStorage.getItem('chapter_progress') || '{}')
    chapterProgress[`${bookId}_${chapterId}`] = { ...progressData, updatedAt: new Date().toISOString() }
    localStorage.setItem('chapter_progress', JSON.stringify(chapterProgress))

    apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
      method: 'POST',
      body: JSON.stringify(progressData),
    }).catch(showSaveError)

    apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
      method: 'POST',
      body: JSON.stringify({
        mode: 'quickmemory',
        correct_count: progressData.correct_count,
        wrong_count: progressData.wrong_count,
        is_completed: true,
      }),
    }).catch(() => {})
  }, [bookId, chapterId, done, queueLength, results, reviewMode, showSaveError])

  useEffect(() => {
    if (!done || sessionLoggedRef.current || results.length < queueLength) return
    const finalResults = resultsRef.current
    if (finalResults.length < queueLength) return
    const summary = summarizeResults(finalResults)

    sessionLoggedRef.current = true
    flushPendingRecordSync()
    syncSessionSnapshot({
      wordsStudied: queueLength,
      correctCount: summary.correctCount,
      wrongCount: summary.wrongCount,
    })
    const durationSeconds = resolveStudySessionDurationSeconds({
      sessionId: sessionIdRef.current,
      startedAt: sessionStartRef.current,
    })
    logSession({
      mode: 'quickmemory',
      bookId,
      chapterId,
      wordsStudied: queueLength,
      correctCount: summary.correctCount,
      wrongCount: summary.wrongCount,
      durationSeconds,
      startedAt: sessionStartRef.current,
      sessionId: sessionIdRef.current,
    })
  }, [
    bookId,
    chapterId,
    done,
    flushPendingRecordSync,
    queueLength,
    results,
    resultsRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
    syncSessionSnapshot,
  ])

  useEffect(() => {
    return () => {
      if (reviewMode || done || !bookId || !chapterId || index === 0) return
      const summary = summarizeResults(results)
      const partialProgress = {
        current_index: index,
        correct_count: summary.correctCount,
        wrong_count: summary.wrongCount,
        words_learned: index,
        is_completed: false,
        updatedAt: new Date().toISOString(),
      }
      const chapterProgress: Record<string, typeof partialProgress> =
        JSON.parse(localStorage.getItem('chapter_progress') || '{}')
      if (!chapterProgress[`${bookId}_${chapterId}`]?.is_completed) {
        chapterProgress[`${bookId}_${chapterId}`] = partialProgress
        localStorage.setItem('chapter_progress', JSON.stringify(chapterProgress))
      }
    }
  }, [bookId, chapterId, done, index, results, reviewMode])

  useEffect(() => {
    sessionStartRef.current = Date.now()
    sessionLoggedRef.current = false
    pendingSessionCancelRef.current = false
    startSession({ mode: 'quickmemory', bookId, chapterId })
      .then(id => {
        sessionIdRef.current = id
        if (pendingSessionCancelRef.current && id) cancelSession(id)
      })
      .catch(() => {})
  }, [bookId, chapterId, pendingSessionCancelRef, sessionIdRef, sessionLoggedRef, sessionStartRef])

  useEffect(() => {
    return () => {
      flushPendingRecordSync(true)
      if (sessionLoggedRef.current) return

      const summary = summarizeResults(resultsRef.current)
      const durationSeconds = resolveStudySessionDurationSeconds({
        sessionId: sessionIdRef.current,
        startedAt: sessionStartRef.current,
      })
      if (summary.wordsStudied <= 0 && durationSeconds < PASSIVE_STUDY_SESSION_MIN_SECONDS) {
        pendingSessionCancelRef.current = true
        cancelSession(sessionIdRef.current)
        return
      }

      sessionLoggedRef.current = true
      syncSessionSnapshot({
        wordsStudied: summary.wordsStudied,
        correctCount: summary.correctCount,
        wrongCount: summary.wrongCount,
      })
      logSession({
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
    }
  }, [
    bookIdRef,
    chapterIdRef,
    flushPendingRecordSync,
    pendingSessionCancelRef,
    resultsRef,
    sessionIdRef,
    sessionLoggedRef,
    sessionStartRef,
    syncSessionSnapshot,
  ])
}
