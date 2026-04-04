import { STORAGE_KEYS } from '../../constants'
import { getStorageItem, setStorageItem } from '../../lib'

export type WrongWordDimension = 'recognition' | 'meaning' | 'listening' | 'dictation'
export type WrongWordCollectionScope = 'history' | 'pending'

export interface WrongWordDimensionState {
  history_wrong: number
  pass_streak: number
  last_wrong_at?: string
  last_pass_at?: string
}

export type WrongWordDimensionStateMap = Record<WrongWordDimension, WrongWordDimensionState>

export interface WrongWordRecord {
  word: string
  phonetic: string
  pos: string
  definition: string
  wrong_count?: number
  pending_wrong_count?: number
  history_dimension_count?: number
  pending_dimension_count?: number
  review_pass_target?: number
  first_wrong_at?: string
  updated_at?: string
  listening_correct?: number
  listening_wrong?: number
  meaning_correct?: number
  meaning_wrong?: number
  dictation_correct?: number
  dictation_wrong?: number
  recognition_wrong?: number
  recognition_pending?: boolean
  recognition_pass_streak?: number
  meaning_pending?: boolean
  meaning_pass_streak?: number
  listening_pending?: boolean
  listening_pass_streak?: number
  dictation_pending?: boolean
  dictation_pass_streak?: number
  ebbinghaus_streak?: number
  ebbinghaus_target?: number
  ebbinghaus_remaining?: number
  ebbinghaus_completed?: boolean
  dimension_states?: WrongWordDimensionStateMap
}

type WrongWordInput = Partial<WrongWordRecord> & {
  wrongCount?: number
  pendingWrongCount?: number
  historyDimensionCount?: number
  pendingDimensionCount?: number
  reviewPassTarget?: number
  firstWrongAt?: string
  updatedAt?: string
  listeningCorrect?: number
  listeningWrong?: number
  meaningCorrect?: number
  meaningWrong?: number
  dictationCorrect?: number
  dictationWrong?: number
  recognitionWrong?: number
  recognitionPending?: boolean
  recognitionPassStreak?: number
  meaningPending?: boolean
  meaningPassStreak?: number
  listeningPending?: boolean
  listeningPassStreak?: number
  dictationPending?: boolean
  dictationPassStreak?: number
  dimensionStates?: Partial<Record<WrongWordDimension, Partial<WrongWordDimensionState>>>
  ebbinghausStreak?: number
  ebbinghausTarget?: number
  ebbinghausRemaining?: number
  ebbinghausCompleted?: boolean
}

type WrongWordsResponse = { words?: WrongWordInput[] }

export const WRONG_WORD_DIMENSIONS: WrongWordDimension[] = [
  'recognition',
  'meaning',
  'listening',
  'dictation',
]

export const WRONG_WORD_DIMENSION_LABELS: Record<WrongWordDimension, string> = {
  recognition: '英译汉（认识）',
  meaning: '汉译英（会想）',
  listening: '听音选义（听得到）',
  dictation: '拼写测试（会拼写）',
}

export const WRONG_WORD_PENDING_REVIEW_TARGET = 4
export const WRONG_WORD_ERROR_REVIEW_TARGET = WRONG_WORD_PENDING_REVIEW_TARGET

type ScopedUserId = string | number | null | undefined

const LEGACY_DIMENSION_KEY_MAP: Record<Exclude<WrongWordDimension, 'recognition'>, string> = {
  meaning: 'meaning',
  listening: 'listening',
  dictation: 'dictation',
}

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

function emptyDimensionState(): WrongWordDimensionState {
  return {
    history_wrong: 0,
    pass_streak: 0,
  }
}

function clampPassStreak(value: unknown, target = WRONG_WORD_PENDING_REVIEW_TARGET): number {
  return Math.min(asNumber(value), target)
}

function normalizeDimensionState(value: unknown): WrongWordDimensionState | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null

  const raw = value as Record<string, unknown>
  return {
    history_wrong: asNumber(raw.history_wrong ?? raw.historyWrong),
    pass_streak: clampPassStreak(raw.pass_streak ?? raw.passStreak),
    last_wrong_at: asIsoDate(raw.last_wrong_at ?? raw.lastWrongAt),
    last_pass_at: asIsoDate(raw.last_pass_at ?? raw.lastPassAt),
  }
}

