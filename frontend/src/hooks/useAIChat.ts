// Cross-feature hook barrel for the legacy single-import surface.
//
// This file exists to keep the old `from '@/hooks/useAIChat'` import path
// working for callers and tests that predate the R1 consolidation. Real
// implementations live under `composables/ai-chat/` and `features/ai-chat/`.
export { useAIChat } from '../composables/ai-chat/useAIChat'
export type { GeneratedBook } from '../types'

export {
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  STUDY_SESSION_IDLE_GRACE_MS,
  cancelSession,
  finalizeStudySessionSegment,
  flushStudySessionOnPageHide,
  isStudySessionActive,
  logSession,
  markStudySessionRecoveryHandled,
  prepareStudySessionForLearningAction,
  recordStudySessionUserActivity,
  recordModeAnswer,
  resolveStudySessionDurationSeconds,
  startSession,
  touchStudySessionActivity,
  updateStudySessionSnapshot,
} from '../composables/ai-chat/sessionTracking'
