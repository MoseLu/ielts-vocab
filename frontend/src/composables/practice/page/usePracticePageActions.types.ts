import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type {
  LastState,
  OptionItem,
  PracticeMode,
  QuickMemoryRecordState,
  SmartDimension,
  SpellingSubmitSource,
  Word,
  WordStatuses,
} from '../../../components/practice/types'
import type { ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'

export interface UsePracticePageActionsParams {
  user: unknown
  userId: string | number | null
  mode?: PracticeMode
  smartDimension: SmartDimension
  bookId: string | null
  chapterId: string | null
  currentDay?: number
  currentWord: Word | undefined
  queue: number[]
  queueIndex: number
  vocabulary: Word[]
  correctCount: number
  wrongCount: number
  correctIndex: number
  options: OptionItem[]
  wrongSelections: number[]
  choiceOptionsReady: boolean
  showResult: boolean
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  errorMode: boolean
  errorReviewRound: number
  settings: {
    repeatWrong?: boolean
  }
  navigate: (to: string) => void
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  saveProgress: (
    correct: number,
    wrong: number,
    options?: { advanceToNext?: boolean },
  ) => void
  clearSpellingRetryTimer: () => void
  clearSpellingFeedbackDismissTimer: () => void
  registerAnsweredWord: (word: string) => void
  syncCurrentSessionSnapshot: (activeAt?: number) => void
  lastState: LastState | null
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  previousWord: Word | null
  setSelectedAnswer: Dispatch<SetStateAction<number | null>>
  setWrongSelections: Dispatch<SetStateAction<number[]>>
  setShowResult: Dispatch<SetStateAction<boolean>>
  setSpellingInput: Dispatch<SetStateAction<string>>
  setSpellingResult: Dispatch<SetStateAction<'correct' | 'wrong' | null>>
  setSpellingFeedbackLocked: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackDismissing: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackSnapshot: Dispatch<SetStateAction<string | null>>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  spellingRetryTimerRef: MutableRefObject<number | null>
  sessionCorrectRef: MutableRefObject<number>
  sessionWrongRef: MutableRefObject<number>
  sessionStartRef: MutableRefObject<number>
  sessionIdRef: MutableRefObject<number | null>
  sessionLoggedRef: MutableRefObject<boolean>
  completedSessionDurationSecondsRef: MutableRefObject<number | null>
  sessionUniqueWordsRef: MutableRefObject<Set<string>>
  sessionBookIdRef: MutableRefObject<string | null>
  sessionChapterIdRef: MutableRefObject<string | null>
  effectiveSessionModeRef: MutableRefObject<string>
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
}

export interface UsePracticePageActionsResult {
  saveWrongWord: (word: Word) => void
  handleQuickMemoryRecordChange: (word: Word, record: QuickMemoryRecordState) => void
  recordErrorReviewOutcome: (word: Word, wasCorrect: boolean) => void
  goBack: () => void
  handleOptionSelect: (idx: number) => void
  handleSpellingSubmit: (source?: SpellingSubmitSource) => void
  handleMeaningRecallSubmit: (source?: SpellingSubmitSource) => void
  handleSkip: () => void
}