function normalizeScopedUserId(value: unknown): string | number | null {
  return typeof value === 'string' || typeof value === 'number'
    ? value
    : null
}

function readAuthUserIdFromStorage(): string | number | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEYS.AUTH_USER)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { id?: unknown }
    return normalizeScopedUserId(parsed.id)
  } catch {
    return null
  }
}

function resolveScopedUserId(userId?: ScopedUserId): string | number | null {
  return normalizeScopedUserId(userId) ?? readAuthUserIdFromStorage()
}

function buildUserScopedStorageKey(baseKey: string, userId?: ScopedUserId): string {
  const resolvedUserId = resolveScopedUserId(userId)
  return resolvedUserId == null ? baseKey : `${baseKey}:user:${String(resolvedUserId)}`
}

function readUserId(user: unknown): string | number | null {
  if (!user || typeof user !== 'object' || !('id' in user)) {
    return null
  }

  return normalizeScopedUserId((user as { id?: unknown }).id)
}

function normalizeDimensionStates(rawWord: WrongWordInput & Record<string, unknown>): WrongWordDimensionStateMap {
  const rawDimensionStates = rawWord.dimension_states ?? rawWord.dimensionStates
  const parsedDimensionStates =
    typeof rawDimensionStates === 'string'
      ? (() => {
          try {
            return JSON.parse(rawDimensionStates) as Record<string, unknown>
          } catch {
            return {}
          }
        })()
      : (rawDimensionStates as Record<string, unknown> | undefined) ?? {}

  const states = WRONG_WORD_DIMENSIONS.reduce((result, dimension) => {
    const normalized = normalizeDimensionState(parsedDimensionStates[dimension])
    result[dimension] = normalized ?? emptyDimensionState()
    return result
  }, {} as WrongWordDimensionStateMap)

  for (const dimension of WRONG_WORD_DIMENSIONS) {
    if (dimension === 'recognition') {
      const recognitionWrong = asNumber(rawWord.recognition_wrong ?? rawWord.recognitionWrong)
      if (recognitionWrong > states.recognition.history_wrong) {
        states.recognition.history_wrong = recognitionWrong
      }
      const recognitionPass = clampPassStreak(
        rawWord.recognition_pass_streak
          ?? rawWord.recognitionPassStreak
          ?? rawWord.ebbinghaus_streak
          ?? rawWord.ebbinghausStreak,
      )
      states.recognition.pass_streak = Math.max(states.recognition.pass_streak, recognitionPass)
      continue
    }

    const legacyKey = LEGACY_DIMENSION_KEY_MAP[dimension]
    const historyWrong = asNumber(rawWord[`${legacyKey}_wrong`] ?? rawWord[`${legacyKey}Wrong`])
    const passStreak = clampPassStreak(
      rawWord[`${legacyKey}_pass_streak`]
        ?? rawWord[`${legacyKey}PassStreak`]
        ?? rawWord[`${legacyKey}_review_streak`]
        ?? rawWord[`${legacyKey}ReviewStreak`],
    )
    if (historyWrong > states[dimension].history_wrong) {
      states[dimension].history_wrong = historyWrong
    }
    states[dimension].pass_streak = Math.max(states[dimension].pass_streak, passStreak)
  }

  const fallbackWrongCount = asNumber(rawWord.wrong_count ?? rawWord.wrongCount)
  const totalHistoryWrong = WRONG_WORD_DIMENSIONS.reduce(
    (sum, dimension) => sum + states[dimension].history_wrong,
    0,
  )
  if (fallbackWrongCount > 0 && totalHistoryWrong === 0) {
    states.recognition.history_wrong = fallbackWrongCount
  } else if (fallbackWrongCount > totalHistoryWrong) {
    states.recognition.history_wrong += fallbackWrongCount - totalHistoryWrong
  }

  return states
}

function getDimensionEventAt(state: WrongWordDimensionState): string | undefined {
  return pickLaterDate(state.last_wrong_at, state.last_pass_at)
}

