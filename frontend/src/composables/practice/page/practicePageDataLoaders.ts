import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { LastState, PracticeMode, ProgressData, Word, WordStatuses } from '../../../features/practice/types'
import { DEFAULT_SETTINGS } from '../../../constants'
import { apiFetch } from '../../../lib'
import { filterWrongWords, parseWrongWordsFiltersFromSearchParams } from '../../../features/vocabulary/wrongWordsFilters'
import { loadWrongWords, readWrongWordsReviewSelectionFromStorage } from '../../../features/vocabulary/wrongWordsStore'
import {
  buildWrongWordsQueue,
  filterVocabularyForMode,
  isWrongWordsProgressForWords,
  normalizeOptionWordKey,
  readWrongWordsProgress,
  type ReviewQueueContext,
  type ReviewQueueSummary,
} from '../../../features/practice/practiceSessionHelpers'
import type { ErrorReviewRoundResults } from '../../../features/practice/errorReviewSession'

const QUICK_MEMORY_REVIEW_BATCH_SIZE = 100

type ToastFn = (message: string, type?: 'success' | 'error' | 'info') => void

export function buildCanonicalWordListPath(bookId: string, chapterId?: string | null): string {
  const params = new URLSearchParams({ scope: 'book', book_id: bookId, include_dictionary: '0' })
  if (chapterId) params.set('chapter_id', chapterId)
  return `/api/books/word-list?${params.toString()}`
}

interface QuickMemoryReviewQueueOptions {
  bookId: string | null
  chapterId: string | null
  reviewOffset: number
  settings: {
    reviewInterval?: string
    reviewLimit?: string
  }
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  setQuickMemoryReviewQueueResolved: Dispatch<SetStateAction<boolean>>
  setVocabulary: Dispatch<SetStateAction<Word[]>>
  vocabRef: MutableRefObject<Word[]>
  setQueue: Dispatch<SetStateAction<number[]>>
  queueRef: MutableRefObject<number[]>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  setReviewSummary: Dispatch<SetStateAction<ReviewQueueSummary | null>>
  setReviewContext: Dispatch<SetStateAction<ReviewQueueContext | null>>
  setReviewQueueError: Dispatch<SetStateAction<string | null>>
  setCurrentChapterTitle: Dispatch<SetStateAction<string>>
  showToast?: ToastFn
  isCancelled: () => boolean
}

export async function loadQuickMemoryReviewQueue({
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
  isCancelled,
}: QuickMemoryReviewQueueOptions) {
  setResumeProgress(null)
  setQuickMemoryReviewQueueResolved(false)

  try {
    const reviewWindowDays = Math.max(1, parseInt(String(settings.reviewInterval ?? '1'), 10) || 1)
    const configuredLimit = settings.reviewLimit === 'unlimited'
      ? 0
      : (parseInt(String(settings.reviewLimit ?? DEFAULT_SETTINGS.reviewLimit), 10) || parseInt(DEFAULT_SETTINGS.reviewLimit, 10))
    const reviewLimit = configuredLimit === 0
      ? QUICK_MEMORY_REVIEW_BATCH_SIZE
      : Math.max(1, configuredLimit)
    const requestOffset = Math.max(0, reviewOffset)
    const params = new URLSearchParams({
      limit: String(reviewLimit),
      within_days: String(reviewWindowDays),
      offset: String(requestOffset),
      scope: 'due',
    })
    if (bookId) params.set('book_id', bookId)
    if (chapterId) params.set('chapter_id', chapterId)

    const data = await apiFetch<{ words?: Word[]; summary?: ReviewQueueSummary }>(
      `/api/ai/quick-memory/review-queue?${params.toString()}`,
    )
    if (isCancelled()) return

    const words = data.words || []
    const nextQueue = Array.from({ length: words.length }, (_, index) => index)
    const fallbackContext = buildQuickMemoryFallbackContext(words, data.summary)

    setVocabulary(words)
    vocabRef.current = words
    setQueue(nextQueue)
    queueRef.current = nextQueue
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    setReviewSummary(data.summary ?? null)
    setReviewContext(fallbackContext)
    setReviewQueueError(null)
    setQuickMemoryReviewQueueResolved(true)

    if (fallbackContext?.chapter_title) {
      setCurrentChapterTitle(fallbackContext.chapter_title)
    } else if (!bookId && !chapterId) {
      setCurrentChapterTitle('艾宾浩斯复习')
    }
  } catch {
    if (isCancelled()) return

    setReviewSummary(null)
    setReviewContext(null)
    setReviewQueueError('加载到期复习失败，请刷新后重试。')
    setQuickMemoryReviewQueueResolved(true)
    showToast?.('加载复习队列失败', 'error')
  }
}

