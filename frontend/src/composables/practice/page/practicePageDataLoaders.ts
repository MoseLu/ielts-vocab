import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { LastState, PracticeMode, ProgressData, Word, WordStatuses } from '../../../components/practice/types'
import { DEFAULT_SETTINGS } from '../../../constants'
import { apiFetch } from '../../../lib'
import { loadSmartStats, buildSmartQueue } from '../../../lib/smartMode'
import { filterWrongWords, parseWrongWordsFiltersFromSearchParams } from '../../../features/vocabulary/wrongWordsFilters'
import { loadWrongWords, readWrongWordsReviewSelectionFromStorage } from '../../../features/vocabulary/wrongWordsStore'
import { shuffleArray } from '../../../components/practice/utils'
import {
  buildWrongWordsQueue,
  createResetProgressState,
  filterVocabularyForMode,
  normalizeOptionWordKey,
  readWrongWordsProgress,
  type ReviewQueueContext,
  type ReviewQueueSummary,
} from '../../../components/practice/page/practicePageHelpers'
import type { ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'

const QUICK_MEMORY_REVIEW_BATCH_SIZE = 100

type ToastFn = (message: string, type?: 'success' | 'error' | 'info') => void

interface ScopedLoadStateRef {
  key: string | null
  generation: number
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
  shuffle?: boolean
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
  shuffle,
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

    const selectedWrongWordKeys = searchParams.get('selection') === 'manual'
      ? new Set(readWrongWordsReviewSelectionFromStorage(userId))
      : null
    const filteredWrongWords = selectedWrongWordKeys
      ? wrongWords.filter(word => {
          const key = normalizeOptionWordKey(word.word)
          return key ? selectedWrongWordKeys.has(key) : false
        })
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
    const fallbackQueue = shuffle !== false ? shuffleArray(indices) : indices
    const savedProgress = selectedWrongWordKeys ? null : readWrongWordsProgress(mode, userId)
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

interface ResolvePracticeWordsForModeOptions {
  rawWords: Word[]
  mode?: PracticeMode
  isCustomPracticeScope: boolean
  setNoListeningPresets: Dispatch<SetStateAction<boolean>>
  onListeningModeFallback: () => void
}

export function resolvePracticeWordsForMode({
  rawWords,
  mode,
  isCustomPracticeScope,
  setNoListeningPresets,
  onListeningModeFallback,
}: ResolvePracticeWordsForModeOptions): Word[] | null {
  const words = filterVocabularyForMode(rawWords, mode)
  const listeningUnavailable = mode === 'listening' && words.length === 0 && rawWords.length > 0

  if (listeningUnavailable && isCustomPracticeScope) {
    setNoListeningPresets(false)
    onListeningModeFallback()
    return null
  }

  setNoListeningPresets(listeningUnavailable)
  return words
}

interface ApplyScopedWordsLoadOptions {
  words: Word[]
  progress: ProgressData | null
  chapterId: string | null
  mode?: PracticeMode
  shuffle?: boolean
  scopedLoadKey: string | null
  scopedLoadGeneration: number
  canApplyScopedLoad: () => boolean
  lastAppliedScopedLoadRef: MutableRefObject<ScopedLoadStateRef>
  scopedQueueWordsCacheRef: MutableRefObject<Record<string, string[]>>
  queueRef: MutableRefObject<number[]>
  vocabRef: MutableRefObject<Word[]>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  setVocabulary: Dispatch<SetStateAction<Word[]>>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
}

export function applyScopedWordsLoad({
  words,
  progress,
  chapterId,
  mode,
  shuffle,
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
}: ApplyScopedWordsLoadOptions) {
  const cachedQueueWords = scopedLoadKey != null
    ? scopedQueueWordsCacheRef.current[scopedLoadKey]
    : undefined
  const previousQueueWords = lastAppliedScopedLoadRef.current.key === scopedLoadKey
    ? queueRef.current
      .map(index => vocabRef.current[index]?.word)
      .filter((word): word is string => Boolean(word))
    : []
  const nextQueue = buildWrongWordsQueue(words, progress?.queue_words)
    ?? (cachedQueueWords?.length ? buildWrongWordsQueue(words, cachedQueueWords) : null)
    ?? (previousQueueWords.length ? buildWrongWordsQueue(words, previousQueueWords) : null)
    ?? buildModeQueue(words, mode, shuffle)

  if (scopedLoadKey != null) {
    scopedQueueWordsCacheRef.current[scopedLoadKey] = nextQueue
      .map(index => words[index]?.word)
      .filter((word): word is string => Boolean(word))
  }

  if (!canApplyScopedLoad()) return

  queueRef.current = nextQueue
  setVocabulary(words)
  vocabRef.current = words
  setQueue(nextQueue)
  resetScopedProgress({
    progress,
    words,
    chapterId,
    queueRef,
    wordsLearnedBaselineRef,
    uniqueAnsweredRef,
    setResumeProgress,
    setQueueIndex,
    setCorrectCount,
    setWrongCount,
    setPreviousWord,
    setLastState,
    setWordStatuses,
  })
  lastAppliedScopedLoadRef.current = {
    key: scopedLoadKey,
    generation: scopedLoadGeneration,
  }
  beginSession()
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

function buildModeQueue(words: Word[], mode?: PracticeMode, shuffle?: boolean) {
  const indices = Array.from({ length: words.length }, (_, index) => index)
  if (mode === 'smart') {
    return buildSmartQueue(words.map(word => word.word), loadSmartStats())
  }

  return shuffle !== false ? shuffleArray(indices) : indices
}

interface ResetScopedProgressOptions {
  progress: ProgressData | null
  words: Word[]
  chapterId: string | null
  queueRef: MutableRefObject<number[]>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
}

function resetScopedProgress({
  progress,
  words,
  chapterId,
  queueRef,
  wordsLearnedBaselineRef,
  uniqueAnsweredRef,
  setResumeProgress,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setWordStatuses,
}: ResetScopedProgressOptions) {
  if (!progress) {
    setResumeProgress(null)
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    wordsLearnedBaselineRef.current = 0
    uniqueAnsweredRef.current = new Set()
    return
  }

  const restored = createResetProgressState(queueRef.current.length, progress, chapterId, words.length)
  setQueueIndex(restored.queueIndex)
  setCorrectCount(restored.correctCount)
  setWrongCount(restored.wrongCount)
  setPreviousWord(null)
  setLastState(null)
  setWordStatuses({})
  setResumeProgress(progress.is_completed ? null : progress)
  wordsLearnedBaselineRef.current = restored.wordsLearnedBaseline
  uniqueAnsweredRef.current = restored.answeredWords
}
