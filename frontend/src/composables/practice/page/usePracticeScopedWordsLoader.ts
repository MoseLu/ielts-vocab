import { useEffect, useRef } from 'react'
import type { MutableRefObject } from 'react'
import type { ProgressData, Word } from '../../../features/practice/types'
import { loadBookProgressSnapshot, loadChapterProgressSnapshot } from '../../../features/practice/progressStorage'
import { apiFetch } from '../../../lib'
import { buildCanonicalWordListPath } from './practicePageDataLoaders'
import { resolvePracticeGroupSize } from './practicePageGrouping'
import { applyScopedWordsLoad, resolvePracticeWordsForMode } from './practicePageScopedLoad'
import type { UsePracticePageDataParams } from './practicePageDataTypes'

export function usePracticeScopedWordsLoader({
  currentDay,
  mode,
  bookId,
  chapterId,
  reviewMode,
  errorMode,
  isCustomPracticeScope,
  searchParamsKey,
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
  setWordStatuses,
  setResumeProgress,
  setReviewQueueError,
  setNoListeningPresets,
  setPracticeGroup,
  vocabRef,
  queueRef,
  chapterGroupStartRef,
  chapterQueueWordsRef,
  wordsLearnedBaselineRef,
  chapterCorrectBaselineRef,
  chapterWrongBaselineRef,
  uniqueAnsweredRef,
  errorProgressHydratedRef,
  beginSession,
  onListeningModeFallback,
}: UsePracticePageDataParams) {
  const scopedLoadGenerationRef = useRef(0)
  const activeScopedLoadKeyRef = useRef<string | null>(null)
  const lastAppliedScopedLoadRef = useRef<{ key: string | null; generation: number }>({ key: null, generation: 0 })
  const scopedQueueWordsCacheRef = useRef<Record<string, string[]>>({})
  const runtimeRefs = useRef({ beginSession, onListeningModeFallback, showToast })
  runtimeRefs.current = { beginSession, onListeningModeFallback, showToast }

  useEffect(() => {
    const currentSearchParams = new URLSearchParams(searchParamsKey)
    const restartRequested = currentSearchParams.get('restart') === '1'
    errorProgressHydratedRef.current = false
    setNoListeningPresets(false)
    setReviewQueueError(null)
    const chapterGroupSize = bookId && chapterId
      ? resolvePracticeGroupSize(settings)
      : null
    if (reviewMode || errorMode || !chapterId) {
      chapterGroupStartRef.current = 0
      chapterQueueWordsRef.current = []
      setPracticeGroup(null)
    }
    const scopedLoadKey = reviewMode || errorMode
      ? null
      : JSON.stringify({
          currentDay: currentDay ?? null,
          mode: mode ?? null,
          bookId,
          chapterId,
          shuffle: settings.shuffle ?? null,
          chapterGroupSize,
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
    const shared = {
      settings,
      lastAppliedScopedLoadRef,
      scopedQueueWordsCacheRef,
      queueRef,
      vocabRef,
      chapterGroupStartRef,
      chapterQueueWordsRef,
      wordsLearnedBaselineRef,
      chapterCorrectBaselineRef,
      chapterWrongBaselineRef,
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
      setNoListeningPresets,
      setPracticeGroup,
      beginSession: runtimeRefs.current.beginSession,
      onListeningModeFallback: runtimeRefs.current.onListeningModeFallback,
      showToast: runtimeRefs.current.showToast,
    }

    if (reviewMode || errorMode) return

    if (bookId && chapterId) {
      loadChapterWords({
        bookId,
        chapterId,
        mode,
        isCustomPracticeScope,
        restartRequested,
        chapterGroupSize,
        scopedLoadKey,
        scopedLoadGeneration,
        canApplyScopedLoad,
        shared,
      })
      return
    }

    if (bookId) {
      setResumeProgress(null)
      loadBookWords({
        bookId,
        chapterId,
        mode,
        isCustomPracticeScope,
        restartRequested,
        scopedLoadKey,
        scopedLoadGeneration,
        canApplyScopedLoad,
        shared,
      })
      return
    }

    if (!currentDay) {
      setResumeProgress(null)
      navigate('/plan')
      return
    }

    loadDayWords({
      currentDay,
      chapterId,
      mode,
      isCustomPracticeScope,
      scopedLoadKey,
      scopedLoadGeneration,
      canApplyScopedLoad,
      shared,
    })
  }, [
    bookId,
    chapterId,
    currentDay,
    errorMode,
    isCustomPracticeScope,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
    errorProgressHydratedRef,
    mode,
    navigate,
    queueRef,
    reviewMode,
    searchParamsKey,
    setCorrectCount,
    setLastState,
    setNoListeningPresets,
    setPracticeGroup,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    setResumeProgress,
    setReviewQueueError,
    setVocabulary,
    setWordStatuses,
    setWrongCount,
    settings.reviewInterval,
    settings.reviewLimit,
    settings.reviewLimitCustomized,
    settings.shuffle,
    uniqueAnsweredRef,
    vocabRef,
    wordsLearnedBaselineRef,
  ])
}

interface LoadWordsOptions {
  mode?: UsePracticePageDataParams['mode']
  chapterId: string | null
  isCustomPracticeScope: boolean
  scopedLoadKey: string | null
  scopedLoadGeneration: number
  canApplyScopedLoad: () => boolean
  shared: SharedScopedLoadOptions
}

interface LoadChapterWordsOptions extends LoadWordsOptions {
  bookId: string
  chapterId: string
  restartRequested: boolean
  chapterGroupSize: number | null
}

function loadChapterWords({
  bookId,
  chapterId,
  mode,
  isCustomPracticeScope,
  restartRequested,
  chapterGroupSize,
  scopedLoadKey,
  scopedLoadGeneration,
  canApplyScopedLoad,
  shared,
}: LoadChapterWordsOptions) {
  apiFetch<{ words?: Word[] }>(buildCanonicalWordListPath(bookId, chapterId))
    .then(async (data: { words?: Word[] }) => {
      if (!canApplyScopedLoad()) return
      const words = resolveLoadedWords(data.words || [], mode, isCustomPracticeScope, shared)
      if (!words || !canApplyScopedLoad()) return
      const progress = restartRequested ? null : await loadChapterProgressSnapshot(bookId, chapterId)
      if (!canApplyScopedLoad()) return
      applyLoadedWords(words, progress, {
        chapterId,
        mode,
        shuffle: false,
        groupSize: chapterGroupSize,
        scopedLoadKey,
        scopedLoadGeneration,
        canApplyScopedLoad,
        shared,
      })
    })
    .catch(() => {
      if (canApplyScopedLoad()) {
        shared.showToast?.('加载章节词汇失败', 'error')
      }
    })
}

interface LoadBookWordsOptions extends LoadWordsOptions {
  bookId: string
  restartRequested: boolean
}

function loadBookWords({
  bookId,
  chapterId,
  mode,
  isCustomPracticeScope,
  restartRequested,
  scopedLoadKey,
  scopedLoadGeneration,
  canApplyScopedLoad,
  shared,
}: LoadBookWordsOptions) {
  apiFetch<{ words?: Word[] }>(buildCanonicalWordListPath(bookId))
    .then(async (data: { words?: Word[] }) => {
      if (!canApplyScopedLoad()) return
      const words = resolveLoadedWords(data.words || [], mode, isCustomPracticeScope, shared)
      if (!words || !canApplyScopedLoad()) return
      const progress = restartRequested ? null : await loadBookProgressSnapshot(bookId)
      if (!canApplyScopedLoad()) return
      applyLoadedWords(words, progress, {
        chapterId,
        mode,
        shuffle: false,
        groupSize: null,
        scopedLoadKey,
        scopedLoadGeneration,
        canApplyScopedLoad,
        shared,
      })
    })
    .catch(() => {
      if (canApplyScopedLoad()) {
        shared.showToast?.('加载词书失败', 'error')
      }
    })
}

interface LoadDayWordsOptions extends LoadWordsOptions {
  currentDay: number
}

function loadDayWords({
  currentDay,
  chapterId,
  mode,
  isCustomPracticeScope,
  scopedLoadKey,
  scopedLoadGeneration,
  canApplyScopedLoad,
  shared,
}: LoadDayWordsOptions) {
  apiFetch<{ vocabulary?: Word[]; words?: Word[] }>(`/api/vocabulary/day/${currentDay}`)
    .then(async (data: { vocabulary?: Word[]; words?: Word[] }) => {
      if (!canApplyScopedLoad()) return
      const rawWords = data.vocabulary || data.words || []
      const words = resolveLoadedWords(rawWords, mode, isCustomPracticeScope, shared)
      if (!words || !canApplyScopedLoad()) return
      const progress = await loadDayProgress(currentDay, canApplyScopedLoad)
      if (!canApplyScopedLoad()) return
      applyLoadedWords(words, progress, {
        chapterId,
        mode,
        shuffle: shared.settings.shuffle,
        groupSize: null,
        scopedLoadKey,
        scopedLoadGeneration,
        canApplyScopedLoad,
        shared,
      })
    })
    .catch(() => {
      if (canApplyScopedLoad()) {
        shared.showToast?.('加载词汇失败', 'error')
      }
    })
}

function resolveLoadedWords(
  rawWords: Word[],
  mode: UsePracticePageDataParams['mode'],
  isCustomPracticeScope: boolean,
  shared: SharedScopedLoadOptions,
) {
  return resolvePracticeWordsForMode({
    rawWords,
    mode,
    isCustomPracticeScope,
    setNoListeningPresets: shared.setNoListeningPresets,
    onListeningModeFallback: shared.onListeningModeFallback,
  })
}

interface ApplyLoadedWordsOptions {
  chapterId: string | null
  mode?: UsePracticePageDataParams['mode']
  shuffle?: boolean
  groupSize: number | null
  scopedLoadKey: string | null
  scopedLoadGeneration: number
  canApplyScopedLoad: () => boolean
  shared: SharedScopedLoadOptions
}

function applyLoadedWords(
  words: Word[],
  progress: ProgressData | null,
  {
    chapterId,
    mode,
    shuffle,
    groupSize,
    scopedLoadKey,
    scopedLoadGeneration,
    canApplyScopedLoad,
    shared,
  }: ApplyLoadedWordsOptions,
) {
  applyScopedWordsLoad({
    words,
    progress,
    chapterId,
    mode,
    shuffle,
    groupSize,
    scopedLoadKey,
    scopedLoadGeneration,
    canApplyScopedLoad,
    lastAppliedScopedLoadRef: shared.lastAppliedScopedLoadRef,
    scopedQueueWordsCacheRef: shared.scopedQueueWordsCacheRef,
    queueRef: shared.queueRef,
    vocabRef: shared.vocabRef,
    chapterGroupStartRef: shared.chapterGroupStartRef,
    chapterQueueWordsRef: shared.chapterQueueWordsRef,
    wordsLearnedBaselineRef: shared.wordsLearnedBaselineRef,
    chapterCorrectBaselineRef: shared.chapterCorrectBaselineRef,
    chapterWrongBaselineRef: shared.chapterWrongBaselineRef,
    uniqueAnsweredRef: shared.uniqueAnsweredRef,
    setVocabulary: shared.setVocabulary,
    setQueue: shared.setQueue,
    setQueueIndex: shared.setQueueIndex,
    setCorrectCount: shared.setCorrectCount,
    setWrongCount: shared.setWrongCount,
    setPreviousWord: shared.setPreviousWord,
    setLastState: shared.setLastState,
    setWordStatuses: shared.setWordStatuses,
    setResumeProgress: shared.setResumeProgress,
    setPracticeGroup: shared.setPracticeGroup,
    beginSession: shared.beginSession,
  })
}

async function loadDayProgress(
  currentDay: number,
  canApplyScopedLoad: () => boolean,
): Promise<ProgressData | null> {
  const saved: Record<string, ProgressData> = JSON.parse(localStorage.getItem('day_progress') || '{}')
  const savedProgress = saved[String(currentDay)] ?? null
  if (savedProgress) return savedProgress

  try {
    const remote = await apiFetch<{
      progress?: Array<{
        day: number
        current_index: number
        correct_count: number
        wrong_count: number
        is_completed?: boolean
      }>
    }>('/api/progress')
    if (!canApplyScopedLoad()) return null
    const entry = remote.progress?.find(item => item.day === currentDay)
    return entry
      ? {
          current_index: entry.current_index,
          correct_count: entry.correct_count,
          wrong_count: entry.wrong_count,
          is_completed: Boolean(entry.is_completed),
        }
      : null
  } catch {
    return null
  }
}

type SharedScopedLoadOptions = Pick<
  UsePracticePageDataParams,
  | 'settings'
  | 'queueRef'
  | 'vocabRef'
  | 'chapterGroupStartRef'
  | 'chapterQueueWordsRef'
  | 'wordsLearnedBaselineRef'
  | 'chapterCorrectBaselineRef'
  | 'chapterWrongBaselineRef'
  | 'uniqueAnsweredRef'
  | 'setVocabulary'
  | 'setQueue'
  | 'setQueueIndex'
  | 'setCorrectCount'
  | 'setWrongCount'
  | 'setPreviousWord'
  | 'setLastState'
  | 'setWordStatuses'
  | 'setResumeProgress'
  | 'setNoListeningPresets'
  | 'setPracticeGroup'
  | 'beginSession'
  | 'onListeningModeFallback'
  | 'showToast'
> & {
  lastAppliedScopedLoadRef: MutableRefObject<{ key: string | null; generation: number }>
  scopedQueueWordsCacheRef: MutableRefObject<Record<string, string[]>>
}
