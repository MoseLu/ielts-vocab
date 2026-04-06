import type { WrongWordRecord } from '../../features/vocabulary/wrongWordsStore'
import type { LearnerProfile as BackendLearnerProfile } from '../../lib/schemas'
import type { SmartWordStatsStore } from '../../lib/smartMode'
import type { PracticeMode, SmartDimension, Word } from './types'

const DIMENSIONS: SmartDimension[] = ['listening', 'meaning', 'dictation']

export interface LearnerProfile {
  activeDimension: SmartDimension
  weakestDimension: SmartDimension
  weakDimensionOrder: SmartDimension[]
  weakFocusWords: string[]
  recentWrongWords: string[]
  trapStrategy: string
  priorityWords: Word[]
}

function getActiveDimension(
  mode: PracticeMode | undefined,
  smartDimension: SmartDimension,
): SmartDimension {
  if (mode === 'listening') return 'listening'
  if (mode === 'dictation') return 'dictation'
  if (mode === 'smart') return smartDimension
  return 'meaning'
}

function getWordKey(word: string): string {
  return word.trim().toLowerCase()
}

function isSmartDimension(value: string): value is SmartDimension {
  return DIMENSIONS.includes(value as SmartDimension)
}

function uniqueStrings(values: Array<string | null | undefined>): string[] {
  const seen = new Set<string>()
  const result: string[] = []

  for (const value of values) {
    const normalized = (value || '').trim()
    if (!normalized || seen.has(normalized)) continue
    seen.add(normalized)
    result.push(normalized)
  }

  return result
}

function uniqueWords(words: Word[]): Word[] {
  const seen = new Set<string>()
  const result: Word[] = []

  for (const word of words) {
    const key = getWordKey(word.word)
    if (!key || seen.has(key)) continue
    seen.add(key)
    result.push(word)
  }

  return result
}

function getDimensionAttempts(
  stats: SmartWordStatsStore[string] | undefined,
  dimension: SmartDimension,
): { correct: number; wrong: number; total: number } {
  const correct = stats?.[dimension].correct ?? 0
  const wrong = stats?.[dimension].wrong ?? 0
  return {
    correct,
    wrong,
    total: correct + wrong,
  }
}

function getDimensionWeaknessScore(
  words: Word[],
  smartStats: SmartWordStatsStore,
  dimension: SmartDimension,
): number {
  if (!words.length) return 0

  let totalAttempts = 0
  let totalWrong = 0
  let missingWords = 0

  for (const word of words) {
    const attempts = getDimensionAttempts(smartStats[getWordKey(word.word)], dimension)
    totalAttempts += attempts.total
    totalWrong += attempts.wrong
    if (attempts.total === 0) missingWords++
  }

  if (totalAttempts === 0) {
    return missingWords / words.length
  }

  return (totalWrong / totalAttempts) + (missingWords / words.length) * 0.15
}

function buildWordPriorityScore(
  word: Word,
  activeDimension: SmartDimension,
  smartStats: SmartWordStatsStore,
  wrongWordsByKey: Map<string, WrongWordRecord>,
): number {
  const key = getWordKey(word.word)
  const stats = smartStats[key]
  const activeAttempts = getDimensionAttempts(stats, activeDimension)
  const overallWrong = stats
    ? stats.listening.wrong + stats.meaning.wrong + stats.dictation.wrong
    : 0
  const activeAccuracy = activeAttempts.total > 0
    ? activeAttempts.correct / activeAttempts.total
    : 0
  const wrongWord = wrongWordsByKey.get(key)

  let score = 0
  score += Math.min(overallWrong, 6)
  score += activeAttempts.wrong * 2
  score += activeAttempts.total > 0 ? (1 - activeAccuracy) * 3 : 1
  if (wrongWord) score += 6 + Math.min(wrongWord.wrong_count ?? 0, 5)

  return score
}

