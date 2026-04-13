import { useEffect } from 'react'
import { apiFetch } from '../../../lib'
import { flushStudySessionOnPageHide } from '../../../hooks/useAIChat'
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
  sessionLastActiveAtRef: React.MutableRefObject<number>
  completedSessionDurationSecondsRef: React.MutableRefObject<number | null>
  bookIdRef: React.MutableRefObject<string | null>
  chapterIdRef: React.MutableRefObject<string | null>
  sessionIdRef: React.MutableRefObject<number | null>
  sessionLoggedRef: React.MutableRefObject<boolean>
  flushPendingRecordSync: (keepalive?: boolean) => void
  completeCurrentSession: () => Promise<number>
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
  sessionLastActiveAtRef,
  completedSessionDurationSecondsRef,
  bookIdRef,
  chapterIdRef,
  sessionIdRef,
  sessionLoggedRef,
  flushPendingRecordSync,
  completeCurrentSession,
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

    flushPendingRecordSync()
    syncSessionSnapshot({
      wordsStudied: queueLength,
      correctCount: summary.correctCount,
      wrongCount: summary.wrongCount,
    })
    void completeCurrentSession().then(totalDurationSeconds => {
      completedSessionDurationSecondsRef.current = totalDurationSeconds
    })
  }, [
    completeCurrentSession,
    completedSessionDurationSecondsRef,
    done,
    flushPendingRecordSync,
    queueLength,
    results,
    resultsRef,
    sessionLoggedRef,
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
    return () => {
      flushPendingRecordSync(true)
      if (sessionLoggedRef.current || sessionStartRef.current <= 0) return
      void completeCurrentSession().then(totalDurationSeconds => {
        completedSessionDurationSecondsRef.current = totalDurationSeconds
      })
      sessionLastActiveAtRef.current = 0
    }
  }, [
    completeCurrentSession,
    completedSessionDurationSecondsRef,
    flushPendingRecordSync,
    sessionLastActiveAtRef,
    sessionLoggedRef,
    sessionStartRef,
  ])
}
