import type { QuickMemoryRecordState } from '../../lib/quickMemory'

export type { QuickMemoryRecordState } from '../../lib/quickMemory'

export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'follow' | 'radio' | 'quickmemory'
export type SpellingSubmitSource = 'button' | 'enter'
export type SmartDimension = 'listening' | 'meaning' | 'dictation'
export type ToastType = 'info' | 'success' | 'error'

export interface QuickMemoryRecord {
  status: 'known' | 'unknown'
  firstSeen: number
  lastSeen: number
  knownCount: number
  unknownCount: number
  nextReview: number
  fuzzyCount: number
  bookId?: string
  chapterId?: string
}

export type QuickMemoryRecords = Record<string, QuickMemoryRecord>

export interface WordExample {
  en: string
  zh: string
}

export interface ListeningConfusableCandidate {
  word: string
  phonetic: string
  pos: string
  definition: string
  group_key?: string
}

export interface Word {
  word: string
  phonetic: string
  pos: string
  definition: string
  group_key?: string
  listening_confusables?: ListeningConfusableCandidate[]
  book_id?: string
  book_title?: string
  chapter_id?: number | string
  chapter_title?: string
  dueState?: 'due' | 'upcoming'
  nextReview?: number
  examples?: WordExample[]
}

export interface ProgressData {
  current_index: number
  correct_count: number
  wrong_count: number
  is_completed: boolean
  words_learned?: number
  answered_words?: string[]
  queue_words?: string[]
  updatedAt?: string
  updated_at?: string
}

export interface AppSettings {
  shuffle?: boolean
  repeatWrong?: boolean
  playbackSpeed?: string
  volume?: string
  interval?: string
  reviewInterval?: string
  reviewLimit?: string
  [key: string]: unknown
}

export interface WordPlaybackOptions {
  playbackSpeed?: string
}

export type WordPlaybackHandler = (word: string, options?: WordPlaybackOptions) => void

export interface OptionItem {
  definition: string
  pos: string
  word?: string
  phonetic?: string
  display_mode?: 'definition' | 'word'
}

export interface LastState {
  qi: number
  cc: number
  wc: number
  prevWord: Word | null
}

export type WordStatus = 'correct' | 'wrong'

export interface WordStatuses {
  [vocabIdx: number]: WordStatus
}

export interface Chapter {
  id: number | string
  title: string
  word_count?: number
  group_count?: number
  is_custom?: boolean
}

export interface RadioQuickSettings {
  playbackSpeed: string
  playbackCount: string
  loopMode: boolean
  interval: string
}

export interface WordListActionControls {
  isFavorite: (word: string | null | undefined) => boolean
  isFavoritePending: (word: string | null | undefined) => boolean
  onFavoriteToggle: (word: Word) => void
  isFamiliar: (word: string | null | undefined) => boolean
  isFamiliarPending: (word: string | null | undefined) => boolean
  onFamiliarToggle: (word: Word) => void
}

export type QuickMemoryRecordChangeHandler = (
  word: Word,
  record: QuickMemoryRecordState,
) => void
