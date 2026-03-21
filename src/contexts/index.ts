// ── Contexts Index ──────────────────────────────────────────────────────────────

export { AuthProvider, useAuth } from './AuthContext'
export { SettingsProvider, useSettings } from './SettingsContext'
export { ToastProvider, useToast } from './ToastContext'
export { setGlobalLearningContext, clearGlobalLearningContext, getGlobalLearningContext } from './AIChatContext'

// Re-export AI Chat hook from the dedicated module
export { useAIChat } from '../hooks/useAIChat'
