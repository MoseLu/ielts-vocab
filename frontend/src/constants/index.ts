import { PRACTICE_MODE_LABELS } from './practiceModes'

// ── Application Constants ────────────────────────────────────────────────────────

// Practice modes
export const PRACTICE_MODES = {
  SMART: 'smart',
  LISTENING: 'listening',
  MEANING: 'meaning',
  DICTATION: 'dictation',
  RADIO: 'radio',
  QUICK_MEMORY: 'quickmemory',
} as const

export const PRACTICE_MODE_NAMES: Record<typeof PRACTICE_MODES[keyof typeof PRACTICE_MODES], string> = {
  [PRACTICE_MODES.SMART]: PRACTICE_MODE_LABELS.smart,
  [PRACTICE_MODES.LISTENING]: PRACTICE_MODE_LABELS.listening,
  [PRACTICE_MODES.MEANING]: PRACTICE_MODE_LABELS.meaning,
  [PRACTICE_MODES.DICTATION]: PRACTICE_MODE_LABELS.dictation,
  [PRACTICE_MODES.RADIO]: PRACTICE_MODE_LABELS.radio,
  [PRACTICE_MODES.QUICK_MEMORY]: PRACTICE_MODE_LABELS.quickmemory,
}

// LocalStorage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'auth_token',
  AUTH_USER: 'auth_user',
  CURRENT_DAY: 'current_day',
  CURRENT_MODE: 'current_mode',
  APP_SETTINGS: 'app_settings',
  DAY_PROGRESS: 'day_progress',
  BOOK_PROGRESS: 'book_progress',
  CHAPTER_PROGRESS: 'chapter_progress',
  WRONG_WORDS: 'wrong_words',
  WRONG_WORDS_PROGRESS: 'wrong_words_progress',
  WRONG_WORDS_REVIEW_SELECTION: 'wrong_words_review_selection',
  SMART_WORD_STATS: 'smart_word_stats',
  QUICK_MEMORY_RECORDS: 'quick_memory_records',
  CHAPTER_MODE_PROGRESS: 'chapter_mode_progress',
  ACTIVE_STUDY_SESSION: 'active_study_session',
} as const

// API endpoints
export const API_BASE = '/api'
export const API_ENDPOINTS = {
  AUTH: `${API_BASE}/auth`,
  BOOKS: `${API_BASE}/books`,
  VOCABULARY: `${API_BASE}/vocabulary`,
  PROGRESS: `${API_BASE}/progress`,
} as const

// Default settings
export const DEFAULT_SETTINGS = {
  shuffle: true,
  repeatWrong: true,
  playbackSpeed: '1.0',
  volume: '100',
  interval: '2',
  reviewInterval: '1',
  reviewLimit: 'unlimited',
  reviewLimitCustomized: false,
  darkMode: false,
  fontSize: 'medium',
} as const

// Practice settings
export const PRACTICE_SETTINGS = {
  OPTION_COUNT: 4,
  AUTO_PLAY_DELAY: 300,
  RESULT_DISPLAY_DELAY: 1200,
  DICTATION_RESULT_DELAY: 1500,
} as const

// UI constants
export const UI = {
  TOAST_DURATION: 3000,
  DEBOUNCE_DELAY: 300,
  ANIMATION_DURATION: 200,
} as const
