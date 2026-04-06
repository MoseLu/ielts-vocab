export type WrongWordDimension = 'recognition' | 'meaning' | 'listening' | 'dictation'
export type WrongWordCollectionScope = 'history' | 'pending'

export interface WrongWordExample {
  en: string
  zh: string
}

export interface WrongWordListeningConfusable {
  word: string
  phonetic: string
  pos: string
  definition: string
  group_key?: string
}

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
  group_key?: string
  listening_confusables?: WrongWordListeningConfusable[]
  examples?: WrongWordExample[]
  book_id?: string
  book_title?: string
  chapter_id?: number | string
  chapter_title?: string
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

export type WrongWordInput = Partial<WrongWordRecord> & {
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

export type WrongWordsResponse = { words?: WrongWordInput[] }
export type ScopedUserId = string | number | null | undefined

export const WRONG_WORD_DIMENSIONS: WrongWordDimension[] = [
  'recognition',
  'meaning',
  'listening',
  'dictation',
]

export const WRONG_WORD_DIMENSION_LABELS: Record<WrongWordDimension, string> = {
  recognition: '看词认义',
  meaning: '中文想英文',
  listening: '听音辨义',
  dictation: '听音拼写',
}

export const WRONG_WORD_DIMENSION_TITLES: Record<WrongWordDimension, string> = {
  recognition: '看到英文单词时，能不能认出中文意思',
  meaning: '看到中文意思时，能不能主动想到英文单词',
  listening: '听到发音后，能不能判断它对应的意思',
  dictation: '听到发音后，能不能把单词完整拼出来',
}

export const WRONG_WORD_SCOPE_LABELS: Record<WrongWordCollectionScope, string> = {
  pending: '待清错词',
  history: '累计错词',
}

export function isWrongWordDimension(value: string | null | undefined): value is WrongWordDimension {
  return value === 'recognition'
    || value === 'meaning'
    || value === 'listening'
    || value === 'dictation'
}

export function getWrongWordDimensionLabel(
  dimension?: string | null,
  fallback?: string | null,
): string | null {
  if (isWrongWordDimension(dimension)) return WRONG_WORD_DIMENSION_LABELS[dimension]

  const normalizedFallback = fallback?.trim()
  return normalizedFallback ? normalizedFallback : null
}

export const WRONG_WORD_PENDING_REVIEW_TARGET = 4
export const WRONG_WORD_ERROR_REVIEW_TARGET = WRONG_WORD_PENDING_REVIEW_TARGET
