export { useAIChat } from '../composables/ai-chat/useAIChat'
export {
  PASSIVE_STUDY_SESSION_MIN_SECONDS,
  STUDY_SESSION_IDLE_GRACE_MS,
  cancelSession,
  flushStudySessionOnPageHide,
  logSession,
  recordModeAnswer,
  startSession,
  touchStudySessionActivity,
  updateStudySessionSnapshot,
} from '../composables/ai-chat/sessionTracking'
export type { GeneratedBook } from '../types'
