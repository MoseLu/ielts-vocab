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
  recognition: '英译汉（认识）',
  meaning: '汉译英（会想）',
  listening: '听音选义（听得到）',
  dictation: '拼写测试（会拼写）',
}

export const WRONG_WORD_PENDING_REVIEW_TARGET = 4
export const WRONG_WORD_ERROR_REVIEW_TARGET = WRONG_WORD_PENDING_REVIEW_TARGET
