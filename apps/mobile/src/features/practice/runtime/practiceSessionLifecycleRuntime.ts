import {
  loadBookProgress,
  loadChapterProgress,
  logPracticeSession,
  savePracticeProgress,
} from '../../../api/learnerApi'
import { asyncAppStorage } from '../../../storage/mobileStorage'
import type { PracticeSessionDependencies } from './practiceSessionLifecycle'

export const practiceSessionDependencies: PracticeSessionDependencies = {
  loadBookProgress,
  loadChapterProgress,
  logPracticeSession,
  savePracticeProgress,
  storage: asyncAppStorage,
}