interface LoadErrorModeDataOptions {
  user: unknown
  userId: string | number | null
  searchParams: URLSearchParams
  mode?: PracticeMode
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  setNoListeningPresets: Dispatch<SetStateAction<boolean>>
  setVocabulary: Dispatch<SetStateAction<Word[]>>
  vocabRef: MutableRefObject<Word[]>
  setQueue: Dispatch<SetStateAction<number[]>>
  queueRef: MutableRefObject<number[]>
  setErrorReviewRound: Dispatch<SetStateAction<number>>
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  errorProgressHydratedRef: MutableRefObject<boolean>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  showToast?: ToastFn
  isCancelled: () => boolean
}

export async function loadErrorModeData({
  user,
  userId,
  searchParams,
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
  beginSession,
  showToast,
  isCancelled,
}: LoadErrorModeDataOptions) {
  setResumeProgress(null)

  try {
    const wrongWords = await loadWrongWords({
      user,
      fetchRemote: () => apiFetch<{ words?: Word[] }>('/api/ai/wrong-words'),
    })
    if (isCancelled()) return

    const selectedWrongWordOrder = searchParams.get('selection') === 'manual'
      ? readWrongWordsReviewSelectionFromStorage(userId)
      : null
    const wrongWordsByKey = new Map(
      wrongWords
        .map(word => [normalizeOptionWordKey(word.word), word] as const)
        .filter((entry): entry is readonly [string, typeof wrongWords[number]] => Boolean(entry[0])),
    )
    const filteredWrongWords = selectedWrongWordOrder
      ? selectedWrongWordOrder
          .map(wordKey => wrongWordsByKey.get(wordKey))
          .filter((word): word is typeof wrongWords[number] => Boolean(word))
      : filterWrongWords(
          wrongWords,
          parseWrongWordsFiltersFromSearchParams(searchParams),
        )
    const savedWords: Word[] = filteredWrongWords.map(word => ({
      word: word.word,
      phonetic: word.phonetic,
      pos: word.pos,
      definition: word.definition,
      group_key: word.group_key,
      listening_confusables: word.listening_confusables,
      book_id: word.book_id,
      book_title: word.book_title,
      chapter_id: word.chapter_id,
      chapter_title: word.chapter_title,
      examples: word.examples,
    }))
    const words = filterVocabularyForMode(savedWords, mode)
    const indices = Array.from({ length: words.length }, (_, index) => index)
    const fallbackQueue = indices
    const candidateProgress = readWrongWordsProgress(mode, userId)
    const savedProgress = isWrongWordsProgressForWords(candidateProgress, words) ? candidateProgress : null
    const nextQueue = savedProgress?.is_completed
      ? fallbackQueue
      : buildWrongWordsQueue(words, savedProgress?.queue_words) ?? fallbackQueue

    setNoListeningPresets(mode === 'listening' && words.length === 0 && savedWords.length > 0)
    setVocabulary(words)
    vocabRef.current = words
    setQueue(nextQueue)
    queueRef.current = nextQueue
    setErrorReviewRound(savedProgress?.is_completed ? 1 : (savedProgress?.round ?? 1))
    errorRoundResultsRef.current = {}
    setQueueIndex(savedProgress?.is_completed ? 0 : Math.min(savedProgress?.current_index ?? 0, Math.max(nextQueue.length - 1, 0)))
    setCorrectCount(savedProgress?.is_completed ? 0 : (savedProgress?.correct_count ?? 0))
    setWrongCount(savedProgress?.is_completed ? 0 : (savedProgress?.wrong_count ?? 0))
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    errorProgressHydratedRef.current = true
    beginSession()
  } catch {
    if (!isCancelled()) {
      showToast?.('加载错词失败', 'error')
    }
  }
}

function buildQuickMemoryFallbackContext(
  words: Word[],
  summary?: ReviewQueueSummary,
): ReviewQueueContext | null {
  const selectedContext = summary?.selected_context ?? null
  if (selectedContext) {
    return selectedContext
  }

  const firstWord = words[0]
  if (!firstWord?.book_id || !firstWord.chapter_id || !firstWord.chapter_title) {
    return null
  }

  return {
    book_id: String(firstWord.book_id),
    book_title: String(firstWord.book_title ?? firstWord.book_id),
    chapter_id: String(firstWord.chapter_id),
    chapter_title: String(firstWord.chapter_title),
    due_count: summary?.due_count ?? 0,
    upcoming_count: summary?.upcoming_count ?? 0,
    total_count: summary?.total_count ?? words.length,
    next_review: Number(firstWord.nextReview ?? 0),
  }
}
