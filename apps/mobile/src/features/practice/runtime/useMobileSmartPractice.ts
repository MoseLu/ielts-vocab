import { useCallback, useEffect, useState } from 'react'
import {
  recordSmartPracticeResult,
  selectSmartPracticeDimension,
  wordKey,
  type LearningStatsPayload,
  type MobileWord,
  type SmartPracticeContext,
  type SmartPracticeDimension,
  type SmartWordStatsStore,
} from '@ielts-vocab/app-core'
import { loadLearnerProfile, loadLearningStats, loadSmartStats, syncSmartStats } from '../../../api/learnerApi'

export function useMobileSmartPractice() {
  const [smartStats, setSmartStats] = useState<SmartWordStatsStore>({})
  const [smartContext, setSmartContext] = useState<SmartPracticeContext>({})

  const refreshSmartPracticeContext = useCallback(async () => {
    const [statsResult, profileResult, learningStatsResult] = await Promise.allSettled([
      loadSmartStats(),
      loadLearnerProfile(),
      loadLearningStats(),
    ])
    if (statsResult.status === 'fulfilled') setSmartStats(statsResult.value)

    const nextContext: SmartPracticeContext = {}
    if (profileResult.status === 'fulfilled') nextContext.learnerProfile = profileResult.value
    if (learningStatsResult.status === 'fulfilled') nextContext.learningStats = learningStatsResult.value as LearningStatsPayload
    setSmartContext(nextContext)
  }, [])

  useEffect(() => {
    void refreshSmartPracticeContext()
  }, [refreshSmartPracticeContext])

  const chooseSmartDimension = useCallback(
    (word: MobileWord) => selectSmartPracticeDimension({ word, stats: smartStats, context: smartContext }).dimension,
    [smartContext, smartStats],
  )

  const recordSmartAnswer = useCallback(async (params: {
    bookId?: string | null
    chapterId?: string | number | null
    correct: boolean
    dimension: SmartPracticeDimension
    word: MobileWord
  }) => {
    const nextStats = recordSmartPracticeResult(smartStats, params.word, params.dimension, params.correct)
    setSmartStats(nextStats)
    const key = wordKey(params.word)
    const statsForWord = nextStats[key]
    if (!statsForWord) return
    await syncSmartStats({
      bookId: params.bookId,
      chapterId: params.chapterId,
      mode: 'smart',
      stats: [{ word: key, ...statsForWord }],
    }).catch(() => undefined)
  }, [smartStats])

  return {
    chooseSmartDimension,
    recordSmartAnswer,
    refreshSmartPracticeContext,
  }
}
