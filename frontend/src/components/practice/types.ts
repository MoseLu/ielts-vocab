import type { ReactNode } from 'react'
import type { QuickMemoryRecordState } from '../../lib/quickMemory'

export type { QuickMemoryRecordState } from '../../lib/quickMemory'

// ── Types for Practice Components ────────────────────────────────────────────────

export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'follow' | 'radio' | 'quickmemory'
export type SpellingSubmitSource = 'button' | 'enter'

// ── Quick Memory — DHP + Ebbinghaus spaced repetition ──────────────────────
export interface QuickMemoryRecord {
  status: 'known' | 'unknown'
  firstSeen: number       // epoch ms
  lastSeen: number        // epoch ms
  knownCount: number
  unknownCount: number
  nextReview: number      // epoch ms — Ebbinghaus-derived next review time
  fuzzyCount: number      // times user went back and re-answered (indicates uncertainty)
  bookId?: string
  chapterId?: string
}
export type QuickMemoryRecords = Record<string, QuickMemoryRecord>  // key = word

export interface QuickMemoryModeProps {
  vocabulary: Word[]
  queue: number[]
  settings: AppSettings
  bookId: string | null
  chapterId: string | null
  bookChapters: Chapter[]
  reviewMode?: boolean
  errorMode?: boolean
  reviewHasMore?: boolean
  onContinueReview?: () => void
  buildChapterPath?: (chapterId: string | number) => string
  onModeChange: (mode: PracticeMode) => void
  onNavigate: (path: string) => void
  /** Called with each word the user marks as "unknown" — adds it to the error book */
  onWrongWord: (word: Word) => void
  /** Called after each quick-memory answer so the parent can react to mastery changes */
  onQuickMemoryRecordChange?: (word: Word, record: QuickMemoryRecordState) => void
  /** Saved queue position to resume from (e.g. after pause+exit in error mode) */
  initialIndex?: number
  /** Called whenever the user advances or goes back, so the parent can persist position */
  onIndexChange?: (index: number) => void
  favoriteSlot?: ReactNode
  speakingSlot?: ReactNode
}

// Which dimension smart mode is testing for the current word
export type SmartDimension = 'listening' | 'meaning' | 'dictation'

export type ToastType = 'info' | 'success' | 'error'

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
  /** 本章已覆盖的不重复词汇数（≤章节词表长度），与 correct+wrong 答题次数分离 */
  words_learned?: number
  /** 恢复进度用：本轮已答过的词（小写） */
  answered_words?: string[]
  /** 恢复进度用：保存练习队列顺序，防止重新洗牌后进度失效 */
  queue_words?: string[]
  updatedAt?: string
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

// Props interfaces for components
export interface PracticePageProps {
  user?: unknown
  currentDay?: number
  mode?: PracticeMode
  showToast?: (message: string, type?: ToastType) => void
  onModeChange?: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
}

export interface RadioQuickSettings {
  playbackSpeed: string
  playbackCount: string
  loopMode: boolean
  interval: string
}

export interface PracticeControlBarProps {
  mode: PracticeMode | undefined
  currentDay: number | undefined
  bookId: string | null
  chapterId: string | null
  errorMode: boolean
  vocabularyLength: number
  currentChapterTitle: string
  bookChapters: Chapter[]
  showWordList: boolean
  showPracticeSettings: boolean
  onWordListToggle: () => void
  onSettingsToggle: () => void
  onModeChange: (mode: PracticeMode) => void
  onDayChange?: (day: number) => void
  onNavigate: (path: string) => void
  buildChapterPath?: (chapterId: string | number) => string
  onExitHome?: () => void
  // Radio mode quick settings
  radioQuickSettings?: RadioQuickSettings
  onRadioSettingChange?: (key: keyof RadioQuickSettings, value: string | boolean) => void
}

export interface WordListActionControls {
  isFavorite: (word: string | null | undefined) => boolean
  isFavoritePending: (word: string | null | undefined) => boolean
  onFavoriteToggle: (word: Word) => void
  isFamiliar: (word: string | null | undefined) => boolean
  isFamiliarPending: (word: string | null | undefined) => boolean
  onFamiliarToggle: (word: Word) => void
}

export interface WordListPanelProps {
  show: boolean
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
  wordStatuses: WordStatuses
  wordActionControls?: WordListActionControls
  onClose: () => void
}

export interface RadioModeProps {
  vocabulary: Word[]
  queue: number[]
  radioIndex: number
  showSettings: boolean
  settings: AppSettings
  onRadioSkipPrev: () => void
  onRadioSkipNext: () => void
  onRadioPause: () => void
  onRadioResume: () => void
  onRadioRestart: () => void
  onRadioStop: () => void
  onNavigate: (path: string) => void
  onCloseSettings: () => void
  onModeChange: (mode: PracticeMode) => void
  onIndexChange?: (index: number) => void
  onSessionInteraction?: () => void | Promise<void>
  onProgressChange?: (wordsStudied: number) => void
  isSessionActive?: (at?: number) => boolean
  favoriteSlot?: ReactNode
  speakingSlot?: ReactNode
}

export interface DictationModeProps {
  currentWord: Word
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  settings: AppSettings
  progressValue: number
  total: number
  queueIndex: number
  previousWord: Word | null
  lastState: LastState | null
  errorMode?: boolean
  reviewMode?: boolean
  spellingLocked?: boolean
  spellingFeedbackDismissing?: boolean
  spellingFeedbackSnapshot?: string | null
  onSpellingInputChange: (value: string) => void
  onSpellingSubmit: (source?: SpellingSubmitSource) => void
  onSkip: () => void
  onGoBack: () => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: WordPlaybackHandler
  favoriteSlot?: ReactNode
  speakingSlot?: ReactNode
}

export interface OptionsModeProps {
  currentWord: Word
  previousWord: Word | null
  lastState: LastState | null
  mode: PracticeMode
  smartDimension?: SmartDimension
  errorMode?: boolean
  reviewMode?: boolean
  options: OptionItem[]
  optionsLoading?: boolean
  selectedAnswer: number | null
  wrongSelections?: number[]
  showResult: boolean
  correctIndex: number
  spellingInput: string
  spellingResult: 'correct' | 'wrong' | null
  speechConnected: boolean
  speechRecording: boolean
  settings: AppSettings
  progressValue: number
  total: number
  onOptionSelect: (idx: number) => void
  onSkip: () => void
  onGoBack: () => void
  onSpellingSubmit: (source?: SpellingSubmitSource) => void
  onSpellingInputChange: (value: string) => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: WordPlaybackHandler
  favoriteSlot?: ReactNode
  speakingSlot?: ReactNode
}
