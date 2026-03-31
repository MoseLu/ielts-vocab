// ── Types for Practice Components ────────────────────────────────────────────────

export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'radio' | 'quickmemory'

// ── Quick Memory — DHP + Ebbinghaus spaced repetition ──────────────────────
export interface QuickMemoryRecord {
  status: 'known' | 'unknown'
  firstSeen: number       // epoch ms
  lastSeen: number        // epoch ms
  knownCount: number
  unknownCount: number
  nextReview: number      // epoch ms — Ebbinghaus-derived next review time
  fuzzyCount: number      // times user went back and re-answered (indicates uncertainty)
}
export type QuickMemoryRecords = Record<string, QuickMemoryRecord>  // key = word

export interface QuickMemoryModeProps {
  vocabulary: Word[]
  queue: number[]
  settings: AppSettings
  bookId: string | null
  chapterId: string | null
  bookChapters: Chapter[]
  reviewHasMore?: boolean
  onContinueReview?: () => void
  onModeChange: (mode: string) => void
  onNavigate: (path: string) => void
  /** Called with each word the user marks as "unknown" — adds it to the error book */
  onWrongWord: (word: Word) => void
}

// Which dimension smart mode is testing for the current word
export type SmartDimension = 'listening' | 'meaning' | 'dictation'

export type ToastType = 'info' | 'success' | 'error'

export interface WordExample {
  en: string
  zh: string
}

export interface Word {
  word: string
  phonetic: string
  pos: string
  definition: string
  chapter_id?: number | string
  chapter_title?: string
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

export interface OptionItem {
  definition: string
  pos: string
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
  onDayChange: (day: number) => void
  onNavigate: (path: string) => void
  onPause?: () => void
  // Radio mode quick settings
  radioQuickSettings?: RadioQuickSettings
  onRadioSettingChange?: (key: keyof RadioQuickSettings, value: string | boolean) => void
}

export interface WordListPanelProps {
  show: boolean
  vocabulary: Word[]
  queue: number[]
  queueIndex: number
  wordStatuses: WordStatuses
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
  onModeChange: (mode: string) => void
  onSessionInteraction?: () => void
  onProgressChange?: (wordsStudied: number) => void
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
  previousWord: Word | null
  lastState: LastState | null
  onSpellingInputChange: (value: string) => void
  onSpellingSubmit: () => void
  onSkip: () => void
  onGoBack: () => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: (word: string) => void
}

export interface OptionsModeProps {
  currentWord: Word
  previousWord: Word | null
  lastState: LastState | null
  mode: PracticeMode
  smartDimension?: SmartDimension
  options: OptionItem[]
  selectedAnswer: number | null
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
  onSpellingSubmit: () => void
  onSpellingInputChange: (value: string) => void
  onStartRecording: () => void
  onStopRecording: () => void
  onPlayWord: (word: string) => void
}
