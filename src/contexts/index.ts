// ── Contexts Index ──────────────────────────────────────────────────────────────

export { AuthProvider, useAuth } from './AuthContext'
export { SettingsProvider, useSettings } from './SettingsContext'
export { ToastProvider, useToast } from './ToastContext'
export {
  AIChatProvider,
  setGlobalLearningContext,
  clearGlobalLearningContext,
  getGlobalLearningContext,
} from './AIChatContext'

// Re-export AI Chat hook from the feature module
export { useAIChat } from '../features/ai-chat/hooks'