function mergeDimensionStates(
  base: WrongWordDimensionStateMap,
  incoming: WrongWordDimensionStateMap,
): WrongWordDimensionStateMap {
  const merged = {} as WrongWordDimensionStateMap

  for (const dimension of WRONG_WORD_DIMENSIONS) {
    const baseState = base[dimension] ?? emptyDimensionState()
    const incomingState = incoming[dimension] ?? emptyDimensionState()
    const latestWrongAt = pickLaterDate(baseState.last_wrong_at, incomingState.last_wrong_at)
    const latestPassAt = pickLaterDate(baseState.last_pass_at, incomingState.last_pass_at)
    const latestEventAt = pickLaterDate(latestWrongAt, latestPassAt)

    let nextPassStreak = 0
    if (latestEventAt && latestPassAt && latestPassAt >= latestEventAt) {
      const passSource = latestPassAt === incomingState.last_pass_at ? incomingState : baseState
      nextPassStreak = clampPassStreak(passSource.pass_streak)
    } else if (latestPassAt && !latestWrongAt) {
      const passSource = latestPassAt === incomingState.last_pass_at ? incomingState : baseState
      nextPassStreak = clampPassStreak(passSource.pass_streak)
    }

    merged[dimension] = {
      history_wrong: Math.max(baseState.history_wrong, incomingState.history_wrong),
      pass_streak: nextPassStreak,
      last_wrong_at: latestWrongAt,
      last_pass_at: latestPassAt,
    }
  }

  return merged
}

function isDimensionPendingState(state: WrongWordDimensionState): boolean {
  return (state.history_wrong ?? 0) > 0 && (state.pass_streak ?? 0) < WRONG_WORD_PENDING_REVIEW_TARGET
}

function summarizeDimensionStates(states: WrongWordDimensionStateMap) {
  const historyWrongCount = WRONG_WORD_DIMENSIONS.reduce(
    (sum, dimension) => sum + (states[dimension]?.history_wrong ?? 0),
    0,
  )
  const pendingWrongCount = WRONG_WORD_DIMENSIONS.reduce((sum, dimension) => {
    const state = states[dimension]
    if (!state || !isDimensionPendingState(state)) return sum
    return sum + (state.history_wrong ?? 0)
  }, 0)
  const historyDimensionCount = WRONG_WORD_DIMENSIONS.filter(
    dimension => (states[dimension]?.history_wrong ?? 0) > 0,
  ).length
  const pendingDimensionCount = WRONG_WORD_DIMENSIONS.filter(
    dimension => isDimensionPendingState(states[dimension]),
  ).length

  return {
    historyWrongCount,
    pendingWrongCount,
    historyDimensionCount,
    pendingDimensionCount,
  }
}

function mergeEbbinghausRemaining(
  baseValue: number | undefined,
  incomingValue: number | undefined,
): number {
  const candidates = [baseValue, incomingValue].filter(
    (value): value is number => typeof value === 'number' && Number.isFinite(value),
  )

  if (candidates.length === 0) return 0
  return Math.min(...candidates)
}

function applyDimensionStateReviewResult(
  state: WrongWordDimensionState,
  wasCorrect: boolean,
  nowIso: string,
): WrongWordDimensionState {
  if (wasCorrect) {
    return {
      ...state,
      pass_streak: Math.min((state.pass_streak ?? 0) + 1, WRONG_WORD_PENDING_REVIEW_TARGET),
      last_pass_at: nowIso,
    }
  }

  return {
    ...state,
    pass_streak: 0,
    last_wrong_at: nowIso,
  }
}

function applyDimensionStateFailure(
  state: WrongWordDimensionState,
  nowIso: string,
): WrongWordDimensionState {
  return {
    ...state,
    history_wrong: (state.history_wrong ?? 0) + 1,
    pass_streak: 0,
    last_wrong_at: nowIso,
  }
}

function applyDimensionStateClear(
  state: WrongWordDimensionState,
  nowIso: string,
): WrongWordDimensionState {
  if ((state.history_wrong ?? 0) <= 0) return state

  return {
    ...state,
    pass_streak: WRONG_WORD_PENDING_REVIEW_TARGET,
    last_pass_at: nowIso,
  }
}

