import { useCallback } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import { apiFetch } from '../../../lib'
import { persistChapterProgressSnapshot } from '../../../features/practice/progressStorage'
import { buildWrongWordsQueue } from '../../../features/practice/practiceSessionHelpers'
import type { AppSettings, PracticeMode, Word } from '../../../features/practice/types'
import {
  resolvePracticeGroupSize,
  resolvePracticeGroupWindow,
  sliceQueueForPracticeGroup,
  type PracticeGroupWindow,
} from './practicePageGrouping'

interface UsePracticeChapterProgressResetParams {
  mode?: PracticeMode
  bookId: string | null
  chapterId: string | null
  queue: number[]
  vocabulary: Word[]
  settings: AppSettings
  showToast?: (message: string, type?: 'success' | 'error' | 'info') => void
  chapterGroupStartRef: MutableRefObject<number>
  chapterQueueWordsRef: MutableRefObject<string[]>
  chapterCorrectBaselineRef: MutableRefObject<number>
  chapterWrongBaselineRef: MutableRefObject<number>
  queueRef: MutableRefObject<number[]>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setPracticeGroup: Dispatch<SetStateAction<PracticeGroupWindow | null>>
}

export function usePracticeChapterProgressReset({
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
}: UsePracticeChapterProgressResetParams) {
  return useCallback(async () => {
    if (!bookId || !chapterId) return

    const queueWords = queue
      .map(index => vocabulary[index]?.word)
      .filter((word): word is string => Boolean(word))
    const fullQueue = buildWrongWordsQueue(vocabulary, chapterQueueWordsRef.current) ?? queue
    const firstGroup = resolvePracticeGroupWindow(fullQueue.length, resolvePracticeGroupSize(settings), 0)
    const resetQueue = sliceQueueForPracticeGroup(fullQueue, firstGroup)
    const resetQueueWords = chapterQueueWordsRef.current.length
      ? chapterQueueWordsRef.current
      : queueWords
    const resetSnapshot = {
      current_index: 0,
      correct_count: 0,
      wrong_count: 0,
      is_completed: false,
      words_learned: 0,
      answered_words: [],
      queue_words: resetQueueWords,
    }

    chapterGroupStartRef.current = firstGroup?.start ?? 0
    chapterCorrectBaselineRef.current = 0
    chapterWrongBaselineRef.current = 0
    setPracticeGroup(firstGroup)
    setQueue(resetQueue)
    queueRef.current = resetQueue
    setQueueIndex(0)
    persistChapterProgressSnapshot(bookId, chapterId, resetSnapshot)

    try {
      await apiFetch(`/api/books/${bookId}/chapters/${chapterId}/progress`, {
        method: 'POST',
        body: JSON.stringify({ mode, ...resetSnapshot }),
      })
    } catch {
      showToast?.('重置进度失败，请检查网络连接', 'error')
    }
  }, [
    bookId,
    chapterId,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    chapterCorrectBaselineRef,
    chapterWrongBaselineRef,
    mode,
    queue,
    queueRef,
    setPracticeGroup,
    setQueue,
    setQueueIndex,
    settings,
    showToast,
    vocabulary,
  ])
}
