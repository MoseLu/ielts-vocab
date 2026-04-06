import type { OptionItem, Word } from './types'

export interface GenerateOptionsConfig {
  mode?: string
  priorityWords?: Word[]
}

const IPA_VOWELS = 'aeiouəɪʊʌæɒɔɑɛɜɐøœɨɯɵ'
const VALID_ONSET2 = new Set([
  'bl', 'br', 'ch', 'cl', 'cr', 'dr', 'dw', 'fl', 'fr', 'gl', 'gr', 'kl', 'kn',
  'ph', 'pl', 'pr', 'sc', 'sh', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sw', 'th', 'tr', 'tw', 'wh', 'wr',
])
const VALID_ONSET3 = new Set(['str', 'scr', 'spr', 'spl', 'squ', 'thr', 'chr'])
const MEANING_POS_RE = /\b(?:n|v|vi|vt|adj|adv|prep|pron|conj|aux|int|num|art|a)\.\s*/gi
const LISTENING_VARIANT_REPLACEMENTS: Array<[RegExp, string]> = [
  [/metres\b/g, 'meters'],
  [/metre\b/g, 'meter'],
  [/litres\b/g, 'liters'],
  [/litre\b/g, 'liter'],
  [/centres\b/g, 'centers'],
  [/centre\b/g, 'center'],
  [/theatres\b/g, 'theaters'],
  [/theatre\b/g, 'theater'],
]

export function shuffleArray<T>(arr: T[]): T[] {
  const next = [...arr]
  for (let index = next.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    ;[next[index], next[swapIndex]] = [next[swapIndex], next[index]]
  }
  return next
}

