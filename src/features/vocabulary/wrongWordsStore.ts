import { STORAGE_KEYS } from '../../constants'
import { getStorageItem, setStorageItem } from '../../lib'
import { QUICK_MEMORY_MASTERY_TARGET } from '../../lib/quickMemory'

export interface WrongWordRecord {
  word: string
  phonetic: string
  pos: string
  definition: string
  wrong_count?: number
  review_streak?: number
  first_wrong_at?: string
  updated_at?: string
  listening_correct?: number
  listening_wrong?: number
  meaning_correct?: number
  meaning_wrong?: number
  dictation_correct?: number
  dictation_wrong?: number
  ebbinghaus_streak?: number
  ebbinghaus_target?: number
  ebbinghaus_remaining?: number
  ebbinghaus_completed?: boolean
}

type WrongWordInput = Partial<WrongWordRecord> & {
  wrongCount?: number
  reviewStreak?: number
  firstWrongAt?: string
  updatedAt?: string
  listeningCorrect?: number
  listeningWrong?: number
  meaningCorrect?: number
  meaningWrong?: number
  dictationCorrect?: number
  dictationWrong?: number
  ebbinghausStreak?: number
  ebbinghausTarget?: number
  ebbinghausRemaining?: number
  ebbinghausCompleted?: boolean
}

type WrongWordsResponse = { words?: WrongWordInput[] }

export const WRONG_WORD_ERROR_REVIEW_TARGET = 2
export const WRONG_WORD_MASTERY_TARGET = WRONG_WORD_ERROR_REVIEW_TARGET

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function asIsoDate(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  if (!trimmed) return undefined

  const timestamp = Date.parse(trimmed)
  if (Number.isNaN(timestamp)) return undefined
  return new Date(timestamp).toISOString()
}

function readDateField(word: WrongWordInput & Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = asIsoDate(word[key])
    if (value) return value
  }
  return undefined
}

function pickEarlierDate(...values: Array<string | undefined>): string | undefined {
  let picked: string | undefined

  for (const value of values) {
    const normalized = asIsoDate(value)
    if (!normalized) continue
    if (!picked || normalized < picked) picked = normalized
  }

  return picked
}

function pickLaterDate(...values: Array<string | undefined>): string | undefined {
  let picked: string | undefined

  for (const value of values) {
    const normalized = asIsoDate(value)
    if (!normalized) continue
    if (!picked || normalized > picked) picked = normalized
  }

  return picked
}

function sortWrongWordRecords(words: WrongWordRecord[]): WrongWordRecord[] {
  return [...words].sort((a, b) => {
    const wrongDiff = (b.wrong_count ?? 0) - (a.wrong_count ?? 0)
    if (wrongDiff !== 0) return wrongDiff
    return a.word.localeCompare(b.word)
  })
}

function normalizeWrongWord(word: WrongWordInput): WrongWordRecord | null {
  const normalizedWord = typeof word.word === 'string' ? word.word.trim() : ''
  if (!normalizedWord) return null

  const rawWord = word as WrongWordInput & Record<string, unknown>
  const firstWrongAt = readDateField(rawWord, [
    'first_wrong_at',
    'firstWrongAt',
    'created_at',
    'createdAt',
    'added_at',
    'addedAt',
    'updated_at',
    'updatedAt',
  ])
  const updatedAt = readDateField(rawWord, ['updated_at', 'updatedAt']) ?? firstWrongAt

  return {
    word: normalizedWord,
    phonetic: typeof word.phonetic === 'string' ? word.phonetic : '',
    pos: typeof word.pos === 'string' ? word.pos : '',
    definition: typeof word.definition === 'string' ? word.definition : '',
    wrong_count: asNumber(word.wrong_count ?? word.wrongCount),
    review_streak: asNumber(word.review_streak ?? word.reviewStreak),
    first_wrong_at: firstWrongAt,
    updated_at: updatedAt,
    listening_correct: asNumber(word.listening_correct ?? word.listeningCorrect),
    listening_wrong: asNumber(word.listening_wrong ?? word.listeningWrong),
    meaning_correct: asNumber(word.meaning_correct ?? word.meaningCorrect),
    meaning_wrong: asNumber(word.meaning_wrong ?? word.meaningWrong),
    dictation_correct: asNumber(word.dictation_correct ?? word.dictationCorrect),
    dictation_wrong: asNumber(word.dictation_wrong ?? word.dictationWrong),
    ebbinghaus_streak: asNumber(word.ebbinghaus_streak ?? word.ebbinghausStreak),
    ebbinghaus_target: asNumber(word.ebbinghaus_target ?? word.ebbinghausTarget, QUICK_MEMORY_MASTERY_TARGET),
    ebbinghaus_remaining: asNumber(word.ebbinghaus_remaining ?? word.ebbinghausRemaining, QUICK_MEMORY_MASTERY_TARGET),
    ebbinghaus_completed: Boolean(word.ebbinghaus_completed ?? word.ebbinghausCompleted),
  }
}

