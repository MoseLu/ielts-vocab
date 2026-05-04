import { useEffect, useRef } from 'react'
import type { Chapter, ProgressData, Word } from '../../../components/practice/types'
import { apiFetch } from '../../../lib'
import { loadSmartStats, loadSmartStatsFromBackend } from '../../../lib/smartMode'
import { safeParse } from '../../../lib/validation'
import { LearnerProfileSchema } from '../../../lib/schemas'
import { loadBookProgressSnapshot, loadChapterProgressSnapshot } from '../../../components/practice/progressStorage'
import { buildCanonicalWordListPath, loadErrorModeData, loadQuickMemoryReviewQueue } from './practicePageDataLoaders'
import { applyScopedWordsLoad, resolvePracticeWordsForMode } from './practicePageScopedLoad'
import { resolvePracticeGroupSize } from './practicePageGrouping'
import type { UsePracticePageDataParams } from './practicePageDataTypes'

export function usePracticePageData({
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
  searchParamsKey,
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
  setPracticeGroup,
  vocabRef,
  queueRef,
  chapterGroupStartRef,
  chapterQueueWordsRef,
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
  const runtimeRefs = useRef({ beginSession, onListeningModeFallback, showToast })
  runtimeRefs.current = { beginSession, onListeningModeFallback, showToast }

  useEffect(() => {
    if (!resolvedPracticeBookId) {
      setBookChapters([])
      return
    }

    let cancelled = false

    apiFetch<{ chapters?: Chapter[] }>(`/api/books/${resolvedPracticeBookId}/chapters`)
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
    const currentSearchParams = new URLSearchParams(searchParamsKey)
    const restartRequested = currentSearchParams.get('restart') === '1'
    errorProgressHydratedRef.current = false
    setNoListeningPresets(false)
    setReviewQueueError(null)
    const chapterGroupSize = bookId && chapterId
      ? resolvePracticeGroupSize(settings)
      : null
    if (reviewMode || errorMode || !chapterId) {
      chapterGroupStartRef.current = 0
      chapterQueueWordsRef.current = []
      setPracticeGroup(null)
    }
    const scopedLoadKey = reviewMode || errorMode
      ? null
      : JSON.stringify({
          currentDay: currentDay ?? null,
          mode: mode ?? null,
          bookId,
          chapterId,
          shuffle: settings.shuffle ?? null,
          chapterGroupSize,
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
        showToast: runtimeRefs.current.showToast,
        isCancelled: () => cancelled,
      })

      return () => {
        cancelled = true
      }
    }

    if (reviewMode) return

    if (errorMode) {
      void loadErrorModeData({
        user: userId == null ? undefined : { id: userId },
        userId,
        searchParams: currentSearchParams,
        mode,
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
        beginSession: runtimeRefs.current.beginSession,
        showToast: runtimeRefs.current.showToast,
        isCancelled: () => cancelled,
      })

      return () => {
        cancelled = true
      }
    }

    if (bookId && chapterId) {
      apiFetch<{ words?: Word[] }>(buildCanonicalWordListPath(bookId, chapterId))
        .then(async (data: { words?: Word[] }) => {
          if (!canApplyScopedLoad()) return
          const rawWords = data.words || []
          const words = resolvePracticeWordsForMode({
            rawWords,
            mode,
            isCustomPracticeScope,
            setNoListeningPresets,
            onListeningModeFallback: runtimeRefs.current.onListeningModeFallback,
          })
          if (!words || !canApplyScopedLoad()) return
          const progress = restartRequested ? null : await loadChapterProgressSnapshot(bookId, chapterId)
          if (!canApplyScopedLoad()) return
          applyScopedWordsLoad({
            words,
            progress,
            chapterId,
            mode,
            shuffle: false,
            groupSize: chapterGroupSize,
            scopedLoadKey,
            scopedLoadGeneration,
            canApplyScopedLoad,
            lastAppliedScopedLoadRef,
            scopedQueueWordsCacheRef,
            queueRef,
            vocabRef,
            chapterGroupStartRef,
            chapterQueueWordsRef,
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
            setPracticeGroup,
            beginSession: runtimeRefs.current.beginSession,
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
      apiFetch<{ words?: Word[] }>(buildCanonicalWordListPath(bookId))
        .then(async (data: { words?: Word[] }) => {
          if (!canApplyScopedLoad()) return
          const rawWords = data.words || []
          const words = resolvePracticeWordsForMode({
            rawWords,
            mode,
            isCustomPracticeScope,
            setNoListeningPresets,
            onListeningModeFallback: runtimeRefs.current.onListeningModeFallback,
          })
          if (!words || !canApplyScopedLoad()) return
          const progress = restartRequested ? null : await loadBookProgressSnapshot(bookId)
          if (!canApplyScopedLoad()) return
          applyScopedWordsLoad({
            words,
            progress,
            chapterId,
            mode,
            shuffle: false,
            groupSize: null,
            scopedLoadKey,
            scopedLoadGeneration,
            canApplyScopedLoad,
            lastAppliedScopedLoadRef,
            scopedQueueWordsCacheRef,
            queueRef,
            vocabRef,
            chapterGroupStartRef,
            chapterQueueWordsRef,
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
            setPracticeGroup,
            beginSession: runtimeRefs.current.beginSession,
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

    apiFetch<{ vocabulary?: Word[]; words?: Word[] }>(`/api/vocabulary/day/${currentDay}`)
      .then(async (data: { vocabulary?: Word[]; words?: Word[] }) => {
        if (!canApplyScopedLoad()) return
        const rawWords = data.vocabulary || data.words || []
        const words = resolvePracticeWordsForMode({
          rawWords,
          mode,
          isCustomPracticeScope,
          setNoListeningPresets,
          onListeningModeFallback: runtimeRefs.current.onListeningModeFallback,
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
          groupSize: null,
          scopedLoadKey,
          scopedLoadGeneration,
          canApplyScopedLoad,
          lastAppliedScopedLoadRef,
          scopedQueueWordsCacheRef,
          queueRef,
          vocabRef,
          chapterGroupStartRef,
          chapterQueueWordsRef,
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
          setPracticeGroup,
          beginSession: runtimeRefs.current.beginSession,
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
    bookId,
    chapterId,
    currentDay,
    errorMode,
    isCustomPracticeScope,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    mode,
    navigate,
    queueRef,
    reviewMode,
    reviewOffset,
    searchParamsKey,
    setResumeProgress,
    setCorrectCount,
    setCurrentChapterTitle,
    setErrorReviewRound,
    setLastState,
    setNoListeningPresets,
    setPreviousWord,
    setPracticeGroup,
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
    settings.reviewLimitCustomized,
    settings.shuffle,
    uniqueAnsweredRef,
    userId,
    vocabRef,
    wordsLearnedBaselineRef,
  ])
}