export function buildLearnerProfile({
  vocabulary,
  currentWord,
  mode,
  smartDimension,
  smartStats,
  wrongWords,
}: {
  vocabulary: Word[]
  currentWord?: Word
  mode?: PracticeMode
  smartDimension: SmartDimension
  smartStats: SmartWordStatsStore
  wrongWords: WrongWordRecord[]
}): LearnerProfile {
  const activeDimension = getActiveDimension(mode, smartDimension)
  const currentKey = currentWord ? getWordKey(currentWord.word) : ''
  const wrongWordsByKey = new Map(
    wrongWords.map(word => [getWordKey(word.word), word] as const),
  )
  const candidatePool = new Map<string, Word>()

  for (const word of vocabulary) {
    candidatePool.set(getWordKey(word.word), word)
  }
  for (const wrongWord of wrongWords) {
    const key = getWordKey(wrongWord.word)
    if (candidatePool.has(key)) continue
    candidatePool.set(key, {
      word: wrongWord.word,
      phonetic: wrongWord.phonetic,
      pos: wrongWord.pos,
      definition: wrongWord.definition,
    })
  }

  const weakDimensionOrder = [...DIMENSIONS].sort((a, b) => (
    getDimensionWeaknessScore(vocabulary, smartStats, b)
    - getDimensionWeaknessScore(vocabulary, smartStats, a)
  ))

  const priorityWords = [...candidatePool.values()]
    .filter(word => getWordKey(word.word) !== currentKey)
    .map(word => ({
      word,
      score: buildWordPriorityScore(word, activeDimension, smartStats, wrongWordsByKey),
    }))
    .filter(item => item.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 4)
    .map(item => item.word)

  const weakFocusWords = priorityWords.slice(0, 3).map(word => word.word)
  const recentWrongWords = [...wrongWords]
    .sort((a, b) => (b.wrong_count ?? 0) - (a.wrong_count ?? 0))
    .slice(0, 5)
    .map(word => word.word)

  const trapParts: string[] = []
  if (recentWrongWords.length > 0) trapParts.push('错词回钩')
  if (weakFocusWords.length > 0) trapParts.push('薄弱词优先')
  if (activeDimension === 'listening') trapParts.push('音近词干扰')
  else if (activeDimension === 'dictation') trapParts.push('形近拼写陷阱')
  else trapParts.push('易混词辨析')

  return {
    activeDimension,
    weakestDimension: weakDimensionOrder[0] ?? activeDimension,
    weakDimensionOrder,
    weakFocusWords,
    recentWrongWords,
    trapStrategy: trapParts.join(' + '),
    priorityWords,
  }
}

export function mergeLearnerProfileWithBackend({
  localProfile,
  backendProfile,
  vocabulary,
  wrongWords,
}: {
  localProfile: LearnerProfile
  backendProfile: BackendLearnerProfile | null
  vocabulary: Word[]
  wrongWords: WrongWordRecord[]
}): LearnerProfile {
  if (!backendProfile) {
    return localProfile
  }

  const wrongWordMap = new Map(
    wrongWords.map(word => [getWordKey(word.word), word] as const),
  )
  const vocabularyMap = new Map(
    vocabulary.map(word => [getWordKey(word.word), word] as const),
  )
  const backendDimensionOrder = backendProfile.dimensions
    .map(item => item.dimension)
    .filter(isSmartDimension)

  const backendFocusWords = uniqueStrings(
    backendProfile.focus_words.map(item => item.word),
  )
  const backendPriorityWords = backendFocusWords
    .map(word => {
      const key = getWordKey(word)
      const vocabWord = vocabularyMap.get(key)
      if (vocabWord) return vocabWord

      const wrongWord = wrongWordMap.get(key)
      if (!wrongWord) return null

      return {
        word: wrongWord.word,
        phonetic: wrongWord.phonetic,
        pos: wrongWord.pos,
        definition: wrongWord.definition,
      }
    })
    .filter((word): word is Word => Boolean(word))

  const repeatedTopicLabel = backendProfile.repeated_topics[0]?.word_context
    || backendProfile.repeated_topics[0]?.title
    || ''

  return {
    ...localProfile,
    weakestDimension: backendDimensionOrder[0] ?? localProfile.weakestDimension,
    weakDimensionOrder: uniqueStrings([
      ...backendDimensionOrder,
      ...localProfile.weakDimensionOrder,
    ]).filter(isSmartDimension),
    weakFocusWords: uniqueStrings([
      ...backendFocusWords,
      ...localProfile.weakFocusWords,
    ]).slice(0, 5),
    recentWrongWords: uniqueStrings([
      ...backendFocusWords,
      ...localProfile.recentWrongWords,
    ]).slice(0, 5),
    trapStrategy: uniqueStrings([
      localProfile.trapStrategy,
      repeatedTopicLabel ? `重复主题:${repeatedTopicLabel}` : '',
      backendProfile.next_actions[0] || '',
    ]).join(' + '),
    priorityWords: uniqueWords([
      ...backendPriorityWords,
      ...localProfile.priorityWords,
    ]).slice(0, 6),
  }
}