function withDerivedFields(base: Omit<WrongWordRecord, 'wrong_count' | 'pending_wrong_count' | 'history_dimension_count' | 'pending_dimension_count' | 'review_pass_target' | 'recognition_wrong' | 'recognition_pending' | 'recognition_pass_streak' | 'meaning_pending' | 'meaning_pass_streak' | 'listening_pending' | 'listening_pass_streak' | 'dictation_pending' | 'dictation_pass_streak' | 'dimension_states'> & {
  dimension_states: WrongWordDimensionStateMap
}): WrongWordRecord {
  const summary = summarizeDimensionStates(base.dimension_states)

  return {
    ...base,
    wrong_count: summary.historyWrongCount,
    pending_wrong_count: summary.pendingWrongCount,
    history_dimension_count: summary.historyDimensionCount,
    pending_dimension_count: summary.pendingDimensionCount,
    review_pass_target: WRONG_WORD_PENDING_REVIEW_TARGET,
    recognition_wrong: base.dimension_states.recognition.history_wrong,
    recognition_pending: isDimensionPendingState(base.dimension_states.recognition),
    recognition_pass_streak: base.dimension_states.recognition.pass_streak,
    meaning_wrong: Math.max(base.meaning_wrong ?? 0, base.dimension_states.meaning.history_wrong),
    meaning_pending: isDimensionPendingState(base.dimension_states.meaning),
    meaning_pass_streak: base.dimension_states.meaning.pass_streak,
    listening_wrong: Math.max(base.listening_wrong ?? 0, base.dimension_states.listening.history_wrong),
    listening_pending: isDimensionPendingState(base.dimension_states.listening),
    listening_pass_streak: base.dimension_states.listening.pass_streak,
    dictation_wrong: Math.max(base.dictation_wrong ?? 0, base.dimension_states.dictation.history_wrong),
    dictation_pending: isDimensionPendingState(base.dimension_states.dictation),
    dictation_pass_streak: base.dimension_states.dictation.pass_streak,
    dimension_states: base.dimension_states,
  }
}

function sortWrongWordRecords(words: WrongWordRecord[]): WrongWordRecord[] {
  return [...words].sort((a, b) => {
    const pendingDiff = (b.pending_wrong_count ?? 0) - (a.pending_wrong_count ?? 0)
    if (pendingDiff !== 0) return pendingDiff

    const historyDiff = (b.wrong_count ?? 0) - (a.wrong_count ?? 0)
    if (historyDiff !== 0) return historyDiff

    return a.word.localeCompare(b.word)
  })
}

function normalizeWrongWord(word: WrongWordInput): WrongWordRecord | null {
  const normalizedWord = typeof word.word === 'string' ? word.word.trim() : ''
  if (!normalizedWord) return null

  const rawWord = word as WrongWordInput & Record<string, unknown>
  const normalizedStates = normalizeDimensionStates(rawWord)
  const firstWrongAt = pickEarlierDate(
    readDateField(rawWord, [
      'first_wrong_at',
      'firstWrongAt',
      'created_at',
      'createdAt',
      'added_at',
      'addedAt',
      'updated_at',
      'updatedAt',
    ]),
    ...WRONG_WORD_DIMENSIONS.map(dimension => normalizedStates[dimension].last_wrong_at),
  )
  const updatedAt = pickLaterDate(
    readDateField(rawWord, ['updated_at', 'updatedAt']),
    ...WRONG_WORD_DIMENSIONS.flatMap(dimension => [
      normalizedStates[dimension].last_wrong_at,
      normalizedStates[dimension].last_pass_at,
    ]),
    firstWrongAt,
  )

  return withDerivedFields({
    word: normalizedWord,
    phonetic: typeof word.phonetic === 'string' ? word.phonetic : '',
    pos: typeof word.pos === 'string' ? word.pos : '',
    definition: typeof word.definition === 'string' ? word.definition : '',
    first_wrong_at: firstWrongAt,
    updated_at: updatedAt,
    listening_correct: asNumber(word.listening_correct ?? word.listeningCorrect),
    listening_wrong: asNumber(word.listening_wrong ?? word.listeningWrong),
    meaning_correct: asNumber(word.meaning_correct ?? word.meaningCorrect),
    meaning_wrong: asNumber(word.meaning_wrong ?? word.meaningWrong),
    dictation_correct: asNumber(word.dictation_correct ?? word.dictationCorrect),
    dictation_wrong: asNumber(word.dictation_wrong ?? word.dictationWrong),
    ebbinghaus_streak: asNumber(word.ebbinghaus_streak ?? word.ebbinghausStreak),
    ebbinghaus_target: asNumber(word.ebbinghaus_target ?? word.ebbinghausTarget),
    ebbinghaus_remaining: asNumber(word.ebbinghaus_remaining ?? word.ebbinghausRemaining),
    ebbinghaus_completed: Boolean(word.ebbinghaus_completed ?? word.ebbinghausCompleted),
    dimension_states: normalizedStates,
  })
}