export function normalizeWordAnswer(value: string): string {
  return value
    .trim()
    .toLowerCase()
    .replace(/[’‘`]/g, "'")
    .replace(/[‐‑‒–—―]/g, '-')
    .replace(/^[\s"'“”‘’.,!?;:()[\]{}]+/, '')
    .replace(/[\s"'“”‘’.,!?;:()[\]{}]+$/, '')
    .replace(/\s+/g, ' ')
}

export function countPhoneticSyllables(phonetic: string): number {
  const ipa = phonetic.replace(/[/[\]ˈˌ.ː]/g, '')
  let count = 0
  let index = 0
  while (index < ipa.length) {
    if (IPA_VOWELS.includes(ipa[index])) {
      count += 1
      index += 1
      while (index < ipa.length && IPA_VOWELS.includes(ipa[index])) index += 1
    } else {
      index += 1
    }
  }
  return Math.max(1, count)
}

export function syllabifyWord(word: string, phonetic: string): string[] {
  if (word.trim().includes(' ')) return [word.trim()]

  const syllableCount = countPhoneticSyllables(phonetic)
  if (syllableCount <= 1 || word.length <= 2) return [word]

  const lower = word.toLowerCase()
  const isVowel = (char: string, index: number): boolean => {
    if ('aeiou'.includes(char)) return true
    return char === 'y' && index > 0 && !'aeiou'.includes(lower[index - 1])
  }

  const vowelGroups: Array<{ start: number; end: number }> = []
  for (let index = 0; index < lower.length;) {
    if (isVowel(lower[index], index)) {
      let end = index
      while (end < lower.length && isVowel(lower[end], end)) end += 1
      vowelGroups.push({ start: index, end })
      index = end
    } else {
      index += 1
    }
  }

  if (vowelGroups.length <= 1) return [word]

  const splitPoints = vowelGroups.slice(0, -1).map((group, groupIndex) => {
    const nextStart = vowelGroups[groupIndex + 1].start
    const gap = nextStart - group.end
    const consonants = lower.slice(group.end, nextStart)

    if (gap <= 1) return group.end
    if (gap === 2) return VALID_ONSET2.has(consonants) ? group.end : group.end + 1
    return VALID_ONSET3.has(consonants) || VALID_ONSET2.has(consonants.slice(1))
      ? group.end + 1
      : group.end + 1
  }).slice(0, syllableCount - 1)

  const parts: string[] = []
  let previous = 0
  for (const split of splitPoints) {
    if (split > previous) parts.push(word.slice(previous, split))
    previous = split
  }
  if (previous < word.length) parts.push(word.slice(previous))
  return parts.filter(Boolean)
}

function levenshtein(left: string, right: string): number {
  const buffer: number[] = Array.from({ length: right.length + 1 }, (_value, index) => index)
  for (let row = 1; row <= left.length; row += 1) {
    let previousDiagonal = buffer[0]
    buffer[0] = row
    for (let column = 1; column <= right.length; column += 1) {
      const previousValue = buffer[column]
      buffer[column] = left[row - 1] === right[column - 1]
        ? previousDiagonal
        : 1 + Math.min(previousDiagonal, buffer[column], buffer[column - 1])
      previousDiagonal = previousValue
    }
  }
  return buffer[right.length]
}

function confusabilityScore(target: Word, candidate: Word): number {
  const targetWord = target.word.toLowerCase()
  const candidateWord = candidate.word.toLowerCase()
  let score = 0

  if (target.pos === candidate.pos) score += 2
  score += (1 - levenshtein(targetWord, candidateWord) / Math.max(targetWord.length, candidateWord.length)) * 5

  let prefix = 0
  while (prefix < targetWord.length && prefix < candidateWord.length && targetWord[prefix] === candidateWord[prefix]) {
    prefix += 1
  }
  score += Math.min(prefix * 0.8, 3)

  let suffix = 0
  while (
    suffix < targetWord.length
    && suffix < candidateWord.length
    && targetWord[targetWord.length - 1 - suffix] === candidateWord[candidateWord.length - 1 - suffix]
  ) {
    suffix += 1
  }
  score += Math.min(suffix * 0.5, 1.5)

  if (Math.abs(targetWord.length - candidateWord.length) <= 2) score += 0.5

  if (target.phonetic && candidate.phonetic) {
    const stripPhonetic = (value: string) => value.replace(/[/[\]ˈˌ.: ]/g, '').toLowerCase()
    const targetPhonetic = stripPhonetic(target.phonetic)
    const candidatePhonetic = stripPhonetic(candidate.phonetic)
    if (targetPhonetic && candidatePhonetic) {
      score += (
        1 - levenshtein(targetPhonetic, candidatePhonetic) / Math.max(targetPhonetic.length, candidatePhonetic.length)
      ) * 4
    }
  }

  return score
}

function cleanMeaningFragment(value: string): string {
  return value
    .replace(MEANING_POS_RE, ' ')
    .replace(/[()（）[\]【】]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function normalizeMeaningText(value: string): string {
  return cleanMeaningFragment(value)
    .toLowerCase()
    .replace(/[;；，,、/]/g, ' ')
    .replace(/[。！？]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

function singularizeListeningToken(token: string): string {
  if (token.endsWith('ies') && token.length > 4) return `${token.slice(0, -3)}y`
  if (/(?:ches|shes|xes|zes|ses|oes)$/.test(token) && token.length > 4) return token.slice(0, -2)
  if (token.endsWith('s') && token.length > 3 && !/(?:ss|us|is)$/.test(token)) return token.slice(0, -1)
  return token
}

function normalizeListeningFamilyKey(word: Pick<Word, 'word' | 'group_key'>): string {
  const explicitGroupKey = normalizeWordAnswer(word.group_key ?? '')
  const normalizedWord = explicitGroupKey || normalizeWordAnswer(word.word)
  if (!normalizedWord) return ''

  const normalizedVariant = LISTENING_VARIANT_REPLACEMENTS.reduce(
    (value, [pattern, replacement]) => value.replace(pattern, replacement),
    normalizedWord,
  )

  return normalizedVariant
    .split(' ')
    .map(token => token.split('-').map(singularizeListeningToken).join('-'))
    .join(' ')
}

function listeningDistractorScore(currentWord: Word, candidate: Word, priorityIndex?: number): number {
  const priorityBonus = priorityIndex == null ? 0 : 6 - Math.min(priorityIndex, 5)
  return confusabilityScore(currentWord, candidate) + priorityBonus
}

export function generateOptions(
  currentWord: Word,
  allWords: Word[],
  modeOrConfig?: string | GenerateOptionsConfig,
): { options: OptionItem[]; correctIndex: number } {
  const config = typeof modeOrConfig === 'string' ? { mode: modeOrConfig } : (modeOrConfig ?? {})
  const isMeaningMode = config.mode === 'meaning'
  const isListeningMode = config.mode === 'listening'
  const currentWordKey = currentWord.word.trim().toLowerCase()
  const currentDefinitionKey = normalizeMeaningText(currentWord.definition)
  const currentListeningFamilyKey = isListeningMode ? normalizeListeningFamilyKey(currentWord) : ''
  const getCandidateKey = (word: Word): string => (
    isMeaningMode
      ? word.word.trim().toLowerCase()
      : isListeningMode
        ? normalizeListeningFamilyKey(word)
        : normalizeMeaningText(word.definition)
  )

  const seenWords = new Set<string>()
  const seenDefinitions = new Set<string>()
  const seenListeningFamilies = new Set<string>()
  const candidates = allWords.filter(word => {
    const wordKey = word.word.trim().toLowerCase()
    const definitionKey = normalizeMeaningText(word.definition)
    const listeningFamilyKey = isListeningMode ? normalizeListeningFamilyKey(word) : ''

    if (!wordKey || !definitionKey || (isListeningMode && !listeningFamilyKey)) return false
    if (wordKey === currentWordKey) return false
    if (isListeningMode && listeningFamilyKey === currentListeningFamilyKey) return false

    if (isMeaningMode) {
      if (seenWords.has(wordKey)) return false
    } else {
      if (definitionKey === currentDefinitionKey) return false
      if (seenWords.has(wordKey) || seenDefinitions.has(definitionKey)) return false
      if (isListeningMode && seenListeningFamilies.has(listeningFamilyKey)) return false
    }

    seenWords.add(wordKey)
    seenDefinitions.add(definitionKey)
    if (isListeningMode) seenListeningFamilies.add(listeningFamilyKey)
    return true
  })

  const priorityWordMap = new Map(
    (config.priorityWords ?? []).map((word, index) => [word.word.trim().toLowerCase(), index] as const),
  )

  let distractorWords: Word[] = []
  if (isListeningMode && candidates.length >= 3) {
    distractorWords = candidates
      .map(word => ({
        word,
        score: listeningDistractorScore(currentWord, word, priorityWordMap.get(word.word.trim().toLowerCase())),
      }))
      .sort((left, right) => right.score - left.score)
      .slice(0, 3)
      .map(item => item.word)
  } else if (priorityWordMap.size > 0 && candidates.length >= 3) {
    distractorWords = candidates
      .map(word => {
        const priorityIndex = priorityWordMap.get(word.word.trim().toLowerCase())
        return {
          word,
          priorityIndex: priorityIndex ?? Number.POSITIVE_INFINITY,
          score: confusabilityScore(currentWord, word) + (priorityIndex == null ? 0 : 12 - Math.min(priorityIndex, 10)),
        }
      })
      .sort((left, right) => {
        if (left.priorityIndex !== right.priorityIndex) return left.priorityIndex - right.priorityIndex
        return right.score - left.score
      })
      .slice(0, 3)
      .map(item => item.word)
  } else {
    distractorWords = shuffleArray(candidates).slice(0, 3)
  }

  if (distractorWords.length < 3) {
    const used = new Set(distractorWords.map(getCandidateKey))
    distractorWords.push(...candidates.filter(word => !used.has(getCandidateKey(word))).slice(0, 3 - distractorWords.length))
  }

  const toOption = (word: Word): OptionItem => (
    isMeaningMode
      ? {
          word: word.word,
          phonetic: word.phonetic,
          definition: word.definition,
          pos: word.pos,
          display_mode: 'word',
        }
      : {
          word: word.word,
          phonetic: word.phonetic,
          definition: cleanMeaningFragment(word.definition) || word.definition,
          pos: word.pos,
          display_mode: 'definition',
        }
  )

  const options = shuffleArray([toOption(currentWord), ...distractorWords.map(toOption)])
  const correctIndex = options.findIndex(option => (
    isMeaningMode
      ? option.word?.trim().toLowerCase() === currentWordKey
      : normalizeMeaningText(option.definition) === currentDefinitionKey
  ))

  return { options, correctIndex }
}
