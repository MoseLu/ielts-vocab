import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Dispatch, MutableRefObject, SetStateAction } from 'react'
import type {
  LastState,
  PracticeMode,
  ProgressData,
  Word,
  WordStatuses,
} from '../../../components/practice/types'

function getResumeLabels(mode: PracticeMode) {
  switch (mode) {
    case 'dictation':
      return { context: '听写', action: '继续听写' }
    case 'listening':
      return { context: '听音', action: '继续练习' }
    case 'quickmemory':
      return { context: '快记', action: '继续练习' }
    case 'meaning':
      return { context: '释义', action: '继续练习' }
    case 'radio':
      return { context: '电台', action: '继续学习' }
    default:
      return { context: '练习', action: '继续学习' }
  }
}

function hasResumeSnapshot(snapshot: ProgressData | null): boolean {
  if (!snapshot || snapshot.is_completed) return false
  if ((snapshot.current_index ?? 0) > 0) return true
  return (snapshot.answered_words?.length ?? 0) > 0
}

interface UsePracticeResumePromptParams {
  practiceMode: PracticeMode
  bookId: string | null
  chapterId: string | null
  reviewMode: boolean
  errorMode: boolean
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
  correctCount: number
  wrongCount: number
  saveProgress: (
    correct: number,
    wrong: number,
    options?: { advanceToNext?: boolean },
  ) => void
  resumeProgress: ProgressData | null
  setResumeProgress: Dispatch<SetStateAction<ProgressData | null>>
  resetChapterProgress: () => Promise<void>
  wordsLearnedBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  setFavoriteQueueIndex: Dispatch<SetStateAction<number>>
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

export function usePracticeResumePrompt({
  practiceMode,
  bookId,
  chapterId,
  reviewMode,
  errorMode,
  vocabulary,
  queue,
  queueIndex,
  correctCount,
  wrongCount,
  saveProgress,
  resumeProgress,
  setResumeProgress,
  resetChapterProgress,
  wordsLearnedBaselineRef,
  uniqueAnsweredRef,
  setFavoriteQueueIndex,
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
}: UsePracticeResumePromptParams) {
  const [resumePromptDismissed, setResumePromptDismissed] = useState(false)
  const labels = useMemo(() => getResumeLabels(practiceMode), [practiceMode])

  useEffect(() => {
    setResumePromptDismissed(false)
  }, [bookId, chapterId, errorMode, practiceMode, reviewMode])

  useEffect(() => {
    const nextIndex = queue.length > 0 ? Math.min(queueIndex, queue.length - 1) : 0
    setFavoriteQueueIndex(nextIndex)
  }, [queue.length, queueIndex, setFavoriteQueueIndex])

  useEffect(() => {
    if (practiceMode !== 'radio' || !vocabulary.length) return
    saveProgress(correctCount, wrongCount, { advanceToNext: false })
  }, [correctCount, practiceMode, queueIndex, saveProgress, vocabulary.length, wrongCount])

  const handlePracticeWordIndexChange = useCallback((index: number) => {
    setFavoriteQueueIndex(index)
    if (practiceMode === 'radio') setQueueIndex(index)
  }, [practiceMode, setFavoriteQueueIndex, setQueueIndex])

  const resumePromptOpen = (
    Boolean(bookId)
    && Boolean(chapterId)
    && !reviewMode
    && !errorMode
    && vocabulary.length > 0
    && queueIndex < queue.length
    && !resumePromptDismissed
    && hasResumeSnapshot(resumeProgress)
  )

  const resumeMessage = useMemo(() => {
    return `上次有未完成的${labels.context}练习，要从中断位置继续吗？`
  }, [labels.context])

  const handleResumeContinue = useCallback(() => {
    setResumePromptDismissed(true)
  }, [])

  const handleResumeRestart = useCallback(async () => {
    setResumePromptDismissed(true)
    setResumeProgress(null)
    wordsLearnedBaselineRef.current = 0
    uniqueAnsweredRef.current = new Set()
    setFavoriteQueueIndex(0)
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
    await resetChapterProgress()
  }, [
    resetChapterProgress,
    setCorrectCount,
    setFavoriteQueueIndex,
    setLastState,
    setPreviousWord,
    setQueueIndex,
    setResumeProgress,
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
    uniqueAnsweredRef,
    wordsLearnedBaselineRef,
  ])

  return {
    handlePracticeWordIndexChange,
    handleResumeContinue,
    handleResumeRestart,
    resumeContinueLabel: labels.action,
    resumeMessage,
    resumePromptOpen,
  }
}
