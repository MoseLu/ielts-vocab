import type { MobileWrongWordDimensionFilter, MobileWrongWordFilters, PracticeMode } from '@ielts-vocab/app-core'

export type ScreenKey =
  | 'home'
  | 'homePlan'
  | 'books'
  | 'customBook'
  | 'practice'
  | 'errors'
  | 'stats'
  | 'statsDetail'
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
  selectedWrongWords?: string[]
  statsSection?: 'chapters' | 'ebbinghaus' | 'history' | 'modes' | 'profile'
  word?: string
  wrongWordDimension?: MobileWrongWordDimensionFilter
  wrongWordFilters?: MobileWrongWordFilters
  wrongWordMode?: PracticeMode | 'all'
}

export type Navigate = (screen: ScreenKey, options?: NavigateOptions) => void