function mergeWrongWord(base: WrongWordRecord, incoming: WrongWordRecord): WrongWordRecord {
  return {
    word: base.word || incoming.word,
    phonetic: base.phonetic || incoming.phonetic,
    pos: base.pos || incoming.pos,
    definition: base.definition || incoming.definition,
    wrong_count: Math.max(base.wrong_count ?? 0, incoming.wrong_count ?? 0),
    review_streak: Math.max(base.review_streak ?? 0, incoming.review_streak ?? 0),
    first_wrong_at: pickEarlierDate(base.first_wrong_at, incoming.first_wrong_at),
    updated_at: pickLaterDate(base.updated_at, incoming.updated_at, base.first_wrong_at, incoming.first_wrong_at),
    listening_correct: Math.max(base.listening_correct ?? 0, incoming.listening_correct ?? 0),
    listening_wrong: Math.max(base.listening_wrong ?? 0, incoming.listening_wrong ?? 0),
    meaning_correct: Math.max(base.meaning_correct ?? 0, incoming.meaning_correct ?? 0),
    meaning_wrong: Math.max(base.meaning_wrong ?? 0, incoming.meaning_wrong ?? 0),
    dictation_correct: Math.max(base.dictation_correct ?? 0, incoming.dictation_correct ?? 0),
    dictation_wrong: Math.max(base.dictation_wrong ?? 0, incoming.dictation_wrong ?? 0),
    ebbinghaus_streak: base.ebbinghaus_streak ?? incoming.ebbinghaus_streak,
    ebbinghaus_target: base.ebbinghaus_target ?? incoming.ebbinghaus_target,
    ebbinghaus_remaining: base.ebbinghaus_remaining ?? incoming.ebbinghaus_remaining,
    ebbinghaus_completed: base.ebbinghaus_completed ?? incoming.ebbinghaus_completed,
  }
}

function normalizeWrongWords(words: WrongWordInput[]): WrongWordRecord[] {
  const normalized: WrongWordRecord[] = []
  for (const word of words) {
    const item = normalizeWrongWord(word)
    if (item) normalized.push(item)
  }
  return normalized
}

export function readWrongWordsFromStorage(): WrongWordRecord[] {
  const stored = getStorageItem<WrongWordInput[]>(STORAGE_KEYS.WRONG_WORDS, [])
  return Array.isArray(stored) ? normalizeWrongWords(stored) : []
}

export function writeWrongWordsToStorage(words: WrongWordInput[]): WrongWordRecord[] {
  const normalized = normalizeWrongWords(words)
  setStorageItem(STORAGE_KEYS.WRONG_WORDS, normalized)
  return normalized
}

export function mergeWrongWordLists(...lists: WrongWordInput[][]): WrongWordRecord[] {
  const merged = new Map<string, WrongWordRecord>()

  for (const list of lists) {
    for (const rawWord of list) {
      const word = normalizeWrongWord(rawWord)
      if (!word) continue
      const key = word.word.toLowerCase()
      const existing = merged.get(key)
      merged.set(key, existing ? mergeWrongWord(existing, word) : word)
    }
  }

  return sortWrongWordRecords([...merged.values()])
}

