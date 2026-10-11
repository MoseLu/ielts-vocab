// ai-chat feature public surface for hooks.
//
// Why: useAIChat's real implementation lives in src/composables/ai-chat/ to
// stay next to the related sessionTracking / commands / streaming siblings.
// Cross-feature code imports it through this barrel only.
export { useAIChat } from '../../../composables/ai-chat/useAIChat'
export type { GeneratedBook } from '../../../types'
