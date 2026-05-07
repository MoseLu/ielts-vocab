import { useCallback } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type { LastState, Word, WordStatuses } from '../../../features/practice/types'
import { buildWrongWordsQueue } from '../../../features/practice/practiceSessionHelpers'
import {
  resolvePracticeGroupWindow,
  sliceQueueForPracticeGroup,
  type PracticeGroupWindow,
} from './practicePageGrouping'

interface UsePracticeChapterGroupControlsParams {
  bookId: string | null
  chapterId: string | null
  practiceGroup: PracticeGroupWindow | null
  vocabulary: Word[]
  queueRef: MutableRefObject<number[]>
  chapterGroupStartRef: MutableRefObject<number>
  chapterQueueWordsRef: MutableRefObject<string[]>
  completedSessionDurationSecondsRef: MutableRefObject<number | null>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  setPracticeGroup: Dispatch<SetStateAction<PracticeGroupWindow | null>>
  setQueue: Dispatch<SetStateAction<number[]>>
  setQueueIndex: Dispatch<SetStateAction<number>>
  setCorrectCount: Dispatch<SetStateAction<number>>
  setWrongCount: Dispatch<SetStateAction<number>>
  setPreviousWord: Dispatch<SetStateAction<Word | null>>
  setLastState: Dispatch<SetStateAction<LastState | null>>
  setWordStatuses: Dispatch<SetStateAction<WordStatuses>>
  setSelectedAnswer: Dispatch<SetStateAction<number | null>>
  setWrongSelections: Dispatch<SetStateAction<number[]>>
  setShowResult: Dispatch<SetStateAction<boolean>>
  setSpellingInput: Dispatch<SetStateAction<string>>
  setSpellingResult: Dispatch<SetStateAction<'correct' | 'wrong' | null>>
  setSpellingFeedbackLocked: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackDismissing: Dispatch<SetStateAction<boolean>>
  setSpellingFeedbackSnapshot: Dispatch<SetStateAction<string | null>>
}

export function usePracticeChapterGroupControls({
  bookId,
  chapterId,
  practiceGroup,
  vocabulary,
  queueRef,
  chapterGroupStartRef,
  chapterQueueWordsRef,
  completedSessionDurationSecondsRef,
  beginSession,
  setPracticeGroup,
  setQueue,
  setQueueIndex,
  setCorrectCount,
  setWrongCount,
  setPreviousWord,
  setLastState,
  setWordStatuses,
  setSelectedAnswer,
  setWrongSelections,
  setShowResult,
  setSpellingInput,
  setSpellingResult,
  setSpellingFeedbackLocked,
  setSpellingFeedbackDismissing,
  setSpellingFeedbackSnapshot,
}: UsePracticeChapterGroupControlsParams) {
  return useCallback(() => {
    if (!practiceGroup?.groupSize || practiceGroup.end >= practiceGroup.total) return
    const fullQueue = buildWrongWordsQueue(vocabulary, chapterQueueWordsRef.current)
      ?? Array.from({ length: vocabulary.length }, (_, index) => index)
    const nextGroup = resolvePracticeGroupWindow(fullQueue.length, practiceGroup.groupSize, practiceGroup.end)
    const nextQueue = sliceQueueForPracticeGroup(fullQueue, nextGroup)
    if (!nextGroup || !nextQueue.length || nextGroup.start <= practiceGroup.start) return

    chapterGroupStartRef.current = nextGroup.start
    setPracticeGroup(nextGroup)
    queueRef.current = nextQueue
    setQueue(nextQueue)
    setQueueIndex(0)
    setCorrectCount(0)
    setWrongCount(0)
    setPreviousWord(null)
    setLastState(null)
    setWordStatuses({})
    setSelectedAnswer(null)
    setWrongSelections([])
    setShowResult(false)
    setSpellingInput('')
    setSpellingResult(null)
    setSpellingFeedbackLocked(false)
    setSpellingFeedbackDismissing(false)
    setSpellingFeedbackSnapshot(null)
    completedSessionDurationSecondsRef.current = null
    beginSession({ bookId, chapterId })
  }, [
    beginSession,
    bookId,
    chapterId,
    chapterGroupStartRef,
    chapterQueueWordsRef,
    completedSessionDurationSecondsRef,
    practiceGroup,
    queueRef,
    setCorrectCount,
    setLastState,
    setPracticeGroup,
    setPreviousWord,
    setQueue,
    setQueueIndex,
    setSelectedAnswer,
    setShowResult,
    setSpellingFeedbackDismissing,
    setSpellingFeedbackLocked,
    setSpellingFeedbackSnapshot,
    setSpellingInput,
    setSpellingResult,
    setWordStatuses,
    setWrongCount,
    setWrongSelections,
    vocabulary,
  ])
}
