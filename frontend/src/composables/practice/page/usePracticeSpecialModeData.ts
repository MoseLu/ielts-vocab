import { useEffect, useRef } from 'react'
import { loadErrorModeData, loadQuickMemoryReviewQueue } from './practicePageDataLoaders'
import type { UsePracticePageDataParams } from './practicePageDataTypes'

export function usePracticeSpecialModeData({
  userId,
  mode,
  bookId,
  chapterId,
  reviewMode,
  errorMode,
  searchParamsKey,
  settings,
  showToast,
  setVocabulary,
  setQueue,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setCurrentChapterTitle,
  setWordStatuses,
  setResumeProgress,
  reviewOffset,
  setReviewSummary,
  setReviewContext,
  setReviewQueueError,
  setQuickMemoryReviewQueueResolved,
  setNoListeningPresets,
  setErrorReviewRound,
  vocabRef,
  queueRef,
  errorProgressHydratedRef,
  errorRoundResultsRef,
  beginSession,
}: UsePracticePageDataParams) {
  const runtimeRefs = useRef({ beginSession, showToast })
  runtimeRefs.current = { beginSession, showToast }

  useEffect(() => {
    if (!reviewMode && !errorMode) return

    let cancelled = false
    const currentSearchParams = new URLSearchParams(searchParamsKey)

    if (reviewMode) {
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
  }, [
    bookId,
    chapterId,
    errorMode,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    mode,
    queueRef,
    reviewMode,
    reviewOffset,
    searchParamsKey,
    setCorrectCount,
    setCurrentChapterTitle,
    setErrorReviewRound,
    setLastState,
    setNoListeningPresets,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    setQuickMemoryReviewQueueResolved,
    setResumeProgress,
    setReviewContext,
    setReviewQueueError,
    setReviewSummary,
    setVocabulary,
    setWordStatuses,
    setWrongCount,
    settings.reviewInterval,
    settings.reviewLimit,
    settings.reviewLimitCustomized,
    userId,
    vocabRef,
  ])
}
