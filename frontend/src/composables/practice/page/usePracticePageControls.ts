import { useCallback, useEffect } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import { apiFetch } from '../../../lib'
import { playWordAudio as playWordUtil } from '../../../components/practice/utils'
import {
  persistBookProgressSnapshot,
  persistChapterProgressSnapshot,
} from '../../../components/practice/progressStorage'
import { buildNextErrorReviewWords, type ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'
import { persistWrongWordsProgress } from '../../../components/practice/page/practicePageHelpers'
import type {
  LastState,
  AppSettings,
  PracticeMode,
  Word,
  WordPlaybackHandler,
  WordStatuses,
} from '../../../components/practice/types'
import { resolveWordPlaybackSettings } from '../../../components/practice/wordPlayback'

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
  uniqueAnsweredRef: MutableRefObject<Set<string>>
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
  uniqueAnsweredRef,
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
}: UsePracticePageControlsParams): UsePracticePageControlsResult {
  const hasValidCurrentDay = Number.isInteger(currentDay ?? null) && (currentDay ?? 0) > 0

  const saveProgress = useCallback((
    correct: number,
    wrong: number,
    { advanceToNext = true }: { advanceToNext?: boolean } = {},
  ) => {
    const nextIndex = advanceToNext ? queueIndex + 1 : queueIndex
    const queueWords = queue
      .map(index => vocabulary[index]?.word)
      .filter((word): word is string => Boolean(word))

    if (errorMode) {
      persistWrongWordsProgress({
        current_index: Math.min(nextIndex, Math.max(queue.length - 1, 0)),
        correct_count: correct,
        wrong_count: wrong,
        is_completed: queue.length > 0 && nextIndex >= queue.length,
        round: errorReviewRound,
        queue_words: queueWords,
        mode,
      }, userId)
      return
    }

    const chapterDone = Boolean(
      chapterId
      && vocabulary.length > 0
      && uniqueAnsweredRef.current.size >= vocabulary.length
      && nextIndex >= queue.length,
    )
    const progressData = {
      current_index: nextIndex,
      correct_count: correct,
      wrong_count: wrong,
      is_completed: chapterId ? chapterDone : (advanceToNext && correct + wrong >= vocabulary.length),
    }

    if (bookId && !chapterId) {
      persistBookProgressSnapshot(bookId, progressData, queueWords)
      apiFetch('/api/books/progress', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId, ...progressData }),
      }).catch(() => showToast?.('进度保存失败，请检查网络连接', 'error'))
      return
    }

    if (bookId && chapterId) {
      const answeredWords = Array.from(uniqueAnsweredRef.current)
      const wordsLearned = computeChapterWordsLearned(vocabulary.length)
      const chapterProgress = {
        ...progressData,
        words_learned: wordsLearned,
        answered_words: answeredWords,
        queue_words: queueWords,
      }
      persistChapterProgressSnapshot(bookId, chapterId, chapterProgress)
      apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
        method: 'POST',
        body: JSON.stringify({ ...chapterProgress }),
      }).catch(() => {})

      if (mode && correct + wrong > 0) {
        apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
          method: 'POST',
          body: JSON.stringify({
            mode,
            correct_count: correct,
            wrong_count: wrong,
            is_completed: progressData.is_completed ?? false,
          }),
        }).catch(() => {})
      }
      return
    }

    if (!hasValidCurrentDay) {
      return
    }
    const activeDay = currentDay

    const dayProgress: Record<string, Record<string, unknown>> = JSON.parse(localStorage.getItem('day_progress') || '{}')
    dayProgress[String(activeDay)] = {
      ...progressData,
      is_completed: correct + wrong >= vocabulary.length,
      queue_words: queueWords,
      updatedAt: new Date().toISOString(),
    }
    localStorage.setItem('day_progress', JSON.stringify(dayProgress))
    apiFetch('/api/progress', {
      method: 'POST',
      body: JSON.stringify({ day: activeDay, ...progressData }),
    }).catch(() => {})
  }, [
    bookId,
    chapterId,
    computeChapterWordsLearned,
    currentDay,
    errorMode,
    errorReviewRound,
    hasValidCurrentDay,
    mode,
    queue,
    queueIndex,
    showToast,
    uniqueAnsweredRef,
    userId,
    vocabulary,
  ])

  useEffect(() => {
    if (!errorMode || !errorProgressHydratedRef.current || !vocabulary.length) return
    const queueWords = queue
      .map(index => vocabulary[index]?.word)
      .filter((word): word is string => Boolean(word))
    persistWrongWordsProgress({
      current_index: Math.min(queueIndex, Math.max(queue.length - 1, 0)),
      correct_count: correctCountRef.current,
      wrong_count: wrongCountRef.current,
      is_completed: queue.length > 0 && queueIndex >= queue.length,
      round: errorReviewRound,
      queue_words: queueWords,
      mode,
    }, userId)
  }, [correctCountRef, errorMode, errorProgressHydratedRef, errorReviewRound, mode, queue, queueIndex, userId, vocabulary, wrongCountRef])

  const startRecording = useCallback(async () => {
    if (!speechConnected) {
      showToast?.('语音服务未连接，请稍后重试', 'error')
      return
    }
    showToast?.('请说出单词...', 'info')
    await startSpeechRecording()
  }, [showToast, speechConnected, startSpeechRecording])

  const resetChapterProgress = useCallback(async () => {
    if (!bookId || !chapterId) return

    const queueWords = queue
      .map(index => vocabulary[index]?.word)
      .filter((word): word is string => Boolean(word))
    const resetSnapshot = {
      current_index: 0,
      correct_count: 0,
      wrong_count: 0,
      is_completed: false,
      words_learned: 0,
      answered_words: [],
      queue_words: queueWords,
    }

    persistChapterProgressSnapshot(bookId, chapterId, resetSnapshot)

    try {
      await apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
        method: 'POST',
        body: JSON.stringify(resetSnapshot),
      })
    } catch {
      showToast?.('重置进度失败，请检查网络连接', 'error')
    }
  }, [bookId, chapterId, queue, showToast, vocabulary])

  const playWord = useCallback<WordPlaybackHandler>((word, options) => {
    playWordUtil(word, resolveWordPlaybackSettings(settings, options))
  }, [settings])

  const handleContinueReview = useCallback(() => {
    const nextOffset = reviewSummary?.next_offset
    if (!reviewSummary?.has_more || nextOffset == null) return
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
    setReviewOffset(nextOffset)
  }, [queueRef, reviewSummary, setCorrectCount, setLastState, setPreviousWord, setQueue, setQueueIndex, setReviewOffset, setVocabulary, setWordStatuses, setWrongCount, vocabRef])

  const buildChapterPath = useCallback((nextChapterId: string | number) => {
    if (!practiceBookId) return '/practice'
    const encodedBookId = encodeURIComponent(practiceBookId)
    const encodedChapterId = encodeURIComponent(String(nextChapterId))
    return reviewMode
      ? `/practice?review=due&book=${encodedBookId}&chapter=${encodedChapterId}`
      : `/practice?book=${encodedBookId}&chapter=${encodedChapterId}`
  }, [practiceBookId, reviewMode])

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
