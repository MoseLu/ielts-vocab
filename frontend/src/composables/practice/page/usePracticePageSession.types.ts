import type { MutableRefObject } from 'react'
import type { AppSettings, PracticeMode, RadioQuickSettings } from '../../../features/practice/types'

export interface UsePracticePageSessionParams {
  mode?: PracticeMode
  errorMode: boolean
  chapterId: string | null
  practiceBookId: string | null
  practiceChapterId: string | null
  correctCount: number
  wrongCount: number
}

export interface UsePracticePageSessionResult {
  settings: AppSettings
  radioQuickSettings: RadioQuickSettings
  handleRadioSettingChange: (key: keyof RadioQuickSettings, value: string | boolean) => void
  sessionStartRef: MutableRefObject<number>
  sessionIdRef: MutableRefObject<number | null>
  sessionCorrectRef: MutableRefObject<number>
  sessionWrongRef: MutableRefObject<number>
  correctCountRef: MutableRefObject<number>
  wrongCountRef: MutableRefObject<number>
  completedSessionDurationSecondsRef: MutableRefObject<number | null>
  sessionLoggedRef: MutableRefObject<boolean>
  currentModeRef: MutableRefObject<PracticeMode | undefined>
  effectiveSessionModeRef: MutableRefObject<string>
  sessionBookIdRef: MutableRefObject<string | null>
  sessionChapterIdRef: MutableRefObject<string | null>
  radioWordsStudiedRef: MutableRefObject<number>
  wordsLearnedBaselineRef: MutableRefObject<number>
  chapterCorrectBaselineRef: MutableRefObject<number>
  chapterWrongBaselineRef: MutableRefObject<number>
  uniqueAnsweredRef: MutableRefObject<Set<string>>
  sessionUniqueWordsRef: MutableRefObject<Set<string>>
  beginSession: (context?: { bookId?: string | null; chapterId?: string | null }) => void
  prepareSessionForLearningAction: (activityAt?: number) => Promise<void>
  completeCurrentSession: () => Promise<number>
  computeChapterWordsLearned: (cap: number) => number
  registerAnsweredWord: (word: string) => void
  markFollowSessionInteraction: (activityAt?: number) => Promise<void>
  markRadioSessionInteraction: () => Promise<void>
  handleRadioProgressChange: (wordsStudied: number) => void
  syncCurrentSessionSnapshot: (activeAt?: number) => void
  isCurrentSessionActive: (at?: number) => boolean
}
