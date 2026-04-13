export { useAIChat } from '../features/ai-chat/hooks/useAIChat'
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
  recordModeAnswer,
  resolveStudySessionDurationSeconds,
  startSession,
  touchStudySessionActivity,
  updateStudySessionSnapshot,
} from '../composables/ai-chat/sessionTracking'
export type { GeneratedBook } from '../types'
