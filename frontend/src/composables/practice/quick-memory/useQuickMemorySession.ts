import { useCallback, useEffect, useRef } from 'react'
import { apiFetch } from '../../../lib'
import { flushStudySessionOnPageHide } from '../../../hooks/useAIChat'
import { persistChapterProgressSnapshot } from '../../../features/practice/progressStorage'
import type { QuickMemorySessionResult } from '../../../features/practice/quickMemorySession'
import type { PracticeGroupWindow } from '../page/practicePageGrouping'

interface QuickMemorySessionLifecycleArgs {
  bookId: string | null
  chapterId: string | null
  done: boolean
  index: number
  queueWords: string[]
  queueLength: number
  chapterGroup?: PracticeGroupWindow | null
  chapterQueueWords?: string[]
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
  flushPendingRecordSync: (keepalive?: boolean) => void | Promise<void>
  completeCurrentSession: () => Promise<number>
  syncSessionSnapshot: (patch?: {
    activeAt?: number
    wordsStudied?: number
    correctCount?: number
    wrongCount?: number
  }) => void
  showSaveError: () => void
}

const PROGRESS_SYNC_RETRY_MS = 15000

type ProgressSyncKind = 'partial-progress' | 'completed-progress' | 'completed-mode-progress'

interface ProgressSyncState {
  signature: string | null
  inFlight: boolean
  lastFailedAt: number
}

function createProgressSyncState(): ProgressSyncState {
  return {
    signature: null,
    inFlight: false,
    lastFailedAt: 0,
  }
}

function summarizeResults(results: QuickMemorySessionResult[]) {
  return {
    wordsStudied: results.length,
    correctCount: results.filter(result => result.choice === 'known').length,
    wrongCount: results.filter(result => result.choice === 'unknown').length,
  }
}

function resolveChapterProgressScope(
  queueWords: string[],
  queueLength: number,
  chapterGroup?: PracticeGroupWindow | null,
  chapterQueueWords?: string[],
) {
  const fullQueueWords = chapterQueueWords?.length ? chapterQueueWords : queueWords
  const total = chapterGroup?.total ?? (fullQueueWords.length || queueLength)
  const groupStart = chapterGroup?.start ?? 0
  const groupEnd = chapterGroup ? Math.min(chapterGroup.end, total) : queueLength

  return {
    currentIndex: groupEnd,
    isCompleted: groupEnd >= total,
    partialIndex: Math.min(groupStart + queueLength, total),
    queueWords: fullQueueWords,
  }
}

export function useQuickMemorySession({
  bookId,
  chapterId,
  done,
  index,
  queueWords,
  queueLength,
  chapterGroup,
  chapterQueueWords,
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
  const progressSyncStateRef = useRef<Record<ProgressSyncKind, ProgressSyncState>>({
    'partial-progress': createProgressSyncState(),
    'completed-progress': createProgressSyncState(),
    'completed-mode-progress': createProgressSyncState(),
  })

  const postProgressSnapshot = useCallback((
    kind: ProgressSyncKind,
    url: string,
    payload: Record<string, unknown>,
    onError?: () => void,
  ) => {
    const state = progressSyncStateRef.current[kind]
    const signature = JSON.stringify({ url, payload })
    const now = Date.now()

    if (state.signature === signature) {
      if (state.inFlight || state.lastFailedAt === 0) return
      if (now - state.lastFailedAt < PROGRESS_SYNC_RETRY_MS) return
    }

    state.signature = signature
    state.inFlight = true
    state.lastFailedAt = 0

    apiFetch(url, {
      method: 'POST',
      body: JSON.stringify(payload),
    }).catch(() => {
      state.lastFailedAt = Date.now()
      onError?.()
    }).finally(() => {
      state.inFlight = false
    })
  }, [])

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
    const progressScope = resolveChapterProgressScope(queueWords, queueLength, chapterGroup, chapterQueueWords)
    const progressData = {
      current_index: progressScope.currentIndex,
      correct_count: results.filter(result => result.choice === 'known').length,
      wrong_count: results.filter(result => result.choice === 'unknown').length,
      words_learned: progressScope.currentIndex,
      is_completed: progressScope.isCompleted,
      queue_words: progressScope.queueWords,
    }

    persistChapterProgressSnapshot(bookId, chapterId, progressData)

    postProgressSnapshot(
      'completed-progress',
      `/api/books/${bookId}/chapters/${chapterId}/progress`,
      { mode: 'quickmemory', ...progressData },
      showSaveError,
    )

    postProgressSnapshot(
      'completed-mode-progress',
      `/api/books/${bookId}/chapters/${chapterId}/mode-progress`,
      {
        mode: 'quickmemory',
        correct_count: progressData.correct_count,
        wrong_count: progressData.wrong_count,
        is_completed: progressData.is_completed,
      },
    )
  }, [
    bookId,
    chapterGroup,
    chapterId,
    chapterQueueWords,
    done,
    postProgressSnapshot,
    queueLength,
    queueWords,
    results,
    reviewMode,
    showSaveError,
  ])

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
    if (reviewMode || done || !bookId || !chapterId || index === 0) return
    if (results.length === 0) return
    const summary = summarizeResults(results)
    const progressScope = resolveChapterProgressScope(queueWords, queueLength, chapterGroup, chapterQueueWords)
    const currentIndex = Math.min(progressScope.partialIndex - queueLength + index, progressScope.currentIndex)
    const partialProgress = {
      current_index: currentIndex,
      correct_count: summary.correctCount,
      wrong_count: summary.wrongCount,
      words_learned: currentIndex,
      is_completed: false,
      queue_words: progressScope.queueWords,
    }
    persistChapterProgressSnapshot(bookId, chapterId, partialProgress)
    postProgressSnapshot(
      'partial-progress',
      `/api/books/${bookId}/chapters/${chapterId}/progress`,
      { mode: 'quickmemory', ...partialProgress },
      showSaveError,
    )
  }, [
    bookId,
    chapterGroup,
    chapterId,
    chapterQueueWords,
    done,
    index,
    postProgressSnapshot,
    queueLength,
    queueWords,
    results,
    reviewMode,
    showSaveError,
  ])

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
