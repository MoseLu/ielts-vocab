import { useCallback, useEffect } from 'react'
import type { MutableRefObject } from 'react'
import { apiFetch } from '../../../lib'
import {
  persistBookProgressSnapshot,
  persistChapterProgressSnapshot,
} from '../../../features/practice/progressStorage'
import { persistWrongWordsProgress } from '../../../features/practice/practiceSessionHelpers'
import type { PracticeMode, Word } from '../../../features/practice/types'

interface UsePracticeProgressPersistenceParams {
  mode?: PracticeMode
  currentDay?: number
  userId: string | number | null
  bookId: string | null
  chapterId: string | null
  errorMode: boolean
  queue: number[]
  queueIndex: number
  vocabulary: Word[]
  errorReviewRound: number
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  computeChapterWordsLearned: (cap: number) => number
  correctCountRef: MutableRefObject<number>
  wrongCountRef: MutableRefObject<number>
  chapterCorrectBaselineRef: MutableRefObject<number>
  chapterWrongBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  chapterGroupStartRef: MutableRefObject<number>
  chapterQueueWordsRef: MutableRefObject<string[]>
  errorProgressHydratedRef: MutableRefObject<boolean>
}

export function usePracticeProgressPersistence({
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
}: UsePracticeProgressPersistenceParams) {
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
    const chapterQueueWords = chapterQueueWordsRef.current.length
      ? chapterQueueWordsRef.current
      : queueWords
    const chapterQueueLength = chapterQueueWords.length || vocabulary.length
    const chapterCurrentIndex = chapterId
      ? Math.min(chapterGroupStartRef.current + nextIndex, chapterQueueLength)
      : nextIndex

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
      && chapterCurrentIndex >= chapterQueueLength,
    )
    const progressData = {
      current_index: chapterId ? chapterCurrentIndex : nextIndex,
      correct_count: correct,
      wrong_count: wrong,
      is_completed: chapterId ? chapterDone : (advanceToNext && correct + wrong >= vocabulary.length),
    }

    if (bookId && !chapterId) {
      persistBookProgressSnapshot(bookId, progressData, queueWords)
      apiFetch('/api/books/progress', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId, mode, ...progressData }),
      }).catch(() => showToast?.('进度保存失败，请检查网络连接', 'error'))
      return
    }

    if (bookId && chapterId) {
      const answeredWords = Array.from(uniqueAnsweredRef.current)
      const wordsLearned = computeChapterWordsLearned(vocabulary.length)
      const cumulativeCorrect = chapterCorrectBaselineRef.current + correct
      const cumulativeWrong = chapterWrongBaselineRef.current + wrong
      const chapterProgress = {
        ...progressData,
        correct_count: cumulativeCorrect,
        wrong_count: cumulativeWrong,
        words_learned: wordsLearned,
        answered_words: answeredWords,
        queue_words: chapterQueueWords,
      }
      persistChapterProgressSnapshot(bookId, chapterId, chapterProgress)
      apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
        method: 'POST',
        body: JSON.stringify({ mode, ...chapterProgress }),
      }).catch(() => {})

      if (mode && correct + wrong > 0) {
        apiFetch(`/api/books/${bookId}/chapters/${chapterId}/mode-progress`, {
          method: 'POST',
          body: JSON.stringify({
            mode,
            correct_count: cumulativeCorrect,
            wrong_count: cumulativeWrong,
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
    chapterGroupStartRef,
    chapterQueueWordsRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
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

  return saveProgress
}