function mergeWrongWord(base: WrongWordRecord, incoming: WrongWordRecord): WrongWordRecord {
  const mergedStates = mergeDimensionStates(
    base.dimension_states ?? normalizeDimensionStates(base as WrongWordInput & Record<string, unknown>),
    incoming.dimension_states ?? normalizeDimensionStates(incoming as WrongWordInput & Record<string, unknown>),
  )

  return withDerivedFields({
    word: base.word || incoming.word,
    phonetic: base.phonetic || incoming.phonetic,
    pos: base.pos || incoming.pos,
    definition: base.definition || incoming.definition,
    first_wrong_at: pickEarlierDate(base.first_wrong_at, incoming.first_wrong_at),
    updated_at: pickLaterDate(
      base.updated_at,
      incoming.updated_at,
      ...WRONG_WORD_DIMENSIONS.map(dimension => getDimensionEventAt(mergedStates[dimension])),
    ),
    listening_correct: Math.max(base.listening_correct ?? 0, incoming.listening_correct ?? 0),
    listening_wrong: Math.max(base.listening_wrong ?? 0, incoming.listening_wrong ?? 0),
    meaning_correct: Math.max(base.meaning_correct ?? 0, incoming.meaning_correct ?? 0),
    meaning_wrong: Math.max(base.meaning_wrong ?? 0, incoming.meaning_wrong ?? 0),
    dictation_correct: Math.max(base.dictation_correct ?? 0, incoming.dictation_correct ?? 0),
    dictation_wrong: Math.max(base.dictation_wrong ?? 0, incoming.dictation_wrong ?? 0),
    ebbinghaus_streak: Math.max(base.ebbinghaus_streak ?? 0, incoming.ebbinghaus_streak ?? 0),
    ebbinghaus_target: Math.max(base.ebbinghaus_target ?? 0, incoming.ebbinghaus_target ?? 0),
    ebbinghaus_remaining: mergeEbbinghausRemaining(base.ebbinghaus_remaining, incoming.ebbinghaus_remaining),
    ebbinghaus_completed: Boolean(base.ebbinghaus_completed || incoming.ebbinghaus_completed),
    dimension_states: mergedStates,
  })
}

function normalizeWrongWords(words: WrongWordInput[]): WrongWordRecord[] {
  const normalized: WrongWordRecord[] = []
  for (const word of words) {
    const item = normalizeWrongWord(word)
    if (item) normalized.push(item)
  }
  return normalized
}

function updateWordWithDimensionMutation(
  words: WrongWordInput[],
  targetWord: string,
  mutate: (word: WrongWordRecord, nowIso: string) => WrongWordRecord,
): WrongWordRecord[] {
  const needle = targetWord.trim().toLowerCase()
  if (!needle) return mergeWrongWordLists(words)

  const nowIso = new Date().toISOString()
  return sortWrongWordRecords(
    mergeWrongWordLists(words).map(word => {
      if (word.word.trim().toLowerCase() !== needle) return word
      return mutate(word, nowIso)
    }),
  )
}

export function getWrongWordsStorageKey(userId?: ScopedUserId): string {
  return buildUserScopedStorageKey(STORAGE_KEYS.WRONG_WORDS, userId)
}

