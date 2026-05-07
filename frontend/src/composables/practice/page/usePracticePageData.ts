import { useEffect } from 'react'
import { loadSmartStats, loadSmartStatsFromBackend } from '../../../lib/smartMode'
import type { UsePracticePageDataParams } from './practicePageDataTypes'
import {
  usePracticeBookChapters,
  usePracticeLearnerProfile,
  usePracticeReviewQueueReset,
} from './usePracticePageMetadata'
import { usePracticeScopedWordsLoader } from './usePracticeScopedWordsLoader'
import { usePracticeSpecialModeData } from './usePracticeSpecialModeData'

export function usePracticePageData(params: UsePracticePageDataParams) {
  const {
    userId,
    currentDay,
    mode,
    bookId,
    chapterId,
    resolvedPracticeBookId,
    resolvedPracticeChapterId,
    reviewMode,
    settings,
    setBookChapters,
    setCurrentChapterTitle,
    setBackendLearnerProfile,
    setReviewOffset,
    setQuickMemoryReviewQueueResolved,
  } = params

  usePracticeBookChapters({
    resolvedPracticeBookId,
    resolvedPracticeChapterId,
    setBookChapters,
    setCurrentChapterTitle,
  })

  usePracticeReviewQueueReset({
    bookId,
    chapterId,
    mode,
    reviewMode,
    settings,
    setReviewOffset,
    setQuickMemoryReviewQueueResolved,
  })

  usePracticeLearnerProfile({
    currentDay,
    reviewMode,
    setBackendLearnerProfile,
    userId,
  })

  useEffect(() => {
    if (mode !== 'quickmemory' && Object.keys(loadSmartStats()).length === 0) {
      void loadSmartStatsFromBackend()
    }
  }, [mode])

  usePracticeScopedWordsLoader(params)
  usePracticeSpecialModeData(params)
}
