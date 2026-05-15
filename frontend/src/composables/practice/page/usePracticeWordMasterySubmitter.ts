import { useCallback, type MutableRefObject } from 'react'
import { submitWordMasteryAttempt } from '../../../lib/gamePractice'
import { recordEbbinghausPracticeResult } from '../../../lib/ebbinghausReview'
import { buildPracticeResultCommand } from '../../../lib/practiceResult/adapters'
import { applyPracticeResult } from '../../../lib/practiceResult/sink'
import type { PracticeRuntimeId } from '../../../lib/practiceResult/modeContracts'
import type { PracticeMode, SmartDimension, Word } from '../../../features/practice/types'

type MasteryDimension = SmartDimension | 'speaking'
type MasteryResult = 'correct' | 'wrong' | 'skipped'

interface UsePracticeWordMasterySubmitterParams {
  userId: string | number | null
  bookId: string | null
  chapterId: string | null
  currentDay?: number
  currentWord: Word | undefined
  errorMode: boolean
  sessionIdRef: MutableRefObject<number | null>
}

interface SubmitPracticeWordMasteryInput {
  dimension: MasteryDimension
  analyticsMode: PracticeMode
  passed: boolean
  result: MasteryResult
  attemptIndex: number
  recordEbbinghaus?: boolean
}

export function usePracticeWordMasterySubmitter({
  userId,
  bookId,
  chapterId,
  currentDay,
  currentWord,
  errorMode,
  sessionIdRef,
}: UsePracticeWordMasterySubmitterParams) {
  return useCallback((input: SubmitPracticeWordMasteryInput) => {
    if (!currentWord) return
    const resultMode: PracticeRuntimeId = errorMode ? 'errors' : input.analyticsMode
    const command = buildPracticeResultCommand({
      userScope: userId ?? 'anonymous',
      route: '/practice',
      mode: resultMode,
      dimension: input.dimension,
      word: currentWord.word,
      wordPayload: currentWord as unknown as Record<string, unknown>,
      result: input.result,
      session: {
        sessionId: sessionIdRef.current,
        localSessionId: `${userId ?? 'anonymous'}:${resultMode}:${bookId ?? 'all'}:${chapterId ?? currentDay ?? 'all'}`,
      },
      progressScope: { bookId, chapterId, day: currentDay },
      attemptIndex: input.attemptIndex,
    })

    void applyPracticeResult(command, {
      quickMemory: () => {
        if (input.recordEbbinghaus === false) return
        recordEbbinghausPracticeResult({
          word: currentWord,
          passed: input.passed,
          sourceMode: input.analyticsMode,
          bookId,
          chapterId,
          scopeKey: command.scopeKey,
          scopeType: command.scopeType,
          originScope: command.originScope,
          occurredAt: command.occurredAt,
        })
      },
      wordMastery: async () => {
        await submitWordMasteryAttempt({
          bookId,
          chapterId,
          word: currentWord.word,
          dimension: input.dimension,
          passed: input.passed,
          sourceMode: input.analyticsMode,
          entry: errorMode ? 'error-review' : 'practice',
          task: errorMode ? 'error-review' : undefined,
          wordPayload: currentWord,
          traceId: command.traceId,
          idempotencyKey: command.idempotencyKey,
        })
      },
    })
  }, [bookId, chapterId, currentDay, currentWord, errorMode, sessionIdRef, userId])
}