export function getWrongWordsProgressStorageKey(userId?: ScopedUserId): string {
  return buildUserScopedStorageKey(STORAGE_KEYS.WRONG_WORDS_PROGRESS, userId)
}

export function readWrongWordsFromStorage(userId?: ScopedUserId): WrongWordRecord[] {
  const stored = getStorageItem<WrongWordInput[]>(getWrongWordsStorageKey(userId), [])
  return Array.isArray(stored) ? normalizeWrongWords(stored) : []
}

export function writeWrongWordsToStorage(words: WrongWordInput[], userId?: ScopedUserId): WrongWordRecord[] {
  const normalized = normalizeWrongWords(words)
  setStorageItem(getWrongWordsStorageKey(userId), normalized)
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
  options: { dimension?: WrongWordDimension } = {},
): WrongWordRecord[] {
  const normalizedIncoming = normalizeWrongWord(word)
  if (!normalizedIncoming) return mergeWrongWordLists(words)

  const dimension = options.dimension ?? 'recognition'
  const nowIso = new Date().toISOString()
  const key = normalizedIncoming.word.toLowerCase()
  const existingWords = mergeWrongWordLists(words)
  let matched = false

  const nextWords = existingWords.map(existingWord => {
    if (existingWord.word.toLowerCase() !== key) return existingWord

    matched = true
    const mergedWord = mergeWrongWord(existingWord, normalizedIncoming)
    const nextStates = {
      ...(mergedWord.dimension_states ?? normalizeDimensionStates(mergedWord as WrongWordInput & Record<string, unknown>)),
    }
    nextStates[dimension] = applyDimensionStateFailure(nextStates[dimension] ?? emptyDimensionState(), nowIso)

    return withDerivedFields({
      ...mergedWord,
      first_wrong_at: mergedWord.first_wrong_at ?? nowIso,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })

  if (!matched) {
    const nextStates = {
      ...(normalizedIncoming.dimension_states ?? normalizeDimensionStates(normalizedIncoming as WrongWordInput & Record<string, unknown>)),
    }
    nextStates[dimension] = applyDimensionStateFailure(nextStates[dimension] ?? emptyDimensionState(), nowIso)

    nextWords.push(withDerivedFields({
      ...normalizedIncoming,
      first_wrong_at: normalizedIncoming.first_wrong_at ?? nowIso,
      updated_at: nowIso,
      dimension_states: nextStates,
    }))
  }

  return sortWrongWordRecords(nextWords)
}

export function removeWrongWordFromList(words: WrongWordInput[], wordToRemove: string): WrongWordRecord[] {
  const needle = wordToRemove.trim().toLowerCase()
  return mergeWrongWordLists(words).filter(word => word.word.toLowerCase() !== needle)
}

export function getWrongWordDimensionState(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): WrongWordDimensionState {
  const normalized = normalizeWrongWord(word as WrongWordInput)
  return normalized?.dimension_states?.[dimension] ?? emptyDimensionState()
}

export function getWrongWordDimensionHistoryWrong(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): number {
  return getWrongWordDimensionState(word, dimension).history_wrong
}

export function getWrongWordDimensionPassStreak(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): number {
  return getWrongWordDimensionState(word, dimension).pass_streak
}

export function isWrongWordPendingInDimension(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
): boolean {
  return isDimensionPendingState(getWrongWordDimensionState(word, dimension))
}

export function hasWrongWordHistory(word: Partial<WrongWordRecord>): boolean {
  return WRONG_WORD_DIMENSIONS.some(dimension => getWrongWordDimensionHistoryWrong(word, dimension) > 0)
}

export function hasWrongWordPending(word: Partial<WrongWordRecord>): boolean {
  return WRONG_WORD_DIMENSIONS.some(dimension => isWrongWordPendingInDimension(word, dimension))
}

export function getWrongWordActiveCount(
  word: Partial<WrongWordRecord>,
  scope: WrongWordCollectionScope,
): number {
  const normalized = normalizeWrongWord(word as WrongWordInput)
  if (!normalized) return 0
  return scope === 'pending'
    ? normalized.pending_wrong_count ?? 0
    : normalized.wrong_count ?? 0
}

export function getWrongWordDimensionProgress(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension,
  masteryTarget = WRONG_WORD_PENDING_REVIEW_TARGET,
): {
  streak: number
  target: number
  remaining: number
  pending: boolean
} {
  const streak = Math.min(getWrongWordDimensionPassStreak(word, dimension), masteryTarget)
  return {
    streak,
    target: masteryTarget,
    remaining: Math.max(0, masteryTarget - streak),
    pending: getWrongWordDimensionHistoryWrong(word, dimension) > 0 && streak < masteryTarget,
  }
}

export function getWrongWordReviewProgress(
  word: Partial<WrongWordRecord>,
  dimension: WrongWordDimension = 'meaning',
  masteryTarget = WRONG_WORD_PENDING_REVIEW_TARGET,
) {
  return getWrongWordDimensionProgress(word, dimension, masteryTarget)
}

export function applyWrongWordReviewResult(
  words: WrongWordInput[],
  reviewedWord: string,
  wasCorrect: boolean,
  dimension: WrongWordDimension = 'meaning',
): {
  words: WrongWordRecord[]
  removed: WrongWordRecord | null
} {
  const nextWords = updateWordWithDimensionMutation(words, reviewedWord, (word, nowIso) => {
    const state = getWrongWordDimensionState(word, dimension)
    if (state.history_wrong <= 0) return word

    const nextStates = {
      ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
      [dimension]: applyDimensionStateReviewResult(state, wasCorrect, nowIso),
    }

    return withDerivedFields({
      ...word,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })

  return {
    words: nextWords,
    removed: null,
  }
}

export function syncWrongWordDimensionPassStreak(
  words: WrongWordInput[],
  reviewedWord: string,
  dimension: WrongWordDimension,
  passStreak: number,
): WrongWordRecord[] {
  const clampedPassStreak = clampPassStreak(passStreak)

  return updateWordWithDimensionMutation(words, reviewedWord, (word, nowIso) => {
    const state = getWrongWordDimensionState(word, dimension)
    if (state.history_wrong <= 0) return word

    const nextStates = {
      ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
      [dimension]: {
        ...state,
        pass_streak: clampedPassStreak,
        last_pass_at: clampedPassStreak > 0 ? nowIso : state.last_pass_at,
      },
    }

    return withDerivedFields({
      ...word,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })
}

export function clearWrongWordPendingFromList(words: WrongWordInput[], targetWord: string): WrongWordRecord[] {
  return updateWordWithDimensionMutation(words, targetWord, (word, nowIso) => {
    const nextStates = {
      ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
    }

    for (const dimension of WRONG_WORD_DIMENSIONS) {
      nextStates[dimension] = applyDimensionStateClear(nextStates[dimension] ?? emptyDimensionState(), nowIso)
    }

    return withDerivedFields({
      ...word,
      updated_at: nowIso,
      dimension_states: nextStates,
    })
  })
}

export function clearAllWrongWordPendingFromList(words: WrongWordInput[]): WrongWordRecord[] {
  const nowIso = new Date().toISOString()

  return sortWrongWordRecords(
    mergeWrongWordLists(words).map(word => {
      const nextStates = {
        ...(word.dimension_states ?? normalizeDimensionStates(word as WrongWordInput & Record<string, unknown>)),
      }

      for (const dimension of WRONG_WORD_DIMENSIONS) {
        nextStates[dimension] = applyDimensionStateClear(nextStates[dimension] ?? emptyDimensionState(), nowIso)
      }

      return withDerivedFields({
        ...word,
        updated_at: nowIso,
        dimension_states: nextStates,
      })
    }),
  )
}

export async function loadWrongWords({
  user,
  fetchRemote,
}: {
  user?: unknown
  fetchRemote?: () => Promise<WrongWordsResponse>
}): Promise<WrongWordRecord[]> {
  const userId = readUserId(user)
  const localWords = readWrongWordsFromStorage(userId)

  if (!user || !fetchRemote) {
    return localWords
  }

  try {
    const response = await fetchRemote()
    const remoteWords = Array.isArray(response.words) ? response.words : []
    const merged = mergeWrongWordLists(remoteWords, localWords)
    writeWrongWordsToStorage(merged, userId)
    return merged
  } catch {
    return localWords
  }
}
