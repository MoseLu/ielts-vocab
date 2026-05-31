import type { ReactNode } from 'react'
import type {
  AppSettings,
  Chapter,
  LastState,
  OptionItem,
  PracticeMode,
  QuickMemoryRecordChangeHandler,
  RadioQuickSettings,
  SmartDimension,
  SpellingSubmitSource,
  ToastType,
  Word,
  WordListActionControls,
  WordPlaybackHandler,
  WordStatuses,
} from '../../features/practice/types'
import type { QuickMemoryModeVariant } from '../../features/practice/quickMemorySession'
import type { PracticeGroupWindow } from '../../composables/practice/page/practicePageGrouping'

export type {
  AppSettings,
  Chapter,
  LastState,
  ListeningConfusableCandidate,
  OptionItem,
  PracticeMode,
  ProgressData,
  QuickMemoryRecord,
  QuickMemoryRecords,
  QuickMemoryRecordState,
  RadioQuickSettings,
  SmartDimension,
  SpellingSubmitSource,
  ToastType,
  Word,
  WordExample,
  WordListActionControls,
  WordPlaybackHandler,
  WordPlaybackOptions,
  WordStatus,
  WordStatuses,
} from '../../features/practice/types'

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
  chapterGroup?: PracticeGroupWindow | null
  chapterQueueWords?: string[]
  onContinueChapterGroup?: () => void
  buildChapterPath?: (chapterId: string | number) => string
  onModeChange: (mode: PracticeMode) => void
  onNavigate: (path: string) => void
  onWrongWord: (word: Word) => void
  onQuickMemoryRecordChange?: QuickMemoryRecordChangeHandler
  initialIndex?: number
  onIndexChange?: (index: number) => void
  favoriteSlot?: ReactNode
  modeVariant?: QuickMemoryModeVariant
}

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
  onDayChange?: (day: number) => void
  onNavigate: (path: string) => void
  buildChapterPath?: (chapterId: string | number) => string
  onExitHome?: () => void
  showWordListAction?: boolean
  showSettingsAction?: boolean
  radioQuickSettings?: RadioQuickSettings
  onRadioSettingChange?: (key: keyof RadioQuickSettings, value: string | boolean) => void
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
