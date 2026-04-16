import { useEffect, useRef } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { Chapter, LastState, PracticeMode, ProgressData, Word, WordStatuses } from '../../../components/practice/types'
import { DEFAULT_SETTINGS } from '../../../constants'
import { apiFetch, buildApiUrl } from '../../../lib'
import { loadSmartStats, loadSmartStatsFromBackend, buildSmartQueue } from '../../../lib/smartMode'
import { filterWrongWords, parseWrongWordsFiltersFromSearchParams } from '../../../features/vocabulary/wrongWordsFilters'
import { loadWrongWords, readWrongWordsReviewSelectionFromStorage } from '../../../features/vocabulary/wrongWordsStore'
import { safeParse } from '../../../lib/validation'
import { LearnerProfileSchema, type LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'
import { shuffleArray } from '../../../components/practice/utils'
import { loadBookProgressSnapshot, loadChapterProgressSnapshot } from '../../../components/practice/progressStorage'
import {
  buildWrongWordsQueue, createResetProgressState, filterVocabularyForMode, normalizeOptionWordKey, readWrongWordsProgress,
  type ReviewQueueContext, type ReviewQueueSummary,
} from '../../../components/practice/page/practicePageHelpers'
import type { ErrorReviewRoundResults } from '../../../components/practice/errorReviewSession'

const QUICK_MEMORY_REVIEW_BATCH_SIZE = 100

interface UsePracticePageDataParams {
  user: unknown
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
  searchParams: URLSearchParams
  settings: {
    shuffle?: boolean
    reviewInterval?: string
    reviewLimit?: string
  }
  navigate: (to: string) => void
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
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
  vocabRef: MutableRefObject<Word[]>
  queueRef: MutableRefObject<number[]>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  errorProgressHydratedRef: MutableRefObject<boolean>
  errorRoundResultsRef: MutableRefObject<ErrorReviewRoundResults>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  onListeningModeFallback: () => void
}

export function usePracticePageData({
  user,
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
  searchParams,
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
  vocabRef,
  queueRef,
  wordsLearnedBaselineRef,
  uniqueAnsweredRef,
  errorProgressHydratedRef,
  errorRoundResultsRef,
  beginSession,
  onListeningModeFallback,
}: UsePracticePageDataParams) {
  const scopedLoadGenerationRef = useRef(0)
  const activeScopedLoadKeyRef = useRef<string | null>(null)
  const lastAppliedScopedLoadRef = useRef<{ key: string | null; generation: number }>({
    key: null,
    generation: 0,
  })
  const scopedQueueWordsCacheRef = useRef<Record<string, string[]>>({})

  useEffect(() => {
    if (!resolvedPracticeBookId) {
      setBookChapters([])
      return
    }

    let cancelled = false

    fetch(buildApiUrl(`/api/books/${resolvedPracticeBookId}/chapters`))
      .then(r => r.json())
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
    errorProgressHydratedRef.current = false
    setNoListeningPresets(false)
    setReviewQueueError(null)
    const scopedLoadKey = reviewMode || errorMode
      ? null
      : JSON.stringify({
          currentDay: currentDay ?? null,
          mode: mode ?? null,
          bookId,
          chapterId,
          shuffle: settings.shuffle ?? null,
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
      setResumeProgress(null)
      setQuickMemoryReviewQueueResolved(false)
      void (async () => {
        try {
          const reviewWindowDays = Math.max(1, parseInt(String(settings.reviewInterval ?? '1'), 10) || 1)
          const configuredLimit = settings.reviewLimit === 'unlimited' ? 0 : (parseInt(String(settings.reviewLimit ?? DEFAULT_SETTINGS.reviewLimit), 10) || parseInt(DEFAULT_SETTINGS.reviewLimit, 10))
          const reviewLimit = configuredLimit === 0
            ? QUICK_MEMORY_REVIEW_BATCH_SIZE
            : Math.max(1, configuredLimit)
          const params = new URLSearchParams({
            limit: String(reviewLimit),
            within_days: String(reviewWindowDays),
            offset: String(reviewOffset),
            scope: 'due',
          })
          if (bookId) params.set('book_id', bookId)
          if (chapterId) params.set('chapter_id', chapterId)
          const data = await apiFetch<{ words?: Word[]; summary?: ReviewQueueSummary }>(
            `/api/ai/quick-memory/review-queue?${params.toString()}`,
          )
          if (cancelled) return

          const words = data.words || []
          const nextQueue = Array.from({ length: words.length }, (_, index) => index)
          const selectedContext = data.summary?.selected_context ?? null
          const fallbackContext = selectedContext ?? (
            words[0]?.book_id && words[0]?.chapter_id && words[0]?.chapter_title
              ? {
                  book_id: String(words[0].book_id),
                  book_title: String(words[0].book_title ?? words[0].book_id),
                  chapter_id: String(words[0].chapter_id),
                  chapter_title: String(words[0].chapter_title),
                  due_count: data.summary?.due_count ?? 0,
                  upcoming_count: data.summary?.upcoming_count ?? 0,
                  total_count: data.summary?.total_count ?? words.length,
                  next_review: Number(words[0].nextReview ?? 0),
                }
              : null
          )

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
          if (!cancelled) {
            setReviewSummary(null)
            setReviewContext(null)
            setReviewQueueError('加载到期复习失败，请刷新后重试。')
            setQuickMemoryReviewQueueResolved(true)
            showToast?.('加载复习队列失败', 'error')
          }
        }
      })()

      return () => {
        cancelled = true
      }
    }

    if (reviewMode) return

    const buildQueue = (words: Word[]) => {
      const indices = Array.from({ length: words.length }, (_, index) => index)
      if (mode === 'smart') return buildSmartQueue(words.map(word => word.word), loadSmartStats())
      return settings.shuffle !== false ? shuffleArray(indices) : indices
    }
    const resolveWordsForMode = (rawWords: Word[]) => {
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
    const resetProgress = (progress: ProgressData | null, words: Word[]) => {
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

    if (errorMode) {
      setResumeProgress(null)
      void (async () => {
        try {
          const wrongWords = await loadWrongWords({
            user,
            fetchRemote: () => apiFetch<{ words?: Word[] }>('/api/ai/wrong-words'),
          })
          if (cancelled) return

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
          const fallbackQueue = settings.shuffle !== false ? shuffleArray(indices) : indices
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
          if (!cancelled) showToast?.('加载错词失败', 'error')
        }
      })()

      return () => {
        cancelled = true
      }
    }

    const loadScopedWords = async (words: Word[], progress: ProgressData | null) => {
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
        ?? buildQueue(words)
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
      resetProgress(progress, words)
      lastAppliedScopedLoadRef.current = {
        key: scopedLoadKey,
        generation: scopedLoadGeneration,
      }
      beginSession()
    }

    if (bookId && chapterId) {
      fetch(buildApiUrl(`/api/books/${bookId}/chapters/${chapterId}`))
        .then(res => res.json())
        .then(async (data: { words?: Word[] }) => {
          if (!canApplyScopedLoad()) return
          const rawWords = data.words || []
          const words = resolveWordsForMode(rawWords)
          if (!words || !canApplyScopedLoad()) return
          const progress = await loadChapterProgressSnapshot(bookId, chapterId)
          if (!canApplyScopedLoad()) return
          await loadScopedWords(words, progress)
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
      fetch(buildApiUrl(`/api/books/${bookId}/words?per_page=100`))
        .then(res => res.json())
        .then(async (data: { words?: Word[] }) => {
          if (!canApplyScopedLoad()) return
          const rawWords = data.words || []
          const words = resolveWordsForMode(rawWords)
          if (!words || !canApplyScopedLoad()) return
          const progress = await loadBookProgressSnapshot(bookId)
          if (!canApplyScopedLoad()) return
          await loadScopedWords(words, progress)
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

    fetch(buildApiUrl(`/api/vocabulary/day/${currentDay}`))
      .then(res => res.json())
      .then(async (data: { vocabulary?: Word[]; words?: Word[] }) => {
        if (!canApplyScopedLoad()) return
        const rawWords = data.vocabulary || data.words || []
        const words = resolveWordsForMode(rawWords)
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
        await loadScopedWords(words, progress)
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
    beginSession,
    bookId,
    chapterId,
    currentDay,
    errorMode,
    isCustomPracticeScope,
    errorProgressHydratedRef,
    errorRoundResultsRef,
    mode,
    navigate,
    onListeningModeFallback,
    queueRef,
    reviewMode,
    reviewOffset,
    searchParams,
    setResumeProgress,
    setCorrectCount,
    setCurrentChapterTitle,
    setErrorReviewRound,
    setLastState,
    setNoListeningPresets,
    setPreviousWord,
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
    settings.shuffle,
    showToast,
    uniqueAnsweredRef,
    user,
    userId,
    vocabRef,
    wordsLearnedBaselineRef,
  ])
}
