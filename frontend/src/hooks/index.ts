// Shared cross-feature / cross-composable facade.
//
// Why this file exists:
// - `src/hooks/useAIChat.ts` and `src/hooks/useSpeechRecognition.ts` were 5-line
//   re-export shims that pretended to be hooks but only forwarded to the real
//   implementation under features/ or composables/.
// - This barrel is the single supported entry point for the truly cross-cutting
//   hooks (useAIChat, useSpeechRecognition) and the study-session helpers that
//   the route layer needs regardless of which feature owns them.
// - The remaining files under src/hooks/ (e.g. useResponsiveSkeletonCount.ts)
//   are true shared hooks and continue to live next to this facade.

export { useAIChat } from '../composables/ai-chat/useAIChat'
export type { GeneratedBook } from '../types'

export {
  useSpeechRecognition,
} from '../features/speech/hooks/useSpeechRecognition'
export type {
  SpeechRecognitionOptions,
  UseSpeechRecognitionReturn,
} from '../features/speech/hooks/speechRecognitionTypes'

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
