import {
  WRONG_WORD_DIMENSIONS,
  WRONG_WORD_PENDING_REVIEW_TARGET,
  type WrongWordDimension,
  type WrongWordDimensionState,
  type WrongWordDimensionStateMap,
  type WrongWordInput,
  type WrongWordRecord,
} from './types'

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

function normalizeOptionalText(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined
  const trimmed = value.trim()
  return trimmed || undefined
}

function normalizeExamples(value: unknown): WrongWordRecord['examples'] {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    .map(item => ({
      en: normalizeOptionalText(item.en) ?? '',
      zh: normalizeOptionalText(item.zh) ?? '',
    }))
    .filter(item => item.en || item.zh)
}

function normalizeListeningConfusables(value: unknown): WrongWordRecord['listening_confusables'] {
  if (!Array.isArray(value)) return []
  return value
    .filter((item): item is Record<string, unknown> => !!item && typeof item === 'object')
    .map(item => ({
      word: normalizeOptionalText(item.word) ?? '',
      phonetic: normalizeOptionalText(item.phonetic) ?? '',
      pos: normalizeOptionalText(item.pos) ?? '',
      definition: normalizeOptionalText(item.definition) ?? '',
      group_key: normalizeOptionalText(item.group_key),
    }))
    .filter(item => item.word)
}

function readDateField(word: WrongWordInput & Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = asIsoDate(word[key])
    if (value) return value
  }
  return undefined
}

export function pickEarlierDate(...values: Array<string | undefined>): string | undefined {
  let picked: string | undefined

  for (const value of values) {
    const normalized = asIsoDate(value)
    if (!normalized) continue
    if (!picked || normalized < picked) picked = normalized
  }

  return picked
}

export function pickLaterDate(...values: Array<string | undefined>): string | undefined {
  let picked: string | undefined

  for (const value of values) {
    const normalized = asIsoDate(value)
    if (!normalized) continue
    if (!picked || normalized > picked) picked = normalized
  }

  return picked
}

export function emptyDimensionState(): WrongWordDimensionState {
  return {
    history_wrong: 0,
    pass_streak: 0,
  }
}

export function clampPassStreak(value: unknown, target = WRONG_WORD_PENDING_REVIEW_TARGET): number {
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

export function normalizeScopedUserId(value: unknown): string | number | null {
  return typeof value === 'string' || typeof value === 'number'
    ? value
    : null
}

export function normalizeDimensionStates(rawWord: WrongWordInput & Record<string, unknown>): WrongWordDimensionStateMap {
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

export function mergeDimensionStates(
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

export function isDimensionPendingState(state: WrongWordDimensionState): boolean {
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

export function applyDimensionStateReviewResult(
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

export function applyDimensionStateFailure(
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

export function applyDimensionStateClear(
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

export function withDerivedFields(base: Omit<WrongWordRecord, 'wrong_count' | 'pending_wrong_count' | 'history_dimension_count' | 'pending_dimension_count' | 'review_pass_target' | 'recognition_wrong' | 'recognition_pending' | 'recognition_pass_streak' | 'meaning_pending' | 'meaning_pass_streak' | 'listening_pending' | 'listening_pass_streak' | 'dictation_pending' | 'dictation_pass_streak' | 'dimension_states'> & {
  dimension_states: WrongWordDimensionStateMap
}): WrongWordRecord {
  const summary = summarizeDimensionStates(base.dimension_states)

  const pendingDimensions = WRONG_WORD_DIMENSIONS.filter(
    dimension => (base.dimension_states[dimension]?.pass_streak ?? 0) < WRONG_WORD_PENDING_REVIEW_TARGET,
  )
  const wordMasteryStatus: WrongWordRecord['word_mastery_status'] =
    pendingDimensions.length === 0
      ? 'passed'
      : WRONG_WORD_DIMENSIONS.every(dimension => (base.dimension_states[dimension]?.pass_streak ?? 0) >= 1)
        ? WRONG_WORD_DIMENSIONS.some(dimension => (base.dimension_states[dimension]?.pass_streak ?? 0) > 1)
          ? 'in_review'
          : 'unlocked'
        : 'new'

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
    word_mastery_status: wordMasteryStatus,
    pending_dimensions: pendingDimensions,
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

export function normalizeWrongWord(word: WrongWordInput): WrongWordRecord | null {
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
    group_key: normalizeOptionalText(rawWord.group_key),
    listening_confusables: normalizeListeningConfusables(rawWord.listening_confusables),
    examples: normalizeExamples(rawWord.examples),
    book_id: normalizeOptionalText(rawWord.book_id),
    book_title: normalizeOptionalText(rawWord.book_title),
    chapter_id: normalizeOptionalText(rawWord.chapter_id) ?? (
      typeof rawWord.chapter_id === 'number' ? rawWord.chapter_id : undefined
    ),
    chapter_title: normalizeOptionalText(rawWord.chapter_title),
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
    group_key: base.group_key || incoming.group_key,
    listening_confusables: (base.listening_confusables?.length ? base.listening_confusables : incoming.listening_confusables) ?? [],
    examples: (base.examples?.length ? base.examples : incoming.examples) ?? [],
    book_id: base.book_id || incoming.book_id,
    book_title: base.book_title || incoming.book_title,
    chapter_id: base.chapter_id ?? incoming.chapter_id,
    chapter_title: base.chapter_title || incoming.chapter_title,
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

export function updateWordWithDimensionMutation(
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
