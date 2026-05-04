import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { Chapter, LastState, PracticeMode, ProgressData, Word, WordStatuses } from '../../../components/practice/types'
import type { ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'
import type { ReviewQueueContext, ReviewQueueSummary } from '../../../components/practice/page/practicePageHelpers'
import type { LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'
import type { PracticeGroupWindow } from './practicePageGrouping'

export interface UsePracticePageDataParams {
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
  searchParamsKey: string
  settings: {
    shuffle?: boolean
    reviewInterval?: string
    reviewLimit?: string
    reviewLimitCustomized?: boolean
  }
  navigate: (to: string) => void
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
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
  setPracticeGroup: Dispatch<SetStateAction<PracticeGroupWindow | null>>
  vocabRef: MutableRefObject<Word[]>
  queueRef: MutableRefObject<number[]>
  chapterGroupStartRef: MutableRefObject<number>
  chapterQueueWordsRef: MutableRefObject<string[]>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  errorProgressHydratedRef: MutableRefObject<boolean>
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  onListeningModeFallback: () => void
}
