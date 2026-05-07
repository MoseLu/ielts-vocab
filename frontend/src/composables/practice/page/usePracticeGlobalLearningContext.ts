import { useEffect } from 'react'
import { setGlobalLearningContext } from '../../../contexts/AIChatContext'
import { loadSmartStats } from '../../../lib/smartMode'
import { readWrongWordsFromStorage } from '../../../features/vocabulary/wrongWordsStore'
import { buildLearnerProfile, mergeLearnerProfileWithBackend } from '../../../features/practice/learnerProfile'
import type {
  PracticeMode,
  SmartDimension,
  Word,
} from '../../../features/practice/types'
import type { LearnerProfile as BackendLearnerProfile } from '../../../lib/schemas'

export function usePracticeGlobalLearningContext({
  backendLearnerProfile,
  bookId,
  chapterId,
  correctCount,
  currentChapterTitle,
  currentWord,
  errorMode,
  mode,
  queueIndex,
  queueLength,
  smartDimension,
  userId,
  vocabulary,
  wrongCount,
}: {
  backendLearnerProfile: BackendLearnerProfile | null
  bookId: string | null
  chapterId: string | null
  correctCount: number
  currentChapterTitle: string
  currentWord: Word | undefined
  errorMode: boolean
  mode?: PracticeMode
  queueIndex: number
  queueLength: number
  smartDimension: SmartDimension
  userId: string | number | null
  vocabulary: Word[]
  wrongCount: number
}) {
  useEffect(() => {
    const accuracy = correctCount + wrongCount > 0
      ? Math.round((correctCount / (correctCount + wrongCount)) * 100)
      : undefined
    const wrongWords = readWrongWordsFromStorage(userId)
    const localLearnerProfile = buildLearnerProfile({
      vocabulary,
      currentWord,
      mode,
      smartDimension,
      smartStats: loadSmartStats(),
      wrongWords,
    })
    const learnerProfile = mergeLearnerProfileWithBackend({
      localProfile: localLearnerProfile,
      backendProfile: backendLearnerProfile,
      vocabulary,
      wrongWords,
    })

    if (!currentWord) {
      if (vocabulary.length > 0) {
        setGlobalLearningContext({
          currentWord: undefined,
          sessionCompleted: true,
          sessionProgress: queueLength,
          totalWords: vocabulary.length,
          wordsCompleted: correctCount + wrongCount,
          sessionAccuracy: accuracy,
          practiceMode: mode as string,
          mode: errorMode ? 'review' : 'learning',
          currentBook: bookId ?? undefined,
          currentChapter: chapterId ?? undefined,
          currentChapterTitle: currentChapterTitle || undefined,
          currentFocusDimension: learnerProfile.activeDimension,
          weakestDimension: learnerProfile.weakestDimension,
          weakDimensionOrder: learnerProfile.weakDimensionOrder,
          weakFocusWords: learnerProfile.weakFocusWords,
          recentWrongWords: learnerProfile.recentWrongWords,
          trapStrategy: learnerProfile.trapStrategy,
          priorityDistractorWords: learnerProfile.priorityWords.map(word => word.word),
        })
      }
      return
    }

    setGlobalLearningContext({
      currentWord: currentWord.word,
      currentPhonetic: currentWord.phonetic,
      currentPos: currentWord.pos,
      currentDefinition: currentWord.definition,
      practiceMode: mode as string,
      mode: errorMode ? 'review' : 'learning',
      sessionProgress: queueIndex + 1,
      totalWords: vocabulary.length,
      wordsCompleted: correctCount + wrongCount,
      sessionAccuracy: accuracy,
      sessionCompleted: false,
      currentBook: bookId ?? undefined,
      currentChapter: chapterId ?? undefined,
      currentChapterTitle: currentChapterTitle || undefined,
      currentFocusDimension: learnerProfile.activeDimension,
      weakestDimension: learnerProfile.weakestDimension,
      weakDimensionOrder: learnerProfile.weakDimensionOrder,
      weakFocusWords: learnerProfile.weakFocusWords,
      recentWrongWords: learnerProfile.recentWrongWords,
      trapStrategy: learnerProfile.trapStrategy,
      priorityDistractorWords: learnerProfile.priorityWords.map(word => word.word),
    })
  }, [
    backendLearnerProfile,
    bookId,
    chapterId,
    correctCount,
    currentChapterTitle,
    currentWord,
    errorMode,
    mode,
    queueIndex,
    queueLength,
    smartDimension,
    userId,
    vocabulary,
    wrongCount,
  ])
}
