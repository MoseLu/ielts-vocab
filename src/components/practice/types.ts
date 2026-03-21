// ── Types for Practice Components ────────────────────────────────────────────────

export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'radio'

export type ToastType = 'info' | 'success' | 'error'

export interface Word {
  word: string
  phonetic: string
  pos: string
  definition: string
  chapter_id?: number | string
  chapter_title?: string
}

export interface ProgressData {
  current_index: number
  correct_count: number
  wrong_count: number
  is_completed: boolean
  words_learned?: number
  updatedAt?: string
}

export interface AppSettings {
  shuffle?: boolean
  repeatWrong?: boolean
  playbackSpeed?: string
  volume?: string
  interval?: string
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
