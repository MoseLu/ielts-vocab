import { useRef, useState } from 'react'
import type {
  Chapter,
  LastState,
  OptionItem,
  ProgressData,
  SmartDimension,
  Word,
  WordStatuses,
} from '../../../features/practice/types'
import type { ReviewQueueContext, ReviewQueueSummary } from '../../../features/practice/practiceSessionHelpers'
import type { ErrorReviewRoundResults } from '../../../features/practice/errorReviewSession'
import type { PracticeGroupWindow } from './practicePageGrouping'

export function usePracticePageState() {
  const [vocabulary, setVocabulary] = useState<Word[]>([])
  const [queue, setQueue] = useState<number[]>([])
  const [queueIndex, setQueueIndex] = useState(0)
  const [options, setOptions] = useState<OptionItem[]>([])
  const [optionsWordKey, setOptionsWordKey] = useState<string | null>(null)
  const [correctIndex, setCorrectIndex] = useState(0)
  const [selectedAnswer, setSelectedAnswer] = useState<number | null>(null)
  const [wrongSelections, setWrongSelections] = useState<number[]>([])
  const [showResult, setShowResult] = useState(false)
  const [correctCount, setCorrectCount] = useState(0)
  const [wrongCount, setWrongCount] = useState(0)
  const [previousWord, setPreviousWord] = useState<Word | null>(null)
  const [lastState, setLastState] = useState<LastState | null>(null)
  const [spellingInput, setSpellingInput] = useState('')
  const [spellingResult, setSpellingResult] = useState<'correct' | 'wrong' | null>(null)
  const [spellingFeedbackLocked, setSpellingFeedbackLocked] = useState(false)
  const [spellingFeedbackDismissing, setSpellingFeedbackDismissing] = useState(false)
  const [spellingFeedbackSnapshot, setSpellingFeedbackSnapshot] = useState<string | null>(null)
  const [favoriteQueueIndex, setFavoriteQueueIndex] = useState(0)
  const [showWordList, setShowWordList] = useState(false)
  const [showPracticeSettings, setShowPracticeSettings] = useState(false)
  const [bookChapters, setBookChapters] = useState<Chapter[]>([])
  const [currentChapterTitle, setCurrentChapterTitle] = useState('')
  const [wordStatuses, setWordStatuses] = useState<WordStatuses>({})
  const [resumeProgress, setResumeProgress] = useState<ProgressData | null>(null)
  const [backendLearnerProfile, setBackendLearnerProfile] = useState<unknown>(null)
  const [reviewOffset, setReviewOffset] = useState(0)
  const [reviewSummary, setReviewSummary] = useState<ReviewQueueSummary | null>(null)
  const [reviewContext, setReviewContext] = useState<ReviewQueueContext | null>(null)
  const [reviewQueueError, setReviewQueueError] = useState<string | null>(null)
  const [practiceGroup, setPracticeGroup] = useState<PracticeGroupWindow | null>(null)
  const [quickMemoryReviewQueueResolved, setQuickMemoryReviewQueueResolved] = useState(false)
  const [noListeningPresets, setNoListeningPresets] = useState(false)
  const [errorReviewRound, setErrorReviewRound] = useState(1)
  const [smartDimension, setSmartDimension] = useState<SmartDimension>('meaning')
  const vocabRef = useRef<Word[]>([])
  const listeningOptionPoolRef = useRef<Word[]>([])
  const queueRef = useRef<number[]>([])
  const chapterGroupStartRef = useRef(0)
  const chapterQueueWordsRef = useRef<string[]>([])
  const errorProgressHydratedRef = useRef(false)
  const errorRoundResultsRef = useRef<ErrorReviewRoundResults>({})
  const practiceCoreSetters = {
    setVocabulary, setQueue, setQueueIndex, setCorrectCount, setWrongCount,
    setPreviousWord, setLastState, setWordStatuses, setPracticeGroup,
  }

  return {
    backendLearnerProfile,
    bookChapters,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    correctCount,
    correctIndex,
    currentChapterTitle,
    errorProgressHydratedRef,
    errorReviewRound,
    errorRoundResultsRef,
    favoriteQueueIndex,
    lastState,
    listeningOptionPoolRef,
    noListeningPresets,
    options,
    optionsWordKey,
    practiceCoreSetters,
    practiceGroup,
    previousWord,
    queue,
    queueIndex,
    queueRef,
    quickMemoryReviewQueueResolved,
    resumeProgress,
    reviewContext,
    reviewOffset,
    reviewQueueError,
    reviewSummary,
    selectedAnswer,
    setBackendLearnerProfile,
    setBookChapters,
    setCorrectCount,
    setCorrectIndex,
    setCurrentChapterTitle,
    setErrorReviewRound,
    setFavoriteQueueIndex,
    setLastState,
    setNoListeningPresets,
    setOptions,
    setOptionsWordKey,
    setPreviousWord,
    setQueue,
    setQuickMemoryReviewQueueResolved,
    setQueueIndex,
    setResumeProgress,
    setReviewContext,
    setReviewOffset,
    setReviewQueueError,
    setReviewSummary,
    setSelectedAnswer,
    setShowPracticeSettings,
    setShowResult,
    setShowWordList,
    setSmartDimension,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    setWordStatuses,
    setWrongCount,
    setWrongSelections,
    showPracticeSettings,
    showResult,
    showWordList,
    smartDimension,
    spellingFeedbackDismissing,
    spellingFeedbackLocked,
    spellingFeedbackSnapshot,
    spellingInput,
    spellingResult,
    vocabRef,
    vocabulary,
    wordStatuses,
    wrongCount,
    wrongSelections,
  }
}
