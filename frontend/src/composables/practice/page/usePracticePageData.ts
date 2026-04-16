import { useEffect, useRef } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { Chapter, LastState, PracticeMode, ProgressData, Word, WordStatuses } from '../../../components/practice/types'
import { apiFetch, buildApiUrl } from '../../../lib'
import { loadSmartStats, loadSmartStatsFromBackend } from '../../../lib/smartMode'
import { safeParse } from '../../../lib/validation'
import { LearnerProfileSchema, type LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'
import { loadBookProgressSnapshot, loadChapterProgressSnapshot } from '../../../components/practice/progressStorage'
import { type ReviewQueueContext, type ReviewQueueSummary } from '../../../components/practice/page/practicePageHelpers'
import type { ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'
import { applyScopedWordsLoad, loadErrorModeData, loadQuickMemoryReviewQueue, resolvePracticeWordsForMode } from './practicePageDataLoaders'

interface UsePracticePageDataParams {
  user: unknown
  userId: string | number | null
  currentDay?: number
  mode?: PracticeMode
  bookId: string | null
  chapterId: string | null
  resolvedPracticeBookId: string | null
  resolvedPracticeChapterId: string | null
  reviewMode: boolean
  errorMode: boolean
  isCustomPracticeScope: boolean
  searchParams: URLSearchParams
  settings: {
    shuffle?: boolean
    reviewInterval?: string
    reviewLimit?: string
  }
  navigate: (to: string) => void
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
  setVocabulary: Dispatch<SetStateAction<Word[]>>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setBookChapters: Dispatch<SetStateAction<Chapter[]>>
  setCurrentChapterTitle: Dispatch<SetStateAction<string>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  setBackendLearnerProfile: Dispatch<SetStateAction<BackendLearnerProfile | null>>
  setReviewOffset: Dispatch<SetStateAction<number>>
  reviewOffset: number
  setReviewSummary: Dispatch<SetStateAction<ReviewQueueSummary | null>>
  setReviewContext: Dispatch<SetStateAction<ReviewQueueContext | null>>
  setReviewQueueError: Dispatch<SetStateAction<string | null>>
  setQuickMemoryReviewQueueResolved: Dispatch<SetStateAction<boolean>>
  setNoListeningPresets: Dispatch<SetStateAction<boolean>>
  setErrorReviewRound: Dispatch<SetStateAction<number>>
  vocabRef: MutableRefObject<Word[]>
  queueRef: MutableRefObject<number[]>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  errorProgressHydratedRef: MutableRefObject<boolean>
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  onListeningModeFallback: () => void
}

export function usePracticePageData({
  user,
  userId,
  currentDay,
  mode,
  bookId,
  chapterId,
  resolvedPracticeBookId,
  resolvedPracticeChapterId,
  reviewMode,
  errorMode,
  isCustomPracticeScope,
  searchParams,
  settings,
  navigate,
  showToast,
  setVocabulary,
  setQueue,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setBookChapters,
  setCurrentChapterTitle,
  setWordStatuses,
  setResumeProgress,
  setBackendLearnerProfile,
  setReviewOffset,
  reviewOffset,
  setReviewSummary,
  setReviewContext,
  setReviewQueueError,
  setQuickMemoryReviewQueueResolved,
  setNoListeningPresets,
  setErrorReviewRound,
  vocabRef,
  queueRef,
  wordsLearnedBaselineRef,
  uniqueAnsweredRef,
  errorProgressHydratedRef,
  errorRoundResultsRef,
  beginSession,
  onListeningModeFallback,
}: UsePracticePageDataParams) {
  const scopedLoadGenerationRef = useRef(0)
  const activeScopedLoadKeyRef = useRef<string | null>(null)
  const lastAppliedScopedLoadRef = useRef<{ key: string | null; generation: number }>({ key: null, generation: 0 })
  const scopedQueueWordsCacheRef = useRef<Record<string, string[]>>({})

  useEffect(() => {
    if (!resolvedPracticeBookId) {
      setBookChapters([])
      return
    }

    let cancelled = false

    fetch(buildApiUrl(`/api/books/${resolvedPracticeBookId}/chapters`))
      .then(r => r.json())
      .then((d: { chapters?: Chapter[] }) => {
        if (cancelled) return
        const chapters = d.chapters || []
        setBookChapters(chapters)
        const current = chapters.find(ch => String(ch.id) === String(resolvedPracticeChapterId)) || chapters[0]
        if (current) setCurrentChapterTitle(current.title)
      })
      .catch(() => {
        if (!cancelled) {
          setBookChapters([])
        }
      })

    return () => {
      cancelled = true
    }
  }, [
    resolvedPracticeBookId,
    resolvedPracticeChapterId,
    setBookChapters,
    setCurrentChapterTitle,
  ])

  useEffect(() => {
    if (!bookId) return
    setReviewOffset(0)
    setQuickMemoryReviewQueueResolved(false)
  }, [bookId, chapterId, mode, reviewMode, settings.reviewInterval, settings.reviewLimit, setQuickMemoryReviewQueueResolved, setReviewOffset])

  useEffect(() => {
    if (reviewMode) {
      setBackendLearnerProfile(null)
      return
    }

    let cancelled = false

    void (async () => {
      try {
        const data = await apiFetch<unknown>('/api/ai/learner-profile')
        const parsed = safeParse(LearnerProfileSchema, data)
        if (!cancelled) {
          setBackendLearnerProfile(parsed.success ? parsed.data : null)
        }
      } catch {
        if (!cancelled) {
          setBackendLearnerProfile(null)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [currentDay, reviewMode, setBackendLearnerProfile, userId])

  useEffect(() => {
    let cancelled = false
    errorProgressHydratedRef.current = false
    setNoListeningPresets(false)
    setReviewQueueError(null)
    const scopedLoadKey = reviewMode || errorMode
      ? null
      : JSON.stringify({
          currentDay: currentDay ?? null,
          mode: mode ?? null,
          bookId,
          chapterId,
          shuffle: settings.shuffle ?? null,
        })
    const scopedLoadGeneration = scopedLoadGenerationRef.current + 1
    scopedLoadGenerationRef.current = scopedLoadGeneration
    activeScopedLoadKeyRef.current = scopedLoadKey
    const canApplyScopedLoad = () => {
      if (activeScopedLoadKeyRef.current !== scopedLoadKey) return false
      return !(
        lastAppliedScopedLoadRef.current.key === scopedLoadKey
        && scopedLoadGeneration < lastAppliedScopedLoadRef.current.generation
      )
    }

    if (!reviewMode && Object.keys(loadSmartStats()).length === 0) {
      void loadSmartStatsFromBackend()
    }

    if (reviewMode && mode === 'quickmemory') {
      void loadQuickMemoryReviewQueue({
        bookId,
        chapterId,
        reviewOffset,
        settings,
        setResumeProgress,
        setQuickMemoryReviewQueueResolved,
        setVocabulary,
        vocabRef,
        setQueue,
        queueRef,
        setQueueIndex,
        setCorrectCount,
        setWrongCount,
        setPreviousWord,
        setLastState,
        setWordStatuses,
        setReviewSummary,
        setReviewContext,
        setReviewQueueError,
        setCurrentChapterTitle,
        showToast,
        isCancelled: () => cancelled,
      })

      return () => {
        cancelled = true
      }
    }

    if (reviewMode) return

    if (errorMode) {
      void loadErrorModeData({
        user,
        userId,
        searchParams,
        mode,
        shuffle: settings.shuffle,
        setResumeProgress,
        setNoListeningPresets,
        setVocabulary,
        vocabRef,
        setQueue,
        queueRef,
        setErrorReviewRound,
        errorRoundResultsRef,
        setQueueIndex,
        setCorrectCount,
        setWrongCount,
        setPreviousWord,
        setLastState,
        setWordStatuses,
        errorProgressHydratedRef,
        beginSession,
        showToast,
        isCancelled: () => cancelled,
      })

      return () => {
        cancelled = true
      }
    }

    if (bookId && chapterId) {
      fetch(buildApiUrl(`/api/books/${bookId}/chapters/${chapterId}`))
        .then(res => res.json())
        .then(async (data: { words?: Word[] }) => {
          if (!canApplyScopedLoad()) return
          const rawWords = data.words || []
          const words = resolvePracticeWordsForMode({
            rawWords,
            mode,
            isCustomPracticeScope,
            setNoListeningPresets,
            onListeningModeFallback,
          })
          if (!words || !canApplyScopedLoad()) return
          const progress = await loadChapterProgressSnapshot(bookId, chapterId)
          if (!canApplyScopedLoad()) return
          applyScopedWordsLoad({
            words,
            progress,
            chapterId,
            mode,
            shuffle: settings.shuffle,
            scopedLoadKey,
            scopedLoadGeneration,
            canApplyScopedLoad,
            lastAppliedScopedLoadRef,
            scopedQueueWordsCacheRef,
            queueRef,
            vocabRef,
            wordsLearnedBaselineRef,
            uniqueAnsweredRef,
            setVocabulary,
            setQueue,
            setQueueIndex,
            setCorrectCount,
            setWrongCount,
            setPreviousWord,
            setLastState,
            setWordStatuses,
            setResumeProgress,
            beginSession,
          })
        })
        .catch(() => {
          if (canApplyScopedLoad()) {
            showToast?.('加载章节词汇失败', 'error')
          }
        })
      return
    }

    if (bookId) {
      setResumeProgress(null)
      fetch(buildApiUrl(`/api/books/${bookId}/words?per_page=100`))
        .then(res => res.json())
        .then(async (data: { words?: Word[] }) => {
          if (!canApplyScopedLoad()) return
          const rawWords = data.words || []
          const words = resolvePracticeWordsForMode({
            rawWords,
            mode,
            isCustomPracticeScope,
            setNoListeningPresets,
            onListeningModeFallback,
          })
          if (!words || !canApplyScopedLoad()) return
          const progress = await loadBookProgressSnapshot(bookId)
          if (!canApplyScopedLoad()) return
          applyScopedWordsLoad({
            words,
            progress,
            chapterId,
            mode,
            shuffle: settings.shuffle,
            scopedLoadKey,
            scopedLoadGeneration,
            canApplyScopedLoad,
            lastAppliedScopedLoadRef,
            scopedQueueWordsCacheRef,
            queueRef,
            vocabRef,
            wordsLearnedBaselineRef,
            uniqueAnsweredRef,
            setVocabulary,
            setQueue,
            setQueueIndex,
            setCorrectCount,
            setWrongCount,
            setPreviousWord,
            setLastState,
            setWordStatuses,
            setResumeProgress,
            beginSession,
          })
        })
        .catch(() => {
          if (canApplyScopedLoad()) {
            showToast?.('加载词书失败', 'error')
          }
        })
      return
    }

    if (!currentDay) {
      setResumeProgress(null)
      navigate('/plan')
      return
    }

    fetch(buildApiUrl(`/api/vocabulary/day/${currentDay}`))
      .then(res => res.json())
      .then(async (data: { vocabulary?: Word[]; words?: Word[] }) => {
        if (!canApplyScopedLoad()) return
        const rawWords = data.vocabulary || data.words || []
        const words = resolvePracticeWordsForMode({
          rawWords,
          mode,
          isCustomPracticeScope,
          setNoListeningPresets,
          onListeningModeFallback,
        })
        if (!words || !canApplyScopedLoad()) return
        const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('day_progress') || '{}')
        let progress: ProgressData | null = saved[String(currentDay)] ?? null
        if (!progress) {
          try {
            const remote = await apiFetch<{ progress?: Array<{ day: number; current_index: number; correct_count: number; wrong_count: number; is_completed?: boolean }> }>('/api/progress')
            if (!canApplyScopedLoad()) return
            const entry = remote.progress?.find(item => item.day === currentDay)
            progress = entry
              ? {
                  current_index: entry.current_index,
                  correct_count: entry.correct_count,
                  wrong_count: entry.wrong_count,
                  is_completed: Boolean(entry.is_completed),
                }
              : null
          } catch {}
        }
        if (!canApplyScopedLoad()) return
        applyScopedWordsLoad({
          words,
          progress,
          chapterId,
          mode,
          shuffle: settings.shuffle,
          scopedLoadKey,
          scopedLoadGeneration,
          canApplyScopedLoad,
          lastAppliedScopedLoadRef,
          scopedQueueWordsCacheRef,
          queueRef,
          vocabRef,
          wordsLearnedBaselineRef,
          uniqueAnsweredRef,
          setVocabulary,
          setQueue,
          setQueueIndex,
          setCorrectCount,
          setWrongCount,
          setPreviousWord,
          setLastState,
          setWordStatuses,
          setResumeProgress,
          beginSession,
        })
      })
      .catch(() => {
        if (canApplyScopedLoad()) {
          showToast?.('加载词汇失败', 'error')
        }
      })

    return () => {
      cancelled = true
    }
  }, [
    beginSession,
    bookId,
    chapterId,
    currentDay,
    errorMode,
    isCustomPracticeScope,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    mode,
    navigate,
    onListeningModeFallback,
    queueRef,
    reviewMode,
    reviewOffset,
    searchParams,
    setResumeProgress,
    setCorrectCount,
    setCurrentChapterTitle,
    setErrorReviewRound,
    setLastState,
    setNoListeningPresets,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    setQuickMemoryReviewQueueResolved,
    setReviewQueueError,
    setReviewContext,
    setReviewSummary,
    setVocabulary,
    setWordStatuses,
    setWrongCount,
    settings.reviewInterval,
    settings.reviewLimit,
    settings.shuffle,
    showToast,
    uniqueAnsweredRef,
    user,
    userId,
    vocabRef,
    wordsLearnedBaselineRef,
  ])
}
