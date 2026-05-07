import type { PracticeMode } from '@ielts-vocab/app-core'

export type ScreenKey =
  | 'home'
  | 'books'
  | 'practice'
  | 'errors'
  | 'stats'
  | 'exams'
  | 'journal'
  | 'ai'
  | 'search'
  | 'profile'
  | 'profileSettings'
  | 'profileSecurity'
  | 'profileFeedback'

export type NavigateOptions = {
  bookId?: string
  chapterId?: string | number | null
  mode?: PracticeMode
  word?: string
}

export type Navigate = (screen: ScreenKey, options?: NavigateOptions) => void
