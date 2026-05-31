import { useCallback } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import { playWordAudio as playWordUtil } from '../../../features/practice/audio/practiceAudio'
import { buildNextErrorReviewWords, type ErrorReviewRoundResults } from '../../../features/practice/errorReviewSession'
import { persistWrongWordsProgress } from '../../../features/practice/practiceSessionHelpers'
import type {
  LastState,
  AppSettings,
  PracticeMode,
  Word,
  WordPlaybackHandler,
  WordStatuses,
} from '../../../features/practice/types'
import { resolveWordPlaybackSettings } from '../../../features/practice/wordPlayback'
import type { PracticeGroupWindow } from './practicePageGrouping'
import { usePracticeChapterProgressReset } from './usePracticeChapterProgressReset'
import { usePracticeProgressPersistence } from './usePracticeProgressPersistence'

interface UsePracticePageControlsParams {
  mode?: PracticeMode
  currentDay?: number
  userId: string | number | null
  bookId: string | null
  chapterId: string | null
  reviewMode: boolean
  errorMode: boolean
  queue: number[]
  queueIndex: number
  vocabulary: Word[]
  correctCount: number
  wrongCount: number
  errorReviewRound: number
  settings: AppSettings
  practiceBookId: string | null
  reviewSummary: {
    has_more: boolean
    next_offset: number | null
  } | null
  navigate: (to: string) => void
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  beginSession: () => void
  computeChapterWordsLearned: (cap: number) => number
  correctCountRef: MutableRefObject<number>
  wrongCountRef: MutableRefObject<number>
  chapterCorrectBaselineRef: MutableRefObject<number>
  chapterWrongBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  chapterGroupStartRef: MutableRefObject<number>
  chapterQueueWordsRef: MutableRefObject<string[]>
  errorProgressHydratedRef: MutableRefObject<boolean>
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
  vocabRef: MutableRefObject<Word[]>
  queueRef: MutableRefObject<number[]>
  startSpeechRecording: () => Promise<void>
  stopSpeechRecording: () => void
  speechConnected: boolean
  setVocabulary: Dispatch<SetStateAction<Word[]>>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  setReviewOffset: Dispatch<SetStateAction<number>>
  setErrorReviewRound: Dispatch<SetStateAction<number>>
  setPracticeGroup: Dispatch<SetStateAction<PracticeGroupWindow | null>>
}

interface UsePracticePageControlsResult {
  saveProgress: (
    correct: number,
    wrong: number,
    options?: { advanceToNext?: boolean },
  ) => void
  resetChapterProgress: () => Promise<void>
  startRecording: () => Promise<void>
  stopRecording: () => void
  playWord: WordPlaybackHandler
  handleContinueReview: () => void
  buildChapterPath: (chapterId: string | number) => string
  handleContinueErrorReview: () => void
}

export function usePracticePageControls({
  mode,
  currentDay,
  userId,
  bookId,
  chapterId,
  reviewMode,
  errorMode,
  queue,
  queueIndex,
  vocabulary,
  errorReviewRound,
  settings,
  practiceBookId,
  reviewSummary,
  showToast,
  beginSession,
  computeChapterWordsLearned,
  correctCountRef,
  wrongCountRef,
  chapterCorrectBaselineRef,
  chapterWrongBaselineRef,
  uniqueAnsweredRef,
  chapterGroupStartRef,
  chapterQueueWordsRef,
  errorProgressHydratedRef,
  errorRoundResultsRef,
  vocabRef,
  queueRef,
  startSpeechRecording,
  stopSpeechRecording,
  speechConnected,
  setVocabulary,
  setQueue,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setWordStatuses,
  setReviewOffset,
  setErrorReviewRound,
  setPracticeGroup,
}: UsePracticePageControlsParams): UsePracticePageControlsResult {
  const saveProgress = usePracticeProgressPersistence({
    mode,
    currentDay,
    userId,
    bookId,
    chapterId,
    errorMode,
    queue,
    queueIndex,
    vocabulary,
    errorReviewRound,
    showToast,
    computeChapterWordsLearned,
    correctCountRef,
    wrongCountRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
    uniqueAnsweredRef,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    errorProgressHydratedRef,
  })

  const startRecording = useCallback(async () => {
    if (!speechConnected) {
      showToast?.('语音服务未连接，请稍后重试', 'error')
      return
    }
    showToast?.('请说出单词...', 'info')
    await startSpeechRecording()
  }, [showToast, speechConnected, startSpeechRecording])

  const resetChapterProgress = usePracticeChapterProgressReset({
    mode,
    bookId,
    chapterId,
    queue,
    vocabulary,
    settings,
    showToast,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
    queueRef,
    setQueue,
    setQueueIndex,
    setPracticeGroup,
  })

  const playWord = useCallback<WordPlaybackHandler>((word, options) => {
    playWordUtil(word, resolveWordPlaybackSettings(settings, options))
  }, [settings])

  const handleContinueReview = useCallback(() => {
    if (!reviewSummary?.has_more) return
    setVocabulary([])
    vocabRef.current = []
    setQueue([])
    queueRef.current = []
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    setReviewOffset(current => (current === 0 ? -1 : 0))
  }, [queueRef, reviewSummary, setCorrectCount, setLastState, setPreviousWord, setQueue, setQueueIndex, setReviewOffset, setVocabulary, setWordStatuses, setWrongCount, vocabRef])

  const buildChapterPath = useCallback((nextChapterId: string | number) => {
    if (!practiceBookId) return '/practice'
    const encodedBookId = encodeURIComponent(practiceBookId)
    const encodedChapterId = encodeURIComponent(String(nextChapterId))
    const memoryModeQuery = mode === 'quickmemory' || mode === 'test' ? `&mode=${mode}` : ''
    return reviewMode
      ? `/practice?review=due&book=${encodedBookId}&chapter=${encodedChapterId}${memoryModeQuery}`
      : `/practice?book=${encodedBookId}&chapter=${encodedChapterId}${memoryModeQuery}`
  }, [mode, practiceBookId, reviewMode])

  const handleContinueErrorReview = useCallback(() => {
    const nextRoundWords = buildNextErrorReviewWords(vocabulary, errorRoundResultsRef.current)
    if (!nextRoundWords.length) return

    const nextRound = errorReviewRound + 1
    const nextQueue = Array.from({ length: nextRoundWords.length }, (_, index) => index)
    setVocabulary(nextRoundWords)
    vocabRef.current = nextRoundWords
    setQueue(nextQueue)
    queueRef.current = nextQueue
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    setErrorReviewRound(nextRound)
    errorRoundResultsRef.current = {}
    errorProgressHydratedRef.current = true

    persistWrongWordsProgress({
      current_index: 0,
      correct_count: 0,
      wrong_count: 0,
      is_completed: false,
      round: nextRound,
      queue_words: nextRoundWords.map(word => word.word),
      mode,
    }, userId)

    beginSession()
  }, [
    beginSession,
    errorProgressHydratedRef,
    errorReviewRound,
    errorRoundResultsRef,
    mode,
    queueRef,
    setCorrectCount,
    setErrorReviewRound,
    setLastState,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    setVocabulary,
    setWordStatuses,
    setWrongCount,
    userId,
    vocabRef,
    vocabulary,
  ])

  return {
    saveProgress,
    resetChapterProgress,
    startRecording,
    stopRecording: stopSpeechRecording,
    playWord,
    handleContinueReview,
    buildChapterPath,
    handleContinueErrorReview,
  }
}