export function addWrongWordToList(
  words: WrongWordInput[],
  word: WrongWordInput,
): WrongWordRecord[] {
  const normalizedIncoming = normalizeWrongWord(word)
  if (!normalizedIncoming) return mergeWrongWordLists(words)

  const nowIso = new Date().toISOString()
  const key = normalizedIncoming.word.toLowerCase()
  const existingWords = mergeWrongWordLists(words)
  let matched = false

  const nextWords = existingWords.map(existingWord => {
    if (existingWord.word.toLowerCase() !== key) return existingWord

    matched = true
    const mergedWord = mergeWrongWord(existingWord, normalizedIncoming)
    return {
      ...mergedWord,
      wrong_count: Math.max((existingWord.wrong_count ?? 0) + 1, normalizedIncoming.wrong_count ?? 0, 1),
      review_streak: 0,
      ebbinghaus_streak: 0,
      ebbinghaus_target: QUICK_MEMORY_MASTERY_TARGET,
      ebbinghaus_remaining: QUICK_MEMORY_MASTERY_TARGET,
      ebbinghaus_completed: false,
      first_wrong_at: mergedWord.first_wrong_at ?? nowIso,
      updated_at: nowIso,
    }
  })

  if (!matched) {
    nextWords.push({
      ...normalizedIncoming,
      wrong_count: Math.max(normalizedIncoming.wrong_count ?? 0, 1),
      review_streak: 0,
      ebbinghaus_streak: 0,
      ebbinghaus_target: QUICK_MEMORY_MASTERY_TARGET,
      ebbinghaus_remaining: QUICK_MEMORY_MASTERY_TARGET,
      ebbinghaus_completed: false,
      first_wrong_at: normalizedIncoming.first_wrong_at ?? nowIso,
      updated_at: nowIso,
    })
  }

  return sortWrongWordRecords(nextWords)
}

export function removeWrongWordFromList(words: WrongWordInput[], wordToRemove: string): WrongWordRecord[] {
  const needle = wordToRemove.trim().toLowerCase()
  return mergeWrongWordLists(words).filter(word => word.word.toLowerCase() !== needle)
}

export function getWrongWordReviewProgress(
  word: WrongWordInput,
  masteryTarget = WRONG_WORD_ERROR_REVIEW_TARGET,
): {
  streak: number
  target: number
  remaining: number
} {
  const streak = Math.min(asNumber(word.review_streak ?? word.reviewStreak), masteryTarget)
  return {
    streak,
    target: masteryTarget,
    remaining: Math.max(0, masteryTarget - streak),
  }
}

export function applyWrongWordReviewResult(
  words: WrongWordInput[],
  reviewedWord: string,
  wasCorrect: boolean,
  masteryTarget = WRONG_WORD_ERROR_REVIEW_TARGET,
): {
  words: WrongWordRecord[]
  removed: WrongWordRecord | null
} {
  const needle = reviewedWord.trim().toLowerCase()
  if (!needle) {
    return {
      words: mergeWrongWordLists(words),
      removed: null,
    }
  }

  const normalizedWords = mergeWrongWordLists(words)
  const nextWords = normalizedWords.flatMap(word => {
    if (word.word.toLowerCase() !== needle) {
      return [word]
    }

    const nextStreak = wasCorrect
      ? Math.min((word.review_streak ?? 0) + 1, masteryTarget)
      : 0
    const updatedWord: WrongWordRecord = {
      ...word,
      review_streak: nextStreak,
    }

    return [updatedWord]
  })

  return {
    words: mergeWrongWordLists(nextWords),
    removed: null,
  }
}

export async function loadWrongWords({
  user,
  fetchRemote,
}: {
  user?: unknown
  fetchRemote?: () => Promise<WrongWordsResponse>
}): Promise<WrongWordRecord[]> {
  const localWords = readWrongWordsFromStorage()

  if (!user || !fetchRemote) {
    return localWords
  }

  try {
    const response = await fetchRemote()
    const remoteWords = Array.isArray(response.words) ? response.words : []
    const merged = mergeWrongWordLists(remoteWords, localWords)
    writeWrongWordsToStorage(merged)
    return merged
  } catch {
    return localWords
  }
}
