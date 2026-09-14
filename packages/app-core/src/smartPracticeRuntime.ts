import {
  evaluatePracticeAnswer,
  type PracticeResult,
} from './practiceEngine'
import {
  chooseSmartPracticeDimension,
  resolveSmartPracticeMode,
  type SmartPracticeContext,
  type SmartPracticeDimension,
  type SmartWordStatsStore,
} from './smartPractice'
import type { MobileWord, PracticeMode } from './mobileSchemas'

export type SmartPracticeSelection = {
  dimension: SmartPracticeDimension
  mode: Extract<PracticeMode, 'listening' | 'meaning' | 'dictation'>
}

export type SmartPracticeAttempt = SmartPracticeSelection & {
  result: PracticeResult
}

export function selectSmartPracticeDimension(params: {
  context?: SmartPracticeContext
  random?: () => number
  stats: SmartWordStatsStore
  word: Pick<MobileWord, 'word'> | string
}): SmartPracticeSelection {
  const dimension = chooseSmartPracticeDimension(params.word, params.stats, params.context, params.random)
  return {
    dimension,
    mode: resolveSmartPracticeMode(dimension),
  }
}

export function evaluateSmartPracticeAttempt(params: {
  answer: string
  context?: SmartPracticeContext
  random?: () => number
  stats: SmartWordStatsStore
  word: MobileWord
}): SmartPracticeAttempt {
  const selection = selectSmartPracticeDimension(params)
  return {
    ...selection,
    result: evaluatePracticeAnswer(params.word, 'smart', params.answer, {
      smartDimension: selection.dimension,
    }),
  }
}
