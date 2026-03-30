import { STORAGE_KEYS } from '../../constants'
import { getStorageItem, setStorageItem } from '../../lib'

export interface WrongWordRecord {
  word: string
  phonetic: string
  pos: string
  definition: string
  wrong_count?: number
  listening_correct?: number
  listening_wrong?: number
  meaning_correct?: number
  meaning_wrong?: number
  dictation_correct?: number
  dictation_wrong?: number
}

type WrongWordInput = Partial<WrongWordRecord> & {
  wrongCount?: number
  listeningCorrect?: number
  listeningWrong?: number
  meaningCorrect?: number
  meaningWrong?: number
  dictationCorrect?: number
  dictationWrong?: number
}

type WrongWordsResponse = { words?: WrongWordInput[] }

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback
}

function normalizeWrongWord(word: WrongWordInput): WrongWordRecord | null {
  const normalizedWord = typeof word.word === 'string' ? word.word.trim() : ''
  if (!normalizedWord) return null

  return {
    word: normalizedWord,
    phonetic: typeof word.phonetic === 'string' ? word.phonetic : '',
    pos: typeof word.pos === 'string' ? word.pos : '',
    definition: typeof word.definition === 'string' ? word.definition : '',
    wrong_count: asNumber(word.wrong_count ?? word.wrongCount),
    listening_correct: asNumber(word.listening_correct ?? word.listeningCorrect),
    listening_wrong: asNumber(word.listening_wrong ?? word.listeningWrong),
    meaning_correct: asNumber(word.meaning_correct ?? word.meaningCorrect),
    meaning_wrong: asNumber(word.meaning_wrong ?? word.meaningWrong),
    dictation_correct: asNumber(word.dictation_correct ?? word.dictationCorrect),
    dictation_wrong: asNumber(word.dictation_wrong ?? word.dictationWrong),
  }
}

function mergeWrongWord(base: WrongWordRecord, incoming: WrongWordRecord): WrongWordRecord {
  return {
    word: base.word || incoming.word,
    phonetic: base.phonetic || incoming.phonetic,
    pos: base.pos || incoming.pos,
    definition: base.definition || incoming.definition,
    wrong_count: Math.max(base.wrong_count ?? 0, incoming.wrong_count ?? 0),
    listening_correct: Math.max(base.listening_correct ?? 0, incoming.listening_correct ?? 0),
    listening_wrong: Math.max(base.listening_wrong ?? 0, incoming.listening_wrong ?? 0),
    meaning_correct: Math.max(base.meaning_correct ?? 0, incoming.meaning_correct ?? 0),
    meaning_wrong: Math.max(base.meaning_wrong ?? 0, incoming.meaning_wrong ?? 0),
    dictation_correct: Math.max(base.dictation_correct ?? 0, incoming.dictation_correct ?? 0),
    dictation_wrong: Math.max(base.dictation_wrong ?? 0, incoming.dictation_wrong ?? 0),
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

  return [...merged.values()].sort((a, b) => {
    const wrongDiff = (b.wrong_count ?? 0) - (a.wrong_count ?? 0)
    if (wrongDiff !== 0) return wrongDiff
    return a.word.localeCompare(b.word)
  })
}

export function addWrongWordToList(
  words: WrongWordInput[],
  word: WrongWordInput,
): WrongWordRecord[] {
  return mergeWrongWordLists([word], words)
}

export function removeWrongWordFromList(words: WrongWordInput[], wordToRemove: string): WrongWordRecord[] {
  const needle = wordToRemove.trim().toLowerCase()
  return mergeWrongWordLists(words).filter(word => word.word.toLowerCase() !== needle)
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
