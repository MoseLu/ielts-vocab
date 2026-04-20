// ── Global Type Definitions ──────────────────────────────────────────────────────

// User types
export interface User {
  id: string | number
  email?: string
  username?: string
  avatar_url?: string | null
  is_admin?: boolean
  created_at?: string
  [key: string]: unknown
}

// Toast types
export type ToastType = 'info' | 'success' | 'error'

export interface ToastData {
  message: string
  type: ToastType
}

// Practice types (re-export from practice)
export type PracticeMode = 'smart' | 'listening' | 'meaning' | 'dictation' | 'follow' | 'radio'

export interface Word {
  word: string
  phonetic: string
  pos: string
  definition: string
  listening_confusables?: Array<{
    word: string
    phonetic: string
    pos: string
    definition: string
    group_key?: string
  }>
  chapter_id?: number | string
  chapter_title?: string
  is_incomplete?: boolean
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
}

export interface AppSettings {
  shuffle?: boolean
  repeatWrong?: boolean
  playbackSpeed?: string
  volume?: string
  interval?: string
  reviewInterval?: string
  reviewLimit?: string
  reviewLimitCustomized?: boolean
  darkMode?: boolean
  fontSize?: string
  [key: string]: unknown
}

// Book types
export interface Book {
  id: string
  title: string
  description?: string
  word_count: number
  chapter_count?: number
  group_count?: number
  category?: string
  level?: string
  icon?: string
  color?: string
  is_paid?: boolean
  has_chapters?: boolean
  is_auto_favorites?: boolean
  is_custom_book?: boolean
  education_stage?: string | null
  exam_type?: string | null
  ielts_skill?: string | null
  share_enabled?: boolean
  chapter_word_target?: number
  incomplete_word_count?: number
  study_type?: string
  file?: string
  practice_mode?: string
  [key: string]: unknown
}

export interface Chapter {
  id: number | string
  title: string
  word_count?: number
  group_count?: number
  is_custom?: boolean
}

export interface BookProgress {
  book_id: string | number
  current_index: number
  correct_count?: number
  wrong_count?: number
  is_completed?: boolean
  updatedAt?: string
}

// API Response types
export interface ApiResponse<T> {
  data?: T
  error?: string
  message?: string
}

// Navigation types
export interface BreadcrumbItem {
  label: string
  href?: string
}

// ── AI Chat Types ────────────────────────────────────────────────────────────────

export interface AIMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  options?: string[]
  isStreaming?: boolean
  timestamp: number
}

export interface LearningContext {
  currentWord?: string
  currentPhonetic?: string
  currentPos?: string
  currentDefinition?: string
  currentBook?: string
  currentChapter?: string
  currentChapterTitle?: string
  practiceMode?: string
  mode?: string
  sessionProgress?: number
  sessionAccuracy?: number
  wordsCompleted?: number
  totalWords?: number
  sessionCompleted?: boolean
  [key: string]: unknown
}

export interface GeneratedBook {
  bookId: string
  title: string
  description: string
  chapters: Array<{ id: string; title: string; wordCount: number }>
  words: Array<{
    chapterId: string
    word: string
    phonetic: string
    pos: string
    definition: string
  }>
}
